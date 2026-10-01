"""Offline regressions for delivery gates, init and headless-only preflight."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import shutil
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
delivery=module('check_delivery');environment=module('check_environment')
class Delivery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        (self.root/'evidence.md').write_text('Spec sheet fixture',encoding='utf-8')
        (self.root/'DIRECTION.md').write_text('# 方向\n因为商品是防水シートバッグ，所以镜头推近止水拉链。\n| # | 镜头 |\n|---|---|\n| 1 | detail |\n',encoding='utf-8')
        self.plan={'demo':False,'style':'brand','channel':'amazon-jp','duration':5,'fps':30,'width':1920,'height':1080,'audioRequired':False,'audioExceptionReason':'User requested a silent version',
            'typography':{'mode':'bilingual','jaStyle':'sans-serif','jaFont':'Noto Sans JP','enFont':'Inter'},
            'shots':[{'id':'detail','start':0,'end':5,'type':'detail','headline':'荷物を、しっかり固定','headlineEn':'Locked in','claim':True,'source':['file:evidence.md'],
                'plainExplanation':'付属のベルトでシートに固定でき、走行中も荷物がずれにくい。','description':'付属ベルトでシートに固定。','asset':'assets/photos/bag.png','actions':[]}]}
    def check(self):return delivery.check(self.plan,project_dir=self.root)
    def errors(self):return self.check()['errors']
    def test_valid_production(self):self.assertEqual(self.errors(),[])
    def test_all_claims_false(self):
        self.plan['shots'][0]['claim']=False;self.assertTrue(any('at least one' in x for x in self.errors()))
    def test_demo_still_allowed(self):
        self.plan['demo']=True;self.plan['shots'][0]['claim']=False;self.assertEqual(self.errors(),[])
    def test_product_assets_required(self):
        for kind in ['detail','macro','spec','install','lifestyle']:
            for value in [None,'','   ']:
                with self.subTest(kind=kind,value=value):
                    self.plan['shots'][0].update(type=kind,asset=value)
                    self.assertTrue(any('product photo' in x for x in self.errors()))
    def test_japanese_typography_required(self):
        self.plan['typography']={'mode':'bilingual','zhStyle':'sans-serif','zhFont':'A','enFont':'B'}
        self.assertTrue(any('font' in x for x in self.errors()))
    def test_audio_exception_required(self):
        for value in [None,'','   ',True]:
            self.plan['audioExceptionReason']=value
            self.assertTrue(any('audioExceptionReason' in x for x in self.errors()))
    def test_source_files_resolve(self):
        for source in ['file:missing.md','./missing.md','product:missing.pdf']:
            self.plan['shots'][0]['source']=[source];self.assertTrue(self.errors())
        self.plan['productDir']=str(self.root)
        for source in ['product:evidence.md:2','file:evidence.md#L3','evidence.md','evidence.md#p3']:
            self.plan['shots'][0]['source']=[source];self.assertEqual(self.errors(),[])
    def test_bare_paths_search_video_then_product_dir(self):
        product=self.root/'product';(product/'spec').mkdir(parents=True)
        (product/'spec/sheet.pdf').write_bytes(b'%PDF-1.4')
        (product/'listing.txt').write_text('Listing',encoding='utf-8')
        self.plan['productDir']='product'
        self.plan['shots'][0]['source']=['spec/sheet.pdf#p2','listing.txt']
        self.assertEqual(self.errors(),[])
        self.assertEqual(delivery.source_file('listing.txt',self.root,'product'),product/'listing.txt')
        (self.root/'listing.txt').write_text('Video evidence',encoding='utf-8')
        self.assertEqual(delivery.source_file('listing.txt',self.root,'product'),self.root/'listing.txt')
        self.plan['shots'][0]['source']=['missing.md'];self.assertTrue(self.errors())
    def test_explicit_source_roots_do_not_fall_back(self):
        product=self.root/'product';product.mkdir();(product/'spec.md').write_text('Spec',encoding='utf-8')
        self.plan['productDir']=str(product)
        for source in ['file:spec.md','./spec.md','../spec.md']:
            self.plan['shots'][0]['source']=[source];self.assertTrue(self.errors())
        self.plan['shots'][0]['source']=['product:spec.md'];self.assertEqual(self.errors(),[])
    def test_production_requires_direction(self):
        (self.root/'DIRECTION.md').unlink()
        self.assertTrue(any('DIRECTION.md' in x for x in self.errors()))
        self.plan['demo']=True;self.assertFalse(any('DIRECTION.md' in x for x in self.errors()))
    def test_direction_without_reasons_warns(self):
        (self.root/'DIRECTION.md').write_text('| # | 镜头 |\n|---|---|\n| 1 | detail |\n',encoding='utf-8')
        self.assertTrue(any('derive devices' in w for w in self.check()['warnings']))
    def test_external_evidence_not_treated_as_file(self):
        self.plan['shots'][0]['source']=['https://example.org/spec.pdf','asin:B000000000'];self.assertEqual(self.errors(),[])
    def test_amazon_jp_wording_warns(self):
        for text in ['今だけ送料無料','楽天ランキングNo.1','3,980円','詳しくは www.example.jp','最強の積載力']:
            with self.subTest(text=text):
                self.plan['shots'][0]['description']=text
                self.assertTrue(any('Amazon.co.jp' in w for w in self.check()['warnings']))
        self.plan['channel']='youtube';self.plan['shots'][0]['description']='今だけ送料無料'
        self.assertFalse(any('Amazon.co.jp' in w for w in self.check()['warnings']))
    def test_certification_terms_need_source(self):
        self.plan['shots'][0].update(description='車検対応のステンレス製。',claim=False,source=[])
        self.plan['shots'].append(dict(self.plan['shots'][0],id='proof',start=5,end=6,claim=True,source=['file:evidence.md'],description='付属ベルトで固定。'))
        self.plan['duration']=6
        self.assertTrue(any('certification' in x for x in self.errors()))
class Preflight(unittest.TestCase):
    def probe(self,project,launch_ok=True):
        def fake_run(args,cwd=None,timeout=30):
            out=''
            if '--version' in args:out='v22.0.0' if 'node' in args[0] else '10.0.0'
            elif '-version' in args:out='ffmpeg 8'
            elif '-filters' in args:out='volume adelay amix loudnorm afade aresample asetnsamples'
            elif '-encoders' in args:out='libx264 aac'
            elif '-e' in args:
                js=args[args.index('-e')+1]
                if 'chromium.launch' in js:
                    if not launch_ok:return {'ok':False,'stdout':'','stderr':'Permission denied','output':'Permission denied'}
                else:
                    self.assertNotIn('executablePath()',js)
                    out=json.dumps({k:{'version':'1.0','path':'/unavailable/'+k} for k in ['playwright','gsap']})
            return {'ok':True,'stdout':out,'stderr':'','output':out}
        with patch.object(environment,'run',side_effect=fake_run),patch.object(environment.shutil,'which',side_effect=lambda n:'/bin/'+n),patch('sys.argv',['check_environment','--project',str(project)]),contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaises(SystemExit) as caught:environment.main()
        return caught.exception.code,json.loads(output.getvalue())
    def test_headless_only_and_cache_revalidation(self):
        with tempfile.TemporaryDirectory() as d:
            code,result=self.probe(Path(d));self.assertEqual(code,0);self.assertTrue(result['ready']);self.assertTrue(result['browser']['launched'])
            code,result=self.probe(Path(d));self.assertTrue(result['cached'])
            code,result=self.probe(Path(d),False);self.assertEqual(code,1);self.assertFalse(result['cached']);self.assertIn('browser-launch',result['missing'])
class Init(unittest.TestCase):
    def init(self,d,*extra):
        project=Path(d)/'video'
        subprocess.run([sys.executable,str(ROOT/'scripts/init_project.py'),'--output',str(project),*extra],capture_output=True,check=True)
        return project
    def test_product_dir_recorded_and_demo_not_promotable(self):
        with tempfile.TemporaryDirectory() as d:
            product=Path(d)/'product';product.mkdir()
            project=self.init(d,'--style','default','--category','electronics','--product-dir',str(product))
            plan=json.loads((project/'plan.json').read_text(encoding='utf-8'))
            self.assertEqual(plan['productDir'],str(product.resolve()))
            self.assertEqual(plan['versions'],[{'id':'en-us','locale':'en','channel':'amazon-us','accent':None}])
            self.assertIn(str(product.resolve()),(project/'BRIEF.md').read_text(encoding='utf-8'))
            self.assertEqual(delivery.check(plan,project_dir=project)['errors'],[])
            plan['demo']=False
            self.assertTrue(any('at least one' in e for e in delivery.check(plan,project_dir=project)['errors']))
    def test_init_writes_direction_questions_not_answers(self):
        with tempfile.TemporaryDirectory() as d:
            project=self.init(d,'--style','brand','--brand','moto boite','--category','motorcycle-parts')
            text=(project/'DIRECTION.md').read_text(encoding='utf-8')
            for heading in ['参考拆解','商品气质','三个方向','选择与理由','画面规范','镜头表']:self.assertIn(heading,text)
            self.assertIn('不要照抄',text)
            self.assertIn('适配车型',(project/'evidence/product-facts.md').read_text(encoding='utf-8'))
            self.assertTrue((project/'assets/photos').is_dir())
    def test_multiple_locales_get_versions_fonts_and_copy(self):
        with tempfile.TemporaryDirectory() as d:
            project=self.init(d,'--style','default','--category','beauty','--locales','en,ja,de,fr,zh-Hans')
            plan=json.loads((project/'plan.json').read_text(encoding='utf-8'))
            self.assertEqual([(v['id'],v['channel'],v['accent']) for v in plan['versions']],
                [('en-us','amazon-us',None),('ja-jp','amazon-jp','en'),('de-de','amazon-de',None),('fr-fr','amazon-fr',None),('zh-Hans','other','en')])
            self.assertEqual(set(plan['typography']['fonts']),{'en','ja','de','fr','zh-Hans'})
            self.assertEqual(plan['typography']['cjkStyle'],'sans-serif')
            for shot in plan['shots']:self.assertEqual(set(shot['copy']),{'en','ja','de','fr','zh-Hans'})
            self.assertNotIn('accent',plan['shots'][0]['copy']['en'])
            self.assertIn('accent',plan['shots'][0]['copy']['ja'])
            self.assertIn('INCI',(project/'evidence/product-facts.md').read_text(encoding='utf-8'))
            self.assertEqual(delivery.check(plan,project_dir=project)['errors'],[])
    def test_explicit_channels_follow_locale_order(self):
        with tempfile.TemporaryDirectory() as d:
            project=self.init(d,'--style','default','--category','electronics','--locales','en,de','--channels','amazon-uk,amazon-de')
            plan=json.loads((project/'plan.json').read_text(encoding='utf-8'))
            self.assertEqual([v['id'] for v in plan['versions']],['en-uk','de-de'])
    def test_invalid_arguments_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            for extra in [['--style','brand','--category','beauty'],['--style','default'],['--style','default','--category','beauty','--locales','es'],
                          ['--style','default','--category','beauty','--locales','en,ja','--channels','amazon-us'],
                          ['--style','default','--category','beauty','--channels','amazon-xx']]:
                with self.subTest(extra=extra):
                    r=subprocess.run([sys.executable,str(ROOT/'scripts/init_project.py'),'--output',str(Path(d)/'v'),*extra],capture_output=True)
                    self.assertNotEqual(r.returncode,0)
class Versions(unittest.TestCase):
    """Multi-language plans: one timeline, copy per locale, rules per version."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name).resolve()
        (self.root/'facts.md').write_text('Spec sheet fixture',encoding='utf-8')
        (self.root/'DIRECTION.md').write_text('# Direction\nBecause the charger folds flat, the opener pushes in on the hinge.\n| # | shot |\n|---|---|\n| 1 | detail |\n',encoding='utf-8')
        self.plan={'demo':False,'style':'default','category':'electronics','duration':5,'fps':30,'width':1920,'height':1080,'audioRequired':False,'audioExceptionReason':'User requested a silent version',
            'versions':[{'id':'en-us','locale':'en','channel':'amazon-us'},{'id':'ja-jp','locale':'ja','channel':'amazon-jp','accent':'en'},
                        {'id':'de-de','locale':'de','channel':'amazon-de'},{'id':'fr-fr','locale':'fr','channel':'amazon-fr'}],
            'typography':{'fonts':{'en':'Inter','ja':'Noto Sans JP','de':'Inter','fr':'Inter'},'cjkStyle':'sans-serif'},
            'shots':[{'id':'detail','start':0,'end':5,'type':'detail','claim':True,'source':['file:facts.md'],'asset':'assets/photos/charger.png','actions':[],
                'copy':{'en':{'headline':'Folds flat','description':'The plug folds into the body, so it slips into a pocket.','plainExplanation':'The plug folds into the body.'},
                        'ja':{'headline':'プラグを折りたためる','accent':'Folds flat','description':'プラグが本体に収まり、ポケットに入れやすい。','plainExplanation':'プラグを本体に折りたたんで収納できる。'},
                        'de':{'headline':'Flach zusammenklappbar','description':'Der Stecker klappt ins Gehäuse und passt in jede Tasche.','plainExplanation':'Der Stecker lässt sich einklappen.'},
                        'fr':{'headline':'Se replie à plat','description':'La fiche se range dans le boîtier et tient dans une poche.','plainExplanation':'La fiche se replie.'}}}]}
    def check(self):return delivery.check(self.plan,project_dir=self.root)
    def copy(self,locale):return self.plan['shots'][0]['copy'][locale]
    def test_valid_multilingual_production(self):
        result=self.check();self.assertEqual(result['errors'],[])
        self.assertFalse(any('too fast' in w for w in result['warnings']))
    def test_missing_locale_copy_is_error(self):
        del self.plan['shots'][0]['copy']['de']
        self.assertTrue(any('[de-de] has no copy.de' in e for e in self.check()['errors']))
    def test_reading_rate_is_per_script(self):
        self.copy('en')['description']='x'*90
        self.assertTrue(any('[en-us]' in w and 'too fast' in w for w in self.check()['warnings']))
        self.copy('ja')['description']='あ'*40
        self.assertTrue(any('[ja-jp]' in w and 'too fast' in w for w in self.check()['warnings']))
    def test_channel_wording_per_locale(self):
        cases={'en':('Free shipping today only','Amazon.com'),'de':('Jetzt kaufen, versandkostenfrei','Amazon.de'),
               'fr':('Livraison gratuite','Amazon.fr'),'ja':('今だけ送料無料','Amazon.co.jp')}
        for locale,(text,market) in cases.items():
            with self.subTest(locale=locale):
                before=self.copy(locale)['description'];self.copy(locale)['description']=text
                self.assertTrue(any(market in w and 'promotion' in w for w in self.check()['warnings']))
                self.copy(locale)['description']=before
    def test_green_claims_flagged(self):
        self.copy('de')['description']='Klimaneutral hergestellt.'
        self.assertTrue(any('[de-de]' in w and 'environmental' in w for w in self.check()['warnings']))
    def test_language_and_toubon_warnings(self):
        self.plan['versions'][3]['locale']='en';self.plan['shots'][0]['copy']['en']=self.copy('en')
        self.assertTrue(any('Loi Toubon' in w for w in self.check()['warnings']))
        self.plan['versions'][3].update(locale='fr',accent='en')
        self.assertTrue(any('Loi Toubon' in w for w in self.check()['warnings']))
    def test_french_spacing_and_german_long_words(self):
        self.copy('fr')['headline']='Pourquoi ?'
        self.assertTrue(any('French punctuation' in w for w in self.check()['warnings']))
        self.copy('fr')['headline']='Pourquoi ?'
        self.assertFalse(any('French punctuation' in w for w in self.check()['warnings']))
        self.copy('de')['headline']='Schnellladegerätesteckerkabel'
        self.assertTrue(any('long word' in w for w in self.check()['warnings']))
    def test_fonts_required_and_cjk_separate(self):
        self.plan['typography']['fonts']['ja']='Inter'
        self.assertTrue(any('separate' in e for e in self.check()['errors']))
        del self.plan['typography']['fonts']['de']
        self.assertTrue(any('typography.fonts.de' in e for e in self.check()['errors']))
        self.plan['typography']['exceptionReason']='User supplied a single brand font with full coverage'
        self.assertFalse(any('font' in e for e in self.check()['errors']))
    def test_category_source_and_restricted_claims(self):
        self.plan['shots'][0].update(claim=False,source=[])
        self.copy('en')['description']='65W fast charging for laptops.'
        self.plan['shots'].append(dict(self.plan['shots'][0],id='proof',start=5,end=6,claim=True,source=['file:facts.md']));self.plan['duration']=6
        self.assertTrue(any('[en-us]' in e and 'certification' in e for e in self.check()['errors']))
        self.plan['category']='beauty';self.copy('en')['description']='Removes wrinkles in a week.'
        self.assertTrue(any('drug-like' in w for w in self.check()['warnings']))
    def test_acronyms_are_case_sensitive(self):
        self.copy('fr')['description']='Dire en une phrase ce que fait le produit.'
        self.copy('en')['description']='A dot of LED light shows the charge level.'
        self.plan['shots'][0].update(claim=False,source=[])
        self.plan['shots'].append(dict(self.plan['shots'][0],id='proof',start=5,end=6,claim=True,source=['file:facts.md']));self.plan['duration']=6
        for category in ['electronics','motorcycle-parts']:
            self.plan['category']=category;self.assertEqual(self.check()['errors'],[],category)
        self.plan['category']='electronics';self.plan['shots'].pop();self.plan['duration']=5
        self.copy('fr')['description']='Avec marquage CE.'
        self.plan['shots'].append(dict(self.plan['shots'][0],id='proof',start=5,end=6,claim=True,source=['file:facts.md']));self.plan['duration']=6
        self.assertTrue(any('[fr-fr]' in e and 'certification' in e for e in self.check()['errors']))
    def test_missing_category_is_production_error(self):
        del self.plan['category']
        self.assertTrue(any('category' in e for e in self.check()['errors']))
    def test_unsupported_locale(self):
        self.plan['versions'][0]['locale']='es'
        self.assertTrue(any("unsupported locale 'es'" in e for e in self.check()['errors']))
