# EC-CUBE一本で大丈夫？Shopify開発者への転向ロードマップ【6ヶ月】

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論：EC-CUBEの経験は7割活きる。残り3割を埋めれば両刀使いになれる

**正直に言います。EC-CUBE案件、減っていませんか？**

D2Cブランドの台頭で「とりあえずShopifyで」という声が増えています。クライアントから「EC-CUBEじゃなくてShopifyでお願いしたい」と言われた経験、あなたにもあるのではないでしょうか。

**でも、焦る必要はありません。**

EC-CUBEで培ったスキルの**7割はShopify開発でも活きます**。残りの3割を埋めれば、「EC-CUBE + Shopify」の両刀使いとして市場価値を大幅に上げられます。

> **EC-CUBEとShopify、両方できるエンジニアは希少。今がスキルを広げるチャンス。**

| EC-CUBE | Shopify |
|---------|---------|
| サーバーを自分で管理 | Shopifyが管理（SaaS） |
| PHPでカスタマイズ | Liquid + JavaScript |
| 何でもできる自由度 | 制約の中で最適化 |
| フルスクラッチ開発 | テーマ/アプリの組み合わせ |

この記事では、EC-CUBEエンジニアが**最短でShopify開発者になるための学習ロードマップ**を紹介します。

## EC-CUBEとShopifyの根本的な違い

### アーキテクチャの違い

```
EC-CUBE（オンプレミス/クラウド）
├── サーバー管理：自分で行う
├── データベース：直接アクセス可能
├── コード：PHP/Symfony/Twig
└── カスタマイズ：ソースレベルで自由

Shopify（SaaS）
├── サーバー管理：Shopifyが行う
├── データベース：API経由のみ
├── コード：Liquid/JavaScript/React
└── カスタマイズ：テーマとアプリで拡張
```

### EC-CUBEエンジニアの強み

EC-CUBEで培った以下のスキルは、Shopify開発でも活きます：

- **ECの業務知識**: 受注、在庫、配送、決済の流れ
- **テンプレートエンジンの経験**: Twig → Liquid は類似点が多い
- **API連携の経験**: REST/GraphQL APIの概念
- **フロントエンド**: HTML/CSS/JavaScriptの基礎

### 学習が必要な領域

一方、以下は新しく学ぶ必要があります：

- **Liquid**: Shopify独自のテンプレート言語
- **React/Remix**: アプリ開発で必須
- **GraphQL**: Shopify Admin APIはGraphQL
- **Shopifyエコシステム**: Polaris、App Bridge、Hydrogen