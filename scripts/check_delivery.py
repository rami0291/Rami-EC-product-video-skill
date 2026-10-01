#!/usr/bin/env python3
"""Check plan invariants and actual media metadata. Does not judge visual/audio taste."""
import argparse
import hashlib
import re
from fractions import Fraction
import json
import math
from pathlib import Path
import subprocess
import sys


def nonempty(value):
    return isinstance(value,str) and bool(value.strip())


FILE_EXT=r'\.(?:md|txt|json|csv|tsv|xlsx?|pdf|docx?|html?|jpe?g|png|webp|tiff?|svg)'

DATA=Path(__file__).resolve().parent/'data'
def load_data(name):
    return json.loads((DATA/(name+'.json')).read_text(encoding='utf-8'))
# Locale, channel and category rules live in scripts/data/*.json so a new market or category is a data change.
LOCALES=load_data('locales');CHANNELS=load_data('channels');CLAIMS=load_data('claims');CATEGORIES=load_data('categories')


def hits(table, locale, text):
    """Patterns in {'*':[...], locale:[...]} that match text (case-insensitive). Hints only: always read in context."""
    if not isinstance(table,dict):return []
    return [p for p in [*table.get('*',[]),*table.get(locale,[])] if re.search(p,text,re.I)]

def source_file(source, project_dir, product_dir):
    """Resolve explicit file:/product: sources and recognizable legacy file paths.
    URLs, ASINs and listing references remain evidence references, not file paths.
    """
    if re.match(r'^[a-zA-Z]+://',source):return None
    root=Path(project_dir or '.').resolve()
    product_root=Path(product_dir).expanduser() if nonempty(product_dir) else None
    if product_root is not None and not product_root.is_absolute():product_root=root/product_root
    legacy_bare=False
    if source.startswith('product:'):
        if not nonempty(product_dir):raise ValueError('product: source requires plan.productDir')
        root=product_root
        raw=source[8:]
    elif source.startswith('file:'):raw=source[5:]
    else:
        raw=source
        legacy_bare=not raw.startswith(('./','../','/','~/'))
        if not (raw.startswith(('./','../','/','~/')) or re.search(FILE_EXT+r'(?:[:#].*)?$',raw,re.I)):
            return None
    raw=re.sub(r'(?::\d+(?::\d+)?|#(?:L|p\.?|page=)\d+(?:-L?\d+)?)$','',raw)
    if not raw.strip():raise ValueError('empty file source')
    path=Path(raw).expanduser()
    if path.is_absolute():return path
    candidate=root/path
    if legacy_bare and not candidate.is_file() and product_root is not None:
        alternative=product_root/path
        if alternative.is_file():return alternative
    return candidate


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def pacing_metrics(video, fps, duration, shots):
    """Frame-difference pacing: share of near-still frames, longest still run, hard changes. Needs ffmpeg."""
    graph='scale=480:-2,format=gray,tblend=all_mode=difference,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-'
    proc=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(video),'-an','-vf',graph,'-f','null','-'],capture_output=True,text=True,check=True)
    values=[float(m) for m in re.findall(r'lavfi\.signalstats\.YAVG=([-+0-9.eE]+)',proc.stdout)]
    if not values:raise ValueError('no frame statistics')
    still=[v<0.15 for v in values]
    runs=[];start=None
    for i,flag in enumerate(still+[False]):
        if flag and start is None:start=i
        elif not flag and start is not None:runs.append((start,i));start=None
    def shot_at(t):
        return next((str(s.get('id')) for s in shots if isinstance(s,dict) and number(s.get('start')) and s['start']<=t<s.get('end',0)),None)
    tail=duration-1.0
    body=[r for r in runs if (r[1]+1)/fps<tail] or runs
    longest=max(body,key=lambda r:r[1]-r[0],default=(0,0))
    return {'frames':len(values),'stillRatio':round(sum(still)/len(values),3),'movingRatio':round(sum(v>1.5 for v in values)/len(values),3),
        'hardChanges':sum(v>12 for v in values),'meanDiff':round(sum(values)/len(values),3),
        'longestStill':{'seconds':round((longest[1]-longest[0])/fps,2),'at':round((longest[0]+1)/fps,2),'shot':shot_at((longest[0]+1)/fps)},
        'thresholds':{'still':0.15,'moving':1.5,'hardChange':12,'note':'mean absolute luma difference between consecutive frames at 480px width'}}


