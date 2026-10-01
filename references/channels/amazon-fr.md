# Amazon.fr

先读 [Amazon 通用](amazon-common.md)。法文写法见 [Français](../locales/fr.md)。上传前以 Seller Central 当时的视频上传说明为准。本页不是法律意见。

## 常见拒审措辞（法文）

| 类别 | 例子 |
| --- | --- |
| 价格与促销 | « 29,99 € » « promo » « soldes » « -20 % » « livraison gratuite » « offre limitée » « achetez maintenant » |
| 评价与排名 | « ★★★★★ » « 4,8 étoiles » « avis clients » « meilleure vente » « N° 1 » « élu produit de l'année » |
| 竞品与比较 | « mieux que les autres marques » « comparé à X » |
| 外部引导 | URL、« rendez-vous sur notre site » « suivez-nous » |
| 保证与承诺 | « satisfait ou remboursé » « garantie à vie » |

## 法规要点

- **Loi Toubon**：面向法国消费者的广告必须使用法语；外语标语要有同等醒目的法语对应。`check_delivery.py` 会对 Amazon.fr 版本的非法语主语言和英文点缀给出提醒。
- **Code de la consommation**：误导性商业行为（pratiques commerciales trompeuses）包括无依据的性能说法、最上级、虚假的稀缺性。
- **环保说法**：
  - 欧盟指令 2024/825 自 **2026-09-27** 起适用，禁止没有依据的笼统环保说法和基于碳抵消的"气候中和"说法。
  - 法国本身更早就有限制：AGEC 法禁止在商品和包装上使用 « biodégradable »« respectueux de l'environnement » 等说法；Climat et Résilience 法对 « neutre en carbone » 类广告说法设了严格条件。视频里一律避开，改成具体事实。
- **"Élu produit de l'année""Saveurs de l'année"类称号**：只有真实获得、获得授权使用时才可以出现，并注明年份。
- **品类法规**：化妆品按欧盟 655/2013；电子产品 CE；健康相关说法从严。详见各品类笔记。