class Data(unittest.TestCase):
    """Rule data stays loadable and every referenced note exists."""
    def test_patterns_compile_and_docs_exist(self):
        import re
        def compile_all(table):
            for patterns in table.values():
                for p in patterns:re.compile(p)
        for kind in delivery.CLAIMS.values():
            if isinstance(kind,dict):compile_all(kind['patterns'])
        for key,cat in delivery.CATEGORIES.items():
            if key.startswith('_'):continue
            compile_all(cat['sourceRequired'])
            if 'restricted' in cat:compile_all(cat['restricted']['patterns'])
            self.assertTrue((ROOT/cat['doc']).is_file(),cat['doc'])
        for locale,data in delivery.LOCALES.items():
            self.assertTrue((ROOT/data['doc']).is_file(),data['doc'])
            self.assertIn(data['defaultChannel'],delivery.CHANNELS)
            for p in data['vague']:re.compile(p)
            self.assertEqual(set(data['placeholders']),{'intro','detail','close'})
        for channel in delivery.CHANNELS.values():
            if channel['doc']:self.assertTrue((ROOT/channel['doc']).is_file(),channel['doc'])
            for kind in [*channel['reject'],*channel['caution']]:self.assertIn(kind,delivery.CLAIMS)
            for locale in channel['languages']:self.assertIn(locale,delivery.LOCALES)