PRODUCT_TYPES=['detail','macro','spec','install','usage','lifestyle']
SHOT_TYPES=['title',*PRODUCT_TYPES,'montage','end']
GENERIC_ACCENTS=['NEW','NEW ITEM','PRODUCT','FEATURE','POINT','CHECK']


def normalize(plan):
    """Language view of a plan: versions, fonts and per-shot copy.

    Current plans list versions [{id, locale, channel, accent}] and keep copy per locale in shot.copy[locale].
    Legacy single-language plans (headline/headlineEn/description, typography.jaFont/enFont) map to one ja version
    whose English headline becomes the accent, so existing projects keep working.
    """
    typo=plan.get('typography') if isinstance(plan.get('typography'),dict) else {}
    view={'exception':nonempty(typo.get('exceptionReason')),'legacy':plan.get('versions') is None}
    if view['legacy']:
        view['versions']=[{'id':'ja','locale':'ja','channel':plan.get('channel') or 'amazon-jp','accent':'en' if typo.get('mode')=='bilingual' else None}]
        view['fonts']={k:v for k,v in [('ja',typo.get('jaFont')),('en',typo.get('enFont'))] if v}
        view['cjkStyle']=typo.get('jaStyle')
    else:
        view['versions']=plan['versions']
        view['fonts']=typo.get('fonts') if isinstance(typo.get('fonts'),dict) else {}
        view['cjkStyle']=typo.get('cjkStyle')
    return view


def shot_copy(shot, locale, view):
    if view['legacy']:
        return {'headline':shot.get('headline'),'accent':shot.get('headlineEn'),'description':shot.get('description'),'plainExplanation':shot.get('plainExplanation')}
    copy=shot.get('copy')
    return copy.get(locale) if isinstance(copy,dict) and isinstance(copy.get(locale),dict) else None


def category_key(plan, view):
    """Legacy plans predate categories and were all motorcycle parts."""
    key=plan.get('category')
    if key is None and view['legacy']:return 'motorcycle-parts'
    return key if isinstance(key,str) and not key.startswith('_') else None


def reading_load(text, locale):
    """Characters to read: CJK counts characters without whitespace, Latin scripts count characters with single spaces."""
    if LOCALES[locale]['script']=='cjk':return len(''.join(text.split()))
    return len(' '.join(text.split()))


def direction_checks(plan, errors, warnings, project_dir):
    """Production films start from a written direction: concept choice, derived devices, frame system, shot list."""
    if plan.get('demo') is not False:return
    path=Path(project_dir or '.')/'DIRECTION.md'
    if not path.is_file():
        errors.append('Production film needs DIRECTION.md (references/direction.md): concept, derived devices, frame system, shot list');return
    text=path.read_text(encoding='utf-8',errors='replace')
    rows=[l for l in text.splitlines() if l.strip().startswith('|') and not set(l.replace('|','').strip())<=set('-: ')]
    if len(rows)<len(plan.get('shots',[]))+1:
        warnings.append('DIRECTION.md shot table looks incomplete; every plan shot should have picture, focal element, copy and sound')
    if not any(word in text.lower() for word in ['因为','because','weil','parce que','ので','ため']):
        warnings.append('DIRECTION.md does not say why each device fits this product; derive devices from the product, not from a previous film')


