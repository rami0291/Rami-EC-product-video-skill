# 渲染管线：seek(t) 运行时与逐帧导出

画面在浏览器里用 HTML/CSS、GSAP 和（需要时）Three.js 搭出来，由 Playwright 逐帧截图，FFmpeg 编码。这一页说明运行时要满足的约定和最小骨架；镜头的样子按 `DIRECTION.md` 为每支片子重新写。已有 HyperFrames 工程可以沿用其契约，原则相同。

## 工程结构（建议）

```
plan.json             时间、文案、事实来源、声音（唯一的时间来源）
index.html            1920×1080 舞台；加载字体、GSAP、src/main.js
src/main.js           读 plan 和当前语言版本，搭各镜头的 builder，暴露 window.seek / window.__filmReady
src/shots/*.js        每个镜头一个 builder：摆 DOM、在主时间轴上加动画、注册 onRender
src/fixtures/         callouts.json 等从事实表派生的数据
src/film.css          本片的画面规范（字号阶梯、安全区、颜色变量），并关闭所有 CSS transition/animation
render.mjs            逐帧导出 MP4（--version 选语言版本）
stills.mjs            导出指定时刻的静帧（--version 选语言版本）
assets/fonts/         各语言的字体文件（确认授权），由 film.css 的 @font-face 加载
```

依赖装在视频工程里：`npm install --save-exact playwright gsap`，用到 WebGL 再加 `three`。

## seek(t) 必须是 t 的纯函数

任意时刻 `t` 都能直接恢复完整画面，不依赖之前播过哪些帧：

1. `master.seek(t)`：所有 GSAP 动画都挂在一条 `paused: true` 的主时间轴上，用影片绝对时间摆放。
2. 按时间显示/隐藏镜头（前后各留约 0.8 秒给转场重叠）。
3. 调用每个 `onRender(id, fn)` 注册的每帧绘制：Three.js、2D canvas、跟随照片坐标的标注线、视差层位置。

```js
// src/main.js（示意）
const plan = await (await fetch('plan.json')).json();
const version = plan.versions.find(v => v.id === new URLSearchParams(location.search).get('version')) ?? plan.versions[0];
document.documentElement.lang = version.locale;          // 断行、断词、:lang() 字体都依赖它
const master = gsap.timeline({paused: true});
const renders = [];
export const shot = id => plan.shots.find(s => s.id === id);
export const copy = id => shot(id).copy[version.locale];  // 镜头只从这里取文字，不在代码里写死文案
export const accent = id => version.accent ? shot(id).copy[version.locale].accent : null;
export const onRender = (id, fn) => renders.push({id, fn});
for (const build of Object.values(await import('./shots/index.js'))) await build(master);
await document.fonts.ready;
await Promise.all([...document.images].map(img => img.decode()));
window.seek = t => {
  master.seek(t, false);
  for (const s of plan.shots) document.getElementById(s.id).style.visibility = t >= s.start - 0.8 && t < s.end + 0.8 ? 'visible' : 'hidden';
  for (const r of renders) { const s = shot(r.id); r.fn(t - s.start, t); }
};
window.__filmReady = true;
```

写镜头时：

- 镜头起止时间只写在 `plan.json`，代码通过 `shot(id)` 读；文字通过 `copy(id)` / `accent(id)` 读。
- 文字元素带 `lang` 属性：主语言用 `version.locale`，点缀用 `version.accent`。`film.css` 用 `:lang(ja)`、`:lang(de)` 等选择器给每种语言指定字体、字号阶梯和断行规则（CJK `line-break: strict`，德语 `hyphens: auto`）。
- 布局测量（标题宽度、标注锚点）发生在 builder 里，所以每个版本各自测量；不要把某个语言版本测出来的数值写死在代码里。
- GSAP 的 `fromTo` 在搭建时就写入起始值，所以测量（照片尺寸、标注锚点位置）要放在摆动画之前。
- GSAP 时间轴是 thenable：`await tl` 会等时间轴播完，暂停的主时间轴永远不会结束。builder 可以是 async，但不要 await 时间轴本身。
- CSS transition/animation 会和影片时钟抢状态：`film.css` 里统一 `* { transition: none !important; animation: none !important; }`，需要动的东西都放进主时间轴或 `onRender`。
- 随机数用固定种子的 PRNG，不用 `Math.random()`。

## 逐帧导出

