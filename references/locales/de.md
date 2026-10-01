# Deutsch（`de`）

默认版本：`de-de` → Amazon.de，默认不加点缀语言。语言无关的写法见 [分镜与文案](../story-and-copy.md)，市场规则见 [Amazon.de](../channels/amazon-de.md)。

## 文案写法

- 德国顾客重视具体、可核对的信息：材质、尺寸、兼容性、测试条件。口号式的英文标题可以保留为品牌点缀，但说明必须是德语，而且完整。
- **称呼统一**：电商通常用 "Sie"（正式），年轻品牌可以用 "du"，全片一致，与品牌既有商品页一致。
- 说明交代对象 + 动作 + 结果：
  - ✗ "Regen? Kein Problem." → ✓ "Wasserabweisende Reißverschlüsse und beschichtetes Gewebe halten dein Gepäck bei Regen trocken."
  - ✗ "Schneller laden." → ✓ "Bis zu 65 W über USB-C – genug, um ein kompatibles Notebook zu laden."
- 数字格式：小数点用逗号（1,2 kg），数字与单位之间用不换行空格（65 W、30 l）；千位分隔用点或窄空格（10.000 mAh / 10 000 mAh），全片统一。
- 避免空洞词：revolutionär、grenzenlos、nächstes Level、Premium-Erlebnis。
- "Testsieger""TÜV-geprüft""Made in Germany"需要真实证书或授权，详见市场笔记。

## 排版

- **德语比英文长约 30%**，复合词很长（Schnellladegerät、Wasserdichtigkeit）。版式按德语设计：标题列宽、字号阶梯在德语版本里放得下才算定稿。
- 设 `lang="de"` 并开启 `hyphens: auto`，让浏览器按德语规则断词；关键标题用软连字符（`&shy;`）手动指定断点，避免难看的断法。`check_delivery.py` 会提示标题里 ≥ 20 个字母的长词。
- 引号用德式 „…“；破折号用 en dash（–）两侧空格。
- 选择覆盖 ä ö ü ß 及大写 ẞ 的字体，渲染静帧时检查变音符号没有被行高裁掉。

## 阅读速度

按约 **14 字符 / 秒**（含空格）提示。德语单词长，实际可读速度比英文略慢；说明长时优先拆成两句或延长停留，不缩字号。

## 本地化注意

- 合成场景标 "Symbolbild" 或 "Abbildung ähnlich"。
- 尺寸用公制；英寸只在规格书原文如此（屏幕尺寸）时出现，并附厘米。