class Mix(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg needed')
    def test_outputs_are_capped_to_film_duration(self):
        import math,struct,wave
        mixer=module('mix_audio')
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'assets/sfx').mkdir(parents=True)
            def tone(path,seconds,freq,channels=2):
                rate=48000;frames=[]
                for i in range(int(rate*seconds)):
                    v=int(0.3*32767*math.sin(2*math.pi*freq*i/rate));frames+= [v]*channels
                with wave.open(str(path),'wb') as w:w.setnchannels(channels);w.setsampwidth(2);w.setframerate(rate);w.writeframes(struct.pack('<%dh'%len(frames),*frames))
            tone(root/'assets/music.wav',3.2,220);tone(root/'assets/sfx/a.wav',0.4,880);tone(root/'assets/sfx/b.wav',1.5,660,1)
            actions=[{'id':f'k{i}','at':0.2+i*0.3,'action':'key','soundRequired':True} for i in range(8)]
            cues=[{'at':a['at'],'actionId':a['id'],'file':'assets/sfx/'+('a' if i%2 else 'b')+'.wav','gain':0.8,'role':'sfx','kind':'click'} for i,a in enumerate(actions)]
            plan={'duration':3,'fps':30,'shots':[{'id':'s','start':0,'end':3,'actions':actions}],'audio':{'music':{'file':'assets/music.wav','gain':0.6},'cues':cues,'ducking':{'enabled':True}}}
            (root/'plan.json').write_text(json.dumps(plan),encoding='utf-8')
            with contextlib.redirect_stdout(io.StringIO()):mixer.mix(root/'plan.json')
            for name in ['sfx-stem.wav','music-ducked.wav','master.wav']:
                out=subprocess.run(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(root/'assets'/name)],capture_output=True,text=True).stdout
                self.assertAlmostEqual(float(out),3.0,delta=0.05,msg=name)
class Landmarks(unittest.TestCase):
    @unittest.skipUnless(shutil.which('ffmpeg'),'FFmpeg needed')
    def test_onset_and_peak(self):
        import math,struct,wave
        landmarks=module('sfx_landmarks').landmarks
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'hit.wav';rate=48000;data=[]
            for i in range(rate):
                t=i/rate;amp=0 if t<0.25 else (0.4 if t<0.5 else 0.9*math.exp(-(t-0.5)*8))
                data.append(int(amp*32767*math.sin(2*math.pi*440*t)))
            with wave.open(str(f),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(struct.pack('<%dh'%len(data),*data))
            r=landmarks(f)
            self.assertAlmostEqual(r['onset'],0.25,delta=0.01)
            self.assertAlmostEqual(r['peak'],0.5,delta=0.01)
            self.assertAlmostEqual(r['peakDbfs'],-0.9,delta=0.3)

if __name__=='__main__':unittest.main()
