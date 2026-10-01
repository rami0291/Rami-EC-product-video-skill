#!/usr/bin/env python3
"""Initialize an isolated product-video workspace. Installs nothing and never touches the product material folder."""
import argparse
import json
from pathlib import Path
import sys

DATA=Path(__file__).resolve().parent/'data'
LOCALES=json.loads((DATA/'locales.json').read_text(encoding='utf-8'))
CHANNELS=json.loads((DATA/'channels.json').read_text(encoding='utf-8'))
CATEGORIES={k:v for k,v in json.loads((DATA/'categories.json').read_text(encoding='utf-8')).items() if not k.startswith('_')}
BASE_FACTS=json.loads((DATA/'categories.json').read_text(encoding='utf-8'))['_baseFacts']


def csv(value):
    return [x.strip() for x in value.split(',') if x.strip()]


def main():
    # JSON reports carry CJK and typographic characters; Windows consoles default to a legacy code page.
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--style', required=True, choices=['brand', 'default', 'hybrid'])
    parser.add_argument('--category', required=True, choices=sorted(CATEGORIES), help='Product category notes to load (references/categories/)')
    parser.add_argument('--locales', default='en', help='Comma-separated language versions confirmed with the user, e.g. en,ja,de (default: en)')
    parser.add_argument('--channels', default='', help='Comma-separated channel per locale, same order, e.g. amazon-us,amazon-jp (default: per-locale default)')
    parser.add_argument('--product-dir', type=Path, help='Folder with product photos, spec sheets and listing text (read-only)')
    parser.add_argument('--brand', default='', help='Brand name, e.g. moto boite')
    args = parser.parse_args()
    locales=csv(args.locales)
    unknown=[l for l in locales if l not in LOCALES]
    if not locales or unknown or len(set(locales))!=len(locales):
        parser.error('--locales must list distinct supported locales: '+', '.join(LOCALES))
    channels=csv(args.channels) or [LOCALES[l]['defaultChannel'] for l in locales]
    if len(channels)!=len(locales):parser.error('--channels needs one channel per locale, in the same order')
    if any(c not in CHANNELS for c in channels):parser.error('--channels must be one of: '+', '.join(CHANNELS))
    product = args.product_dir.expanduser().resolve() if args.product_dir else None
    target = args.output.expanduser().resolve()
    if product is not None and not product.is_dir():
        parser.error('--product-dir must be an existing directory')
    if args.style in ('brand', 'hybrid') and not args.brand.strip():
        parser.error('brand/hybrid requires --brand so the brand identity can be audited')
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        parser.error('output must be absent or empty; existing work is never overwritten')
    skill = Path(__file__).resolve().parents[1]
    if target == skill or skill in target.parents:
        parser.error('output must be outside the skill bundle')
    if product is not None and (target == product or product in target.parents):
        parser.error('output must be outside the product material folder')
    versions=[]
    for locale,channel in zip(locales,channels):
        accent=LOCALES[locale]['defaultAccent']
        versions.append({'id':locale+('-'+channel.split('-',1)[1] if channel.startswith('amazon-') else ''),'locale':locale,'channel':channel,'accent':accent})
    used=sorted({l for v in versions for l in [v['locale'],v['accent']] if l})
    typography={'fonts':{l:LOCALES[l]['defaultFont'] for l in used}}
    if any(LOCALES[l]['script']=='cjk' for l in used):typography['cjkStyle']='sans-serif'
    target.mkdir(parents=True, exist_ok=True)
    for name in ['assets/photos', 'assets/brand', 'assets/fonts', 'assets/sfx', 'evidence', 'renders', 'src']:
        (target/name).mkdir(parents=True, exist_ok=True)
    timing=[('intro',0,3,'title'),('detail',3,7,'detail'),('close',7,10,'end')]
    shots=[]
    for sid,start,end,kind in timing:
        copy={}
        for locale in locales:
            text=dict(LOCALES[locale]['placeholders'][sid])
            text['plainExplanation']=text['description']
            if not any(v['locale']==locale and v['accent'] for v in versions):text.pop('accent',None)
            copy[locale]=text
        shots.append({'id':sid,'start':start,'end':end,'type':kind,'copy':copy,'descriptionAt':0,'claim':False,'source':[],'asset':None,
                      'actions':[{'id':sid+'-enter','at':0,'action':'copy enters','soundRequired':False}]})
    shots[1]['actions'].append({'id':'product-land','at':0.45,'action':'product photo lands','soundRequired':True})
    shots[2]['actions'][0]['soundRequired']=True
    plan = {'demo':True,'product':None,'brand':args.brand or None,'category':args.category,'style':args.style,
            'versions':versions,'width':1920,'height':1080,'fps':30,'duration':10,
            'productDir':str(product) if product else None,'audioRequired':True,'sfxRequired':True,
            'typography':typography,
            'audio':{'ducking':{'enabled':True},'music':{'file':'assets/music.wav','gain':0.65},'cues':[
              {'at':3.45,'actionId':'product-land','file':'assets/sfx/pop.wav','gain':0.8,'role':'sfx','kind':'pop'},
              {'at':7.0,'actionId':'close-enter','file':'assets/sfx/resolve.wav','gain':0.7,'role':'sfx','kind':'resolve'}]},
            'shots':shots}
    (target/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    category=CATEGORIES[args.category]
    version_lines='\n'.join(f"  - `{v['id']}`：{LOCALES[v['locale']]['name']}"+(f" + {LOCALES[v['accent']]['name']} 点缀标题" if v['accent'] else '')
                            +f" → {CHANNELS[v['channel']]['name']}" for v in versions)
    docs=[category['doc'],*[LOCALES[l]['doc'] for l in used],*[CHANNELS[c]['doc'] for c in set(channels) if CHANNELS[c]['doc']]]
    (target/'BRIEF.md').write_text(f"""# 视频 brief

- 状态：刚初始化，尚未完成商品调查与分镜。
- 风格选择：{args.style}（应来自用户已确认的选择）
- 品牌：{args.brand or '未指定'}
- 品类：{category['name']}（`{args.category}`）
- 语言版本与发布渠道（应来自用户已确认的选择；同一条时间线，按版本分别导出）：
{version_lines}
- 素材目录：{product or '未指定，制作正式内容前补充'}（只读，不在里面写文件）
- 商品 / 型号 / 卖点范围：待从用户输入和规格书确定。
- 目标顾客与使用场景：待确认。
- 画幅 / 时长：待记录；plan.json 当前只是 10 秒占位。
- 品牌资源 / 字体：待审计；版式按最长的语言版本设计。
- 声音：音乐默认代码原创；音效先找合适的录音素材，缺项用 scripts/make_sfx.py 生成。
- 卖点证据、素材审计与来源：记录在 evidence/。
- 本片需要读的品类、语言、渠道笔记：{', '.join(docs)}

保留用户原有的决定；没确认的字段不要伪装成已确认。正式成片完成后同步 plan.json 与实际时间线。
""", encoding='utf-8')
    (target/'DIRECTION.md').write_text('''# 影片方向（写代码前完成，见 references/direction.md）

> 这份文件只有问题，没有答案。每一项都从这个商品本身推导；不要照抄案例或上一支片子。

## 1. 参考拆解（用户给了参考才写）
| 参考里的手法 | 它在表达什么 | 本片是否采用、怎么改写 |
|---|---|---|

## 2. 商品气质
- 商品是什么、在哪里怎么用、给谁用：
- 顾客买它要解决什么问题（痛点）：
- 外观与材质（颜色、表面处理、形状、可见的结构）：
- 品牌设计语言（色板、字体、Logo）来源：
- 能成为视觉母题的元素（轮廓、材质、结构、使用动作、使用场景）：

## 3. 三个方向（沿不同的轴拉开）
| 方向 | 底色与光 | 字体声音 | 母题来源 | 镜头语言 | 节奏 | 音乐 |
|---|---|---|---|---|---|---|
| A | | | | | | |
| B | | | | | | |
| C | | | | | | |

## 4. 选择与理由
- 选哪个、为什么适合这个商品和顾客：
- 本片专属手法（3–5 个，每个写成"因为商品有 X，所以用 Y"）：
- 与本工作区既往影片的区别（开场、转场、背景、配乐）：

## 5. 画面规范
- 画幅 / 帧率 / 底色 / 安全区：
- 字号阶梯（每种语言的标题、说明、标注）与字体来源；最长的语言版本放得下：
- 商品上镜规则（占画面比例、最大放大倍数 = 素材分辨率允许的范围）：
- 动效语法（入场、镜头运动、缓动、禁止项）：

## 6. 镜头表
| # | 时间 | 镜头 | 主角 | 画面与动作 | 文案 | 声音 |
|---|---|---|---|---|---|---|
''', encoding='utf-8')
    rows='\n'.join(f'| {field} | | | |' for field in [*BASE_FACTS,*category['facts']])
    (target/'evidence/product-facts.md').write_text(f'''# 商品事实表（见 references/product-and-brand.md 与 {category['doc']}）

内容按原文照录（含原文语言与单位）；各语言版本的上屏文案从这里改写，不从另一个语言版本转译数字。

| 项目 | 内容 | 来源（文件 + 页/行） | 能否上屏 |
|---|---|---|---|
{rows}
''', encoding='utf-8')
    print(json.dumps({'project':str(target),'style':args.style,'category':args.category,'versions':[v['id'] for v in versions],'demo':True,
                      'read':docs,
                      'next':'Audit product facts and photos, then write DIRECTION.md (references/direction.md) before building shots.'},ensure_ascii=False))

if __name__ == '__main__':
    main()
