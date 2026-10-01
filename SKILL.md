---
name: Rami-EC-product-video-skill
license: "AGPL-3.0"
description: 为跨境电商的实物商品制作商品视频，默认按 Amazon 各站点（US/UK/DE/FR/JP）的要求：整理有出处的卖点、按语言写文案（英/中/日/德/法，默认英语，一支片子可出多个语言版本）、处理商品照片、做动画、写配乐、配音效，最后导出视频和可继续修改的工程。内置摩托车周边、3C 电子、美妆个护的品类规则，其他品类按模板补。每支片子的视觉手法都从商品本身推导，不套模板。用户说"做商品视频""宣传片""Amazon 动画""商品动画""product video""A+ 视频"时使用。
---

# Rami-EC-product-video-skill

用真实商品照片和有出处的规格事实，讲清楚一件商品：它是什么、怎么用、解决什么问题、为什么值得买。画面、文案和声音一起推进；同一条时间线可以按语言导出多个版本，分别上传到不同站点。

本文术语：
- **素材目录**：用户提供的商品照片、规格书、商品页文字所在的文件夹（只读）。
- **方向文件**：视频工程里的 `DIRECTION.md`。
- **事实表**：`evidence/product-facts.md`。
- **版本**：`plan.versions` 里的一项，即一种主语言 + 一个发布渠道。
- **品类 / 语言 / 渠道笔记**：分别在 `references/categories/`、`references/locales/`、`references/channels/`。
- 音效事件统一保存在 `audio.cues`。

## 流程

1. **确认范围、品类、语言版本、渠道与风格。** 已有工程沿用 brief 和用户决定，只处理本次修改。新片要补齐以下几项：
   - 品牌、商品名 / 型号（单品、系列还是一组搭配）、目标顾客与使用场景、时长与画幅、有没有参考视频。
   - **品类**：`motorcycle-parts`、`electronics`、`beauty`，或 `other`。用 `other` 时先按 `categories/_template.md` 补品类笔记。
   - **语言版本**：问一次"要做哪些语言？"，可选英语 `en`（默认）、日语 `ja`、德语 `de`、法语 `fr`、简体中文 `zh-Hans`。
   - **每个语言版本发到哪个站点**：默认 en→Amazon US、ja→Amazon JP、de→Amazon DE、fr→Amazon FR、zh-Hans→other（内部审片或其他平台）；英国站用 `amazon-uk`。

   **宣传哪件商品、讲哪几个卖点、面向谁，必须由用户拍板**：素材只能说明商品有什么，说明不了用户想卖什么。没指定时问一次，答案写入 `plan.json` 的 `scope`（如 `{"items":["65W GaN charger"],"variants":["black"],"audience":"business travelers"}`）并同步进 BRIEF。风格没定时问一次："沿用品牌自己的视觉风格（推荐），还是用默认的风格？" `brand` 按品牌 VI；`default` 用中性包装；`hybrid` 保留品牌色和 Logo、调整外层排版。常见起点：横版 16:9、45–60 秒。
2. **初始化并检查环境。** 按下方工具入口初始化独立视频目录，再运行环境检查；只对报告的缺项加载 [依赖安装](references/onboarding.md)，装完复查。已有工程直接检查，不重新初始化。初始化输出的 `read` 列出本片要读的品类、语言、渠道笔记：**动手前读完**。
3. **调查商品，整理素材。** 按 [商品与品牌审计](references/product-and-brand.md) 和品类笔记，从规格书、商品页文字和照片里整理事实表，每项写出处；记下品牌设计语言和可做母题的商品元素。按 [素材处理](references/asset-pipeline.md) 审核照片：分辨率够不够放大、有没有可用的透明底、场景照里有没有第三方 Logo 和个人信息。先做一个商品镜头并出静帧。
4. **定方向，写 `DIRECTION.md`。** 按 [影片方向](references/direction.md)：
   - 拆解参考，提炼商品气质，沿不同的轴提出三个方向，选一个并写出理由。
   - 列出 3–5 个"因为商品有 X、所以用 Y"的专属手法，并避开本工作区上一支片子的手法。
   - 把画面规范写成具体数字，**版式按最长的语言版本设计**。
   - 写到每一秒的镜头表。

   用户想先看方向时，给三个方向和 3–6 张关键静帧，等反馈；否则继续。