def version_checks(view, errors, warnings, production):
    """Each version is one language cut for one channel; fonts and channel expectations are checked per version."""
    issue=errors if production else warnings
    versions=view['versions']
    if not isinstance(versions,list) or not versions or not all(isinstance(v,dict) for v in versions):
        errors.append('versions must be a nonempty array of {id, locale, channel}');return []
    ids=[v.get('id') for v in versions]
    if not all(nonempty(i) for i in ids) or len(set(ids))!=len(ids):errors.append('Every version needs a unique id')
    usable=[]
    for v in versions:
        vid=str(v.get('id'));locale=v.get('locale');accent=v.get('accent')
        if locale not in LOCALES:
            issue.append(vid+': unsupported locale '+repr(locale)+'; add it to scripts/data/locales.json and references/locales/ first');continue
        if accent is not None and accent not in LOCALES:
            issue.append(vid+': unsupported accent locale '+repr(accent));accent=None
        channel=v.get('channel') or 'other'
        if channel not in CHANNELS:warnings.append(vid+': unknown channel '+repr(channel)+'; only generic wording checks apply')
        rules=CHANNELS.get(channel,CHANNELS['other'])
        if rules['languages'] and locale not in rules['languages']:
            warnings.append(vid+': '+rules['name']+' customers read '+'/'.join(rules['languages'])+'; '+rules.get('languageNote','confirm the user chose this language for this marketplace'))
        if accent and rules.get('accentNote'):warnings.append(vid+': '+rules['accentNote'])
        if not view['exception']:
            for lang in [locale,*([accent] if accent else [])]:
                if not nonempty(view['fonts'].get(lang)):issue.append(vid+': specify a '+LOCALES[lang]['name']+' font in typography.fonts.'+lang)
            if accent and LOCALES[locale]['script']!=LOCALES[accent]['script'] and view['fonts'].get(locale)==view['fonts'].get(accent):
                issue.append(vid+': specify separate '+LOCALES[locale]['name']+' and '+LOCALES[accent]['name']+' fonts; do not let fallback pick glyphs')
            if LOCALES[locale]['script']=='cjk' and view['cjkStyle']!='sans-serif':
                issue.append(vid+': '+LOCALES[locale]['name']+' headings default to sans-serif (Gothic / 黑体); do not mix serif and sans lines')
        usable.append({'id':vid,'locale':locale,'accent':accent,'channel':channel,'rules':rules})
    return usable


FR_SPACE=re.compile(r'\x20[?!:;»]|«\x20|[^\s  \d][?!;]|[^\s  \d/]:(?![\d/])')


def copy_checks(plan, shot, label, versions, view, errors, warnings, production):
    """On-screen copy of one shot in every version: presence, reading time, wording, channel and category hints."""
    issue=errors if production else warnings
    category=CATEGORIES.get(category_key(plan,view))
    appeared=shot.get('descriptionAt',0)
    readable=shot['end']-shot['start']-appeared if number(appeared) and 0<=appeared<shot['end']-shot['start'] else None
    for v in versions:
        locale=v['locale'];tag=label+' ['+v['id']+']'
        copy=shot_copy(shot,locale,view)
        if copy is None:issue.append(tag+' has no copy.'+locale);continue
        if not nonempty(copy.get('headline')):errors.append(tag+' is missing its headline')
        desc=copy.get('description','')
        if not isinstance(desc,str):errors.append(tag+' description must be text');desc=''
        if readable and reading_load(desc,locale)/readable>LOCALES[locale]['readingRate']:
            warnings.append(tag+' description may be too fast to read ('+LOCALES[locale]['readingNote']+'); inspect actual reading time')
        accent=copy.get('accent','')
        if v['accent'] and not view['exception'] and shot.get('type') in ['title',*PRODUCT_TYPES,'end']:
            letters=r'[A-Za-zÀ-ÿ]' if LOCALES[v['accent']]['script']=='latin' else r'[^\x00-\x7f]'
            if not isinstance(accent,str) or not re.search(letters,accent) or accent.strip().upper() in GENERIC_ACCENTS:
                issue.append(tag+' needs a meaningful '+LOCALES[v['accent']]['name']+' accent headline, not a decorative generic label')
        if shot.get('claim'):
            if not nonempty(copy.get('plainExplanation')):issue.append(tag+' needs a plain explanation of object, action and observable result')
            if not nonempty(desc):issue.append(tag+' lacks an on-screen explanation')
        text=' '.join(str(copy.get(k) or '') for k in ['headline','accent','description'])
        if any(re.search(term,text,re.I) for term in LOCALES[locale].get('vague',[])):
            warnings.append(tag+' may contain vague promotional language; perform the plain-language read-through')
        rules=v['rules']
        for kind in [*rules['reject'],*rules['caution']]:
            found=hits(CLAIMS[kind]['patterns'],locale,text)
            if found:
                verdict='usually rejects this' if kind in rules['reject'] else 'needs evidence or rewording for this'
                warnings.append(tag+' on-screen text looks like '+CLAIMS[kind]['label']+' ('+found[0]+'); '+rules['name']+' '+verdict+(' ('+rules['doc']+')' if rules.get('doc') else ''))
        if category:
            found=hits(category.get('sourceRequired'),locale,text)
            if found and not shot.get('source'):
                issue.append(tag+' states a certification/performance term ('+found[0]+') without a source (spec sheet, test report)')
            restricted=category.get('restricted')
            found=hits(restricted.get('patterns'),locale,text) if restricted else []
            if found:warnings.append(tag+' '+restricted['label']+' ('+found[0]+'); see '+category['doc'])
        long_word=LOCALES[locale].get('longWord')
        if long_word and any(len(w)>=long_word for w in re.findall(r'[^\W\d_]+',str(copy.get('headline') or ''))):
            warnings.append(tag+' headline has a very long word; set lang="'+locale+'" with hyphens:auto or a soft hyphen, and check the line break in stills')
        if LOCALES[locale].get('nbspBefore') and FR_SPACE.search(text):
            warnings.append(tag+' French punctuation: use a no-break space (U+202F/U+00A0) before ? ! ; : and inside « » so marks never wrap alone')