```js
// render.mjs（示意）node render.mjs --version en-us --from 0 --to 10 --output renders/draft-en-us.mp4 [--audio assets/master.wav]
import {chromium} from 'playwright';
import {spawn} from 'node:child_process';
import {readFileSync} from 'node:fs';
const plan = JSON.parse(readFileSync('plan.json', 'utf8'));
const arg = (k, d) => { const i = process.argv.indexOf(k); return i < 0 ? d : process.argv[i + 1]; };
const version = arg('--version', plan.versions[0].id);
const from = +arg('--from', 0), to = +arg('--to', plan.duration), out = arg('--output', `renders/draft-${version}.mp4`), audio = arg('--audio');
const browser = await chromium.launch({args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']});
const page = await browser.newPage({viewport: {width: plan.width, height: plan.height}});
await page.goto(`http://localhost:8080/index.html?version=${encodeURIComponent(version)}`);  // 本地 HTTP 服务，不用 file://
await page.waitForFunction(() => window.__filmReady === true);
const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(plan.fps), '-i', '-',
  ...(audio ? ['-ss', String(from), '-i', audio, '-c:a', 'aac', '-b:a', '192k', '-shortest'] : []),
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', out], {stdio: ['pipe', 'inherit', 'inherit']});
for (let f = Math.round(from * plan.fps); f < Math.round(to * plan.fps); f++) {
  await page.evaluate(t => window.seek(t), f / plan.fps);
  const jpg = await page.screenshot({type: 'jpeg', quality: 92});
  if (!ff.stdin.write(jpg)) await new Promise(r => ff.stdin.once('drain', r));
}
ff.stdin.end(); await new Promise(r => ff.on('close', r)); await browser.close();
```

`stills.mjs` 用同样的方式打开页面（同样带 `?version=`），对传入的几个时刻 seek 后各存一张 PNG，并打印页面错误（`page.on('pageerror')`）和加载失败的资源（`page.on('requestfailed')`）。多语言片子每个版本各出一组静帧，先看最长的语言版本。

- `seek` 里有需要等待的工作（例如 WebGL 纹理首次上传）时让它返回 Promise，`page.evaluate` 会等。
- 50 秒、带 WebGL 和模糊滤镜的片子，逐帧导出一般要几分钟；先渲染几秒估算。
- Three.js 渲染器设 `preserveDrawingBuffer: true`、像素比 1；整片控制在 2–4 个 WebGL 上下文以内，背景层能用 CSS 或 2D canvas 就不用 WebGL。

正式导出：

```sh
python3 <skill-dir>/scripts/mix_audio.py plan.json            # 所有版本共用同一个 master
node render.mjs --version en-us --audio assets/master.wav --output renders/final-en-us.mp4
node render.mjs --version ja-jp --audio assets/master.wav --output renders/final-ja-jp.mp4
python3 <skill-dir>/scripts/check_delivery.py plan.json --video renders/final-en-us.mp4 --mix-report evidence/audio-mix.json
python3 <skill-dir>/scripts/check_delivery.py plan.json --video renders/final-ja-jp.mp4 --mix-report evidence/audio-mix.json
```

## plan 字段

- `demo`：初始化占位为 true，正式内容完成后设为 false。
- `product / brand / category / width / height / fps / duration / style / audioRequired`：工程规格。`category` 取 `scripts/data/categories.json` 的键（`motorcycle-parts`、`electronics`、`beauty`、`other`），决定事实表字段和品类措辞检查。
- `versions[]`：`{id, locale, channel, accent}`。一个版本 = 一种主语言 + 一个发布渠道；`accent` 是可选的点缀语言（例如日文版的英文短标题）。`locale` 取 `locales.json`（`en`、`de`、`fr`、`ja`、`zh-Hans`），`channel` 取 `channels.json`（`amazon-us`、`amazon-uk`、`amazon-de`、`amazon-fr`、`amazon-jp`、`other`）。交付检查按每个版本的语言和渠道提示措辞。
- `productDir`：素材目录（只读）。`scope`：用户确认的商品、颜色/型号、受众。
- `typography`：`fonts` 按语言指定字体（`{"en":"Inter","ja":"Noto Sans JP"}`），所有版本用到的主语言和点缀语言都要有；有 CJK 时 `cjkStyle:"sans-serif"`。用户指定单一字体或其他方案时，用 `exceptionReason` 记录依据。
- `shots[]`：`id, start, end, type, copy, descriptionAt, claim, source, asset, actions`。`copy[locale]` 是 `{headline, description, plainExplanation, accent?}`，每个版本的 `locale` 都要有。镜头在代码里的实现以 `DIRECTION.md` 的镜头表为准，plan 记录时间、事实与声音，两者要一致。
- 旧版单语言 plan（`headline / headlineEn / description`、`typography.jaFont / enFont`、`channel`）仍可检查：视为一个 `ja` 版本 + 英文点缀 + `motorcycle-parts`。下次修改时迁移到 `versions` / `copy`。
- `type`：`title`（字卡）、`detail`（商品特写）、`macro`（材质 / 质地 / 工艺微距）、`spec`（尺寸 / 规格标注）、`install`（安装 / 实装）、`usage`（使用演示）、`lifestyle`（使用场景）、`montage`（快切）、`end`（落版）。`detail / macro / spec / install / usage / lifestyle` 必须给 `asset`。
- `claim` 为 true 的镜头必须给 `source`。写法：`file:evidence/product-facts.md`（相对视频工程）或 `product:spec/仕様書.pdf#p2`（相对 `plan.productDir`），支持 `:行号`、`#L行号`、`#p页码`；裸路径先查视频工程再查 `productDir`；URL、`asin:` 等留给人工核对。品牌开场不需要假造 source。
- `actions`：唯一 `id`、相对镜头开始的 `at`、动作描述、`soundRequired`。
- `audio.music / audio.cues`：cue 的 `at` 是文件开始的影片绝对时间，`syncOffset` 是文件内听觉落点，满足 `at + syncOffset = 动作时间`。落点用 `scripts/sfx_landmarks.py` 测，不要猜。可选 `onBeat` / `beatDivision` 对照 `audio.beatGrid`。
- `descriptionAt`：说明文字相对镜头开始的出现时间，所有版本共用，用于按各语言阅读速度提示。

改了分镜或配乐就重新混音；正式导出会核对 plan 与 master 的哈希。
