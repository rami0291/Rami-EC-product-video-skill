# Français（`fr`）

默认版本：`fr-fr` → Amazon.fr，默认不加点缀语言。语言无关的写法见 [分镜与文案](../story-and-copy.md)，市场规则见 [Amazon.fr](../channels/amazon-fr.md)。

## 必须先知道：Loi Toubon

在法国面向消费者的广告和商品介绍必须使用法语（loi n° 94-665）。英文标语、英文点缀标题可以保留，但必须配上**同等醒目**的法语对应文字。所以：

- 面向 Amazon.fr 的版本，主语言必须是 `fr`；用英文版本直接上 Amazon.fr 时，`check_delivery.py` 会警告。
- 给法语版加英文点缀（`accent: en`）时，法语标题的字号、对比度不能低于英文。
- 品牌名、商品名（注册商标）不需要翻译。

## 文案写法

- 说明交代对象 + 动作 + 结果：
  - ✗ "La pluie ? Aucun souci." → ✓ "Fermetures étanches et tissu enduit : vos affaires restent au sec sous la pluie."
  - ✗ "Rechargez plus vite." → ✓ "Jusqu'à 65 W en USB-C, de quoi recharger un ordinateur portable compatible."
- **称呼统一**：电商一般用 "vous"；全片一致。
- 数字格式：小数点用逗号（1,2 kg），千位用窄不换行空格（10 000 mAh），数字与单位之间不换行空格（65 W）。
- 避免空洞词：révolutionnaire、inégalé、nouvelle dimension、expérience ultime、sans limites。
- 法语比英文长约 15–20%，标题列宽要按法语留余量。

## 排版

- **标点前的空格**：`? ! ; :` 前加窄不换行空格（U+202F），`:` 前也可以用不换行空格（U+00A0）；书名号用 « … »，内侧同样加不换行空格。普通空格会让标点单独掉到下一行，`check_delivery.py` 会提示。
- 设 `lang="fr"`；说明文字可以开 `hyphens: auto`，标题不自动断词。
- 字体要覆盖 é è ê à ç œ « » 等字符；大写字母上的重音（É、À）保留，不省略。

## 阅读速度

按约 **14 字符 / 秒**（含空格）提示。

## 本地化注意

- 合成场景标 "Photo non contractuelle" 或 "Visuel non contractuel"。
- 环保用语管得严，详见 [Amazon.fr](../channels/amazon-fr.md)。