def creative_checks(plan, errors, warnings, project_dir, mix_report, final_video, plan_path):
    production = plan.get('demo') is False
    issue = errors if production else warnings
    if plan.get('typography') is not None and not isinstance(plan.get('typography'),dict):
        issue.append('typography must describe language/font roles')
    view=normalize(plan)
    versions=version_checks(view,errors,warnings,production)
    category=plan.get('category')
    if category is None and view['legacy']:
        warnings.append('Legacy single-language plan: checked as ja + motorcycle-parts; add versions/category when it is next edited')
    elif category is None:
        issue.append('plan.category is not set; read the matching references/categories/ notes and record the choice')
    elif not isinstance(category,str) or category not in CATEGORIES or category.startswith('_'):
        warnings.append('Unknown category '+repr(category)+'; only generic source checks apply. Start from references/categories/_template.md')
    if production:
        if not any(isinstance(s,dict) and s.get('claim') is True for s in plan['shots']):
            errors.append('Production promo needs at least one evidenced product claim')
        if plan.get('audioRequired') is False and not nonempty(plan.get('audioExceptionReason')):
            errors.append('Disabling audio needs audioExceptionReason documenting the user request')
    actions={};required=set()
    for shot in plan['shots']:
        if not isinstance(shot,dict):continue
        label=str(shot.get('id','shot'))
        if production and shot.get('type') in PRODUCT_TYPES and not nonempty(shot.get('asset')):
            errors.append(label+' needs a real product photo/asset path for its product visual')
        if number(shot.get('start')) and number(shot.get('end')) and shot['end']>shot['start']:
            copy_checks(plan,shot,label,versions,view,errors,warnings,production)
        for action in shot.get('actions',[]) if isinstance(shot.get('actions'),list) else []:
            if not isinstance(action,dict):issue.append(label+' has malformed action');continue
            aid=action.get('id')
            if not isinstance(aid,str) or not aid or aid in actions:issue.append(label+' needs unique action IDs');continue
            at=action.get('at')
            if not number(at) or not number(shot.get('start')) or not number(shot.get('end')) or not 0<=at<shot['end']-shot['start']:
                issue.append(label+' has action outside shot');continue
            actions[aid]=shot['start']+at
            if action.get('soundRequired'):required.add(aid)
    sfx_required=plan.get('audioRequired') and plan.get('sfxRequired',True)
    if plan.get('audioRequired') and plan.get('sfxRequired') is False and not plan.get('audioExceptionReason'):
        issue.append('Disabling SFX needs the user-requested reason, not an agent shortcut')
    audio=plan.get('audio',{})
    if not isinstance(audio,dict):issue.append('audio must be an object');audio={}
    cues=audio.get('cues',[])
    if not isinstance(cues,list):issue.append('audio.cues must be an array');cues=[]
    linked=set()
    if sfx_required:
        if not required:issue.append('Mark key state changes with soundRequired; do not leave all key actions silent')
        if not cues:issue.append('Missing SFX cues; a music track alone is insufficient')
        music=audio.get('music',{})
        if not isinstance(music,dict) or not music.get('file'):issue.append('Record BGM separately from SFX')
        for cue in cues:
            if not isinstance(cue,dict):issue.append('Malformed SFX cue');continue
            aid=cue.get('actionId')
            if not isinstance(aid,str) or aid not in actions:issue.append('SFX cue needs a known actionId');continue
            if cue.get('role')!='sfx' or not isinstance(cue.get('file'),str) or not cue['file'].strip():issue.append('SFX cue needs role=sfx and an actual file')
            offset=cue.get('syncOffset',0)
            if not number(offset) or offset<0 or not number(cue.get('at')) or abs(cue['at']+offset-actions[aid])>2/plan['fps']:issue.append('SFX audible landmark must align with its action within two frames')
            if not number(cue.get('gain',1)) or not 0<cue.get('gain',1)<=4:issue.append('SFX gain must be in (0,4]')
            linked.add(aid)
        kinds={c.get('kind',Path(c.get('file','')).stem) for c in cues if isinstance(c,dict)}
        if plan['duration']>=30 and len(kinds)<3:warnings.append('Long promo has fewer than three SFX roles; review sound variety rather than repeating one chime')
        if required-linked:issue.append('Key actions without SFX: '+', '.join(sorted(required-linked)))
        if production and final_video and mix_report is None:errors.append('Final video needs --mix-report evidence of BGM + SFX assembly; audio stream existence is insufficient')
    if mix_report is not None:
        try:
            report=json.loads(Path(mix_report).read_text(encoding='utf-8'))
            base=Path(project_dir)
            def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
            if report.get('planSha256')!=digest(Path(plan_path) if plan_path else base/'plan.json'):errors.append('Mix report is stale for the current plan')
            if report.get('cues') is None or [{k:v for k,v in c.items() if k!='sha256'} for c in report['cues']]!=cues:
                errors.append('Mix report cues differ from plan')
            if sfx_required and not report.get('ducking') and not audio.get('ducking',{}).get('reason'):errors.append('Missing music ducking evidence')
            for item in report.get('timing',[]):
                if abs(item.get('beatErrorFrames',0))>2:warnings.append(item['actionId']+' is off its requested beat; adjust picture and audio together')
            for entry in [report['master'],report['sfxStem'],report['music'],*([report['musicStem']] if 'musicStem' in report else []),*report['cues']]:
                if digest(base/entry['file'])!=entry['sha256']:errors.append('Mix asset hash mismatch: '+entry['file'])
            warnings.append('Mix inputs/stem/master verified; listen to SFX audibility and verify this master was used in the final export')
        except (OSError,ValueError,KeyError,TypeError) as exc:errors.append('Invalid mix evidence: '+str(exc))