5. **逐镜头搭建。** 按 [渲染管线](references/render-pipeline.md) 搭运行时：
   - 每个镜头 = 画面结构 + builder（GSAP 主时间轴、`onRender` 画布层）。
   - 时间只从 `plan.json` 读，文字只从 `shot.copy[locale]` 读。
   - 手法从 [视觉手法词汇](references/visual-vocabulary.md) 里选能从商品推导的。
   - 文案按 [分镜与文案](references/story-and-copy.md) 和语言笔记，每种语言单独写，不逐句翻译。
   - 每搭完一个镜头就出静帧，对照镜头表（[审片](references/review.md)）。多语言片子先看最长的语言版本。
6. **配乐与音效。** 按 [配乐与音效](references/audio-sourcing.md)：
   - 选音乐来源：用户提供 → 本机可用的生成模型 → 代码合成。
   - 编曲从镜头边界推出来，音色从商品气质和目标顾客推出来。
   - 音效先用与商品动作相符的录音素材，缺项再用 `make_sfx.py` 生成。
   - 用 `sfx_landmarks.py` 实测落点和电平，按 [混音与验收](references/audio-and-qa.md) 对位、让位、混音。所有语言版本共用一个 master。
7. **审片并交付。** 每个版本导出 MP4，看 2 fps 联系表、每个转场的 10 fps 条带和信息密集镜头的全尺寸帧，按 [审片](references/review.md) 修改后重新导出。
   - 每个版本按其渠道笔记逐项检查，Amazon 先看 [Amazon 通用](references/channels/amazon-common.md)。
   - 每个版本运行 `check_delivery.py`（`pacing` 只提示该去看哪一段）。
   - 交付每个版本的 MP4、可复现工程和少量预览。说清哪些是自动检查、哪些实际看过 / 听过、哪些仍未验证（例如某个语言没有母语者读过）。
   - 历史问题查 [案例复盘](references/case-study.md)。

## 硬约束

- **真实商品，真实事实。** 商品画面只用真实照片（用户提供或用户确认可用的实拍），不用 AI 生成或改画商品外观、颜色、细节；背景和氛围层可以合成，但不能让人误以为是实物状态。正式片至少一项可追溯的卖点；尺寸、材质、兼容、认证、性能、功效类数字和说法必须能在事实表里找到出处。范围以 `plan.scope` 为准，没覆盖的颜色 / 型号在交付时说明。
- **看得清。** 商品在功能镜头里是唯一主角；放大不超过照片原始分辨率允许的范围；画面里的文字在成片里 ≥ 28px（1080p），每个语言版本在手机上也能读。
- **先有方向，再写代码。** 正式片必须有 `DIRECTION.md`：选定的方向和理由、从商品推导的专属手法、画面规范、镜头表。
- **不套模板。** 每个视觉手法都要能说出它对应商品的哪一点。案例和品类笔记是推导示范，不是风格包；同一工作区连续做片，不原样复用上一支的开场、章节和背景手法。片内也要避免所有元素同一种入场、同一种转场。
- **每种语言都写清楚。** 每个版本的文案用该语言单独写，交代对象、动作和结果；数字从事实表抄，不从另一个语言版本转译。每种语言（含点缀语言）独立 span、设 `lang`、分别指定字体；CJK 用无衬线。用户指定的语言 / 字体优先，例外记录在 `typography.exceptionReason`。
- **合规表达。** 不出现价格、促销、评价星级、排名 / No.1、竞品对比、URL 和保证类说法（Amazon 各站点的常见拒审点）；按版本的渠道笔记和品类笔记检查各市场法规（景品表示法、薬機法、FTC、UWG、Loi Toubon、欧盟环保说法新规等）；场景画面里不出现第三方 Logo / 商标和个人信息。这些笔记不是法律意见，正式上线前由用户确认。
- **完整声音。** 默认音乐与独立动作音效都进音轨，关键反馈听得见、音画同步；但信息不能只靠声音传达（很多人静音看）。用户要求静音或省略音效时，记录 `audioExceptionReason`。
- **隔离工程。** 渲染代码、处理后的素材和构建配置放在视频工程；素材目录只读，不在里面写文件。
- **授权与真实验收。** 照片、字体（每种语言）、音乐、音效保留来源和许可；模特、他人物品要有使用许可，覆盖所有上线市场。自动检查只证明结构与文件一致；视觉、语义和听感靠实际审阅，没有试听或没有母语者审读就如实说明。

