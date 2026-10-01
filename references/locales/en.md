# English（`en`）

默认版本：`en-us` → Amazon.com；英国站用 `--channels amazon-uk`（`en-uk`）。英文版默认不加点缀语言。语言无关的写法见 [分镜与文案](../story-and-copy.md)。

## 文案写法

- **标题是动作或结果，不是形容词。** "Folds flat" "Locks in one click" 比 "Premium Design" "Next-level Comfort" 有信息量。
- **说明交代对象 + 动作 + 结果**，一句话，主动语态：
  - ✗ "Rain? No problem." → ✓ "Water-resistant zips and coated fabric keep your gear dry in sudden rain."
  - ✗ "Charge faster." → ✓ "One USB-C port delivers up to 65W, enough to charge a compatible laptop."
  - ✗ "Skin, transformed." → ✓ "A lightweight gel that leaves skin feeling hydrated without stickiness."
- 用顾客的词，不用工厂术语。数字保留规格书单位；美国站默认英制 / 公制双写时，以规格书原文为准，不自己换算后四舍五入。
- 避免空洞营销词：game-changer、revolutionary、unleash、elevate、next level、like never before（`check_delivery.py` 会提示）。
- 句首大写（Sentence case）比每词大写（Title Case）更易读，长标题尤其如此；同一支片子保持一致。
- 美式 / 英式拼写按市场统一：color / colour、aluminum / aluminium、organize / organise。`en-uk` 版本要按英式拼写检查一遍。

## 排版

- 拉丁字体优先选有多字重的无衬线（Inter、Manrope、品牌字体）。全片 1–2 个字体家族。
- 大标题适当收紧字距（-1% 到 -2%），全大写的小标签适当放宽字距（+4% 到 +8%）。
- 设 `lang="en"`；标题不自动连字符（`hyphens: manual`），避免标题里出现断词。
- 英文通常比日文、中文版短，**版式按最长的语言版本（通常是德语）设计**，英文版不要因此字号放得过大。

## 阅读速度

`check_delivery.py` 按约 **15 字符 / 秒**（含空格）提示，来自字幕惯例（成人 15–17 cps）。画面同时有复杂变化时再放慢。

## 本地化注意

- 合成场景加 "Image for illustration purposes only."（或品牌既有措辞）。
- 美国 FTC 对 "Made in USA" 有 "all or virtually all" 的严格要求，没有依据不要出现；英国 / 欧盟同理看原产地规则。
- 测试条件注释用小字放在画面下部安全区内，仍需 ≥ 28px。