def check(plan, video=None, project_dir=None, mix_report=None, plan_path=None):
    errors, warnings = [], []
    result = {'errors':errors, 'warnings':warnings, 'limits':['Wording hints are keyword matches per locale, not legal review','No semantic verification of feature claims', 'No visual clipping or taste assessment', 'No listening or sound cue alignment assessment', 'Pacing numbers are hints for where to look, not a quality score']}
    if not isinstance(plan, dict):
        errors.append('plan must be an object')
        return result
    for field in ['duration','fps','width','height']:
        if not number(plan.get(field)) or plan[field] <= 0:
            errors.append(field+' must be a positive finite number')
    if errors:
        return result
    for field in ['width','height']:
        if int(plan[field]) != plan[field] or int(plan[field]) % 2:
            errors.append(field+' must be an even integer for yuv420p')
    if plan.get('style') not in ['brand','default','hybrid']:
        errors.append('style must be brand/default/hybrid')
    if not isinstance(plan.get('audioRequired'), bool):
        errors.append('audioRequired must explicitly be true or false')
    if plan.get('demo', True):
        warnings.append('Technical demo; not a completed promotional film')
    shots = plan.get('shots')
    if not isinstance(shots, list) or not shots:
        errors.append('shots must be a nonempty array')
        return result
    tolerance = .5/plan['fps']
    cursor = 0
    ids=set()
    types=set()
    for idx,s in enumerate(shots):
        label='shot '+str(idx+1)
        if not isinstance(s,dict):
            errors.append(label+' must be an object');continue
        if not isinstance(s.get('id'),str) or not s['id'] or s['id'] in ids:
            errors.append(label+' requires a unique nonempty id')
        else:
            ids.add(s['id']);label=s['id']
        if not all(number(s.get(k)) for k in ['start','end']) or s.get('end',0)<=s.get('start',0):
            errors.append(label+' has invalid timing');continue
        if abs(s['start']-cursor)>tolerance:
            errors.append(label+' creates a timeline gap/overlap; shots must cover the timeline in order')
        cursor=s['end']
        if s.get('type') in SHOT_TYPES:
            types.add(s['type'])
        else:
            warnings.append(label+' has custom/missing type; review shot variety')
        if not isinstance(s.get('claim'),bool):
            errors.append(label+' must explicitly identify whether it makes a feature claim')
        sources=s.get('source')
        if s.get('claim') and (not isinstance(sources,list) or not sources or not all(isinstance(x,str) and x.strip() for x in sources)):
            errors.append(label+' claims a feature without a source array')
        if plan.get('demo') is False and isinstance(sources,list):
            for source in sources:
                if not nonempty(source):continue
                try:
                    resolved=source_file(source,project_dir,plan.get('productDir'))
                    if resolved is not None and not resolved.is_file():errors.append(label+' source file missing: '+source)
                except ValueError as exc:errors.append(label+' invalid source: '+str(exc))
        appeared=s.get('descriptionAt',0)
        if not number(appeared) or appeared<0 or appeared>=s['end']-s['start']:
            errors.append(label+' has invalid descriptionAt')
        if not isinstance(s.get('actions'),list) or not s['actions']:
            warnings.append(label+' has no recorded action beats')
    if abs(cursor-plan['duration'])>tolerance:
        errors.append('shots do not end at declared duration')
    if len(shots)>3 and len(types)<2:
        warnings.append('All shots use one layout type; review visual rhythm')
    creative_checks(plan, errors, warnings, project_dir, mix_report, bool(video), plan_path)
    direction_checks(plan, errors, warnings, project_dir)
    if video:
        try:
            proc=subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)],capture_output=True,text=True,check=True)
            meta=json.loads(proc.stdout)
            streams=meta.get('streams',[])
            videos=[s for s in streams if s.get('codec_type')=='video']
            audios=[s for s in streams if s.get('codec_type')=='audio']
            result['media']={'format':meta.get('format',{}),'video':videos,'audio':audios}
            if not videos:
                errors.append('No video stream')
            else:
                stream=videos[0]
                for dim in ['width','height']:
                    if stream.get(dim)!=plan[dim]:errors.append('Video '+dim+' differs from plan')
                rate=float(Fraction(stream.get('avg_frame_rate','0/1')))
                if abs(rate-plan['fps'])>.02:errors.append('Video frame rate differs from plan')
                duration=float(stream.get('duration',meta['format'].get('duration',0)))
                if abs(duration-plan['duration'])>max(.1,2/plan['fps']):errors.append('Video duration differs from plan')
            if plan.get('audioRequired') and not audios:
                errors.append('Music/SFX required but audio stream missing')
            elif audios:
                ad=float(audios[0].get('duration',meta['format'].get('duration',0)))
                if ad+0.2<plan['duration']:warnings.append('Audio stream ends before the video; inspect ending')
                warnings.append('Audio stream exists; loudness, audibility and synchronization still need review')
            if videos:
                try:
                    pacing=pacing_metrics(video,plan['fps'],plan['duration'],shots)
                    result['pacing']=pacing
                    run=pacing['longestStill']
                    if run['seconds']>3:warnings.append(f"{run['seconds']}s nearly still around {run['at']}s ({run['shot']}); watch it: reading pause, or missing continuation? (hint only)")
                except (subprocess.CalledProcessError,ValueError) as exc:warnings.append('Pacing statistics unavailable: '+str(exc))
        except (OSError,subprocess.CalledProcessError,ValueError,KeyError,ZeroDivisionError) as exc:
            errors.append('Could not inspect media: '+str(exc))
    return result


def main():
    # JSON reports carry CJK and typographic characters; Windows consoles default to a legacy code page.
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('plan',type=Path)
    p.add_argument('--video',type=Path)
    p.add_argument('--mix-report',type=Path)
    args=p.parse_args()
    try:
        result=check(json.loads(args.plan.read_text(encoding='utf-8')),args.video,args.plan.resolve().parent,args.mix_report,args.plan)
    except (OSError,ValueError) as exc:
        result={'errors':[str(exc)],'warnings':[]}
    result['ok']=not result['errors']
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(0 if result['ok'] else 1)

if __name__=='__main__':
    main()