## 工具入口

先确认风格、品类和语言版本，再初始化；`brand` / `hybrid` 必须给 `--brand`：

```sh
python3 <skill-dir>/scripts/init_project.py --output <video-dir> --style brand --brand "<brand>" \
  --category electronics --locales en,ja,de --product-dir <素材目录>
# 渠道默认按语言推断；需要时显式指定，顺序与 --locales 一致：--channels amazon-uk,amazon-jp,amazon-de
python3 <skill-dir>/scripts/check_environment.py --project <video-dir> --engine browser
# 缺项 → 按 references/onboarding.md 补装 → 使用 --force 复查。
```

已有 HyperFrames 工程使用 `--engine hyperframes`。新工程只有目录骨架、10 秒占位 `plan.json`（每个版本各有占位文案）、只有问题的 `DIRECTION.md` 和按品类生成表头的事实表；渲染运行时按 [渲染管线](references/render-pipeline.md) 在工程里搭。

- [商品与品牌审计](references/product-and-brand.md)：事实表、适配与认证类说法、品牌 VI、母题候选、风格决策。
- **品类笔记**：[摩托车周边](references/categories/motorcycle-parts.md)、[3C 电子](references/categories/electronics.md)、[美妆个护](references/categories/beauty.md)、[新品类模板](references/categories/_template.md)。
- **语言笔记**：[English](references/locales/en.md)、[日本語](references/locales/ja.md)、[Deutsch](references/locales/de.md)、[Français](references/locales/fr.md)、[简体中文](references/locales/zh-Hans.md)。文案写法、排版、断行、阅读速度。
- **渠道笔记**：[Amazon 通用](references/channels/amazon-common.md)，以及 [US](references/channels/amazon-us.md)、[UK](references/channels/amazon-uk.md)、[DE](references/channels/amazon-de.md)、[FR](references/channels/amazon-fr.md)、[JP](references/channels/amazon-jp.md) 的差异。
- [素材处理](references/asset-pipeline.md)：照片分辨率与放大上限、抠图、场景照处理、多语言标注、素材证据。
- [影片方向](references/direction.md)：参考拆解、商品气质、三个方向与差异轴、专属手法推导、反重复、画面规范、镜头表。
- [视觉手法词汇](references/visual-vocabulary.md)：按作用分组的手法，写明表达什么、从哪里推导、怎么实现、何时不用。
- [分镜与文案](references/story-and-copy.md)：叙事结构、多语言版本工作流、文案写法、试读。
- [渲染管线](references/render-pipeline.md)：seek(t) 运行时、按版本取文案与字体、GSAP 主时间轴、onRender、Playwright 逐帧导出、plan 字段。
- [审片](references/review.md)：三个审片节点、联系表与转场条带、多语言审片、常见问题对照表。
- `scripts/make_sfx.py --output <new-sfx-dir>`：生成 12 个原创合成音效（click、pop、whoosh、impact、resolve 等），只用来补录音素材的缺项。
- `scripts/sfx_landmarks.py <files>`：实测音效的起音点、峰值时间和峰值电平。
- `scripts/mix_audio.py <plan.json>`：混音、音乐让位、独立音轨和证据报告。
- `scripts/check_delivery.py <plan.json> [--video <final-<version>.mp4>] [--mix-report <audio-mix.json>]`：检查以下几类问题。
  - 结构、文件、时间线、方向文件。
  - 每个版本的文案、字体与阅读速度。
  - 按渠道和品类的措辞提示。
  - 媒体与画面节奏提示。
- 规则数据在 `scripts/data/`：`locales.json`、`channels.json`、`claims.json`、`categories.json`。加语言、站点或品类时同时补数据、笔记和测试。
- `python3 -m unittest discover -s <skill-dir>/tests`：维护此 skill 时运行；日常制片不需要读测试源码。
