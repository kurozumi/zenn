## 学習ロードマップ

### Phase 1: テーマ開発の基礎（1〜2ヶ月）

まずはテーマ開発から始めましょう。EC-CUBEでTwigを使っていた経験が活きます。

### 1-1. Liquidの基礎

Liquidは、EC-CUBEのTwigに相当するテンプレート言語です。

```liquid
{# Twig（EC-CUBE） #}
{% for product in products %}
  <h2>{{ product.name }}</h2>
  <p>{{ product.price|number_format }}円</p>
{% endfor %}

{# Liquid（Shopify） #}
{% for product in collections.all.products %}
  <h2>{{ product.title }}</h2>
  <p>{{ product.price | money }}</p>
{% endfor %}
```

主な違い：
- Twigの `number_format` → Liquidの `money` フィルター
- プロパティ名が異なる（`name` → `title`）
- オブジェクトの取得方法が異なる

**学習リソース:**
- [Liquid公式ドキュメント](https://shopify.github.io/liquid/)
- [Shopify Liquid reference](https://shopify.dev/docs/api/liquid)

### 1-2. テーマ構造の理解

```
Shopifyテーマ構造
├── assets/          # CSS, JS, 画像
├── config/          # 設定ファイル
├── layout/          # ベースレイアウト
├── locales/         # 多言語対応
├── sections/        # 再利用可能なセクション
├── snippets/        # 部品テンプレート
└── templates/       # ページテンプレート
```

EC-CUBEの`app/template/`に相当しますが、Shopifyは**セクション**という概念でより柔軟な構成が可能です。

### 1-3. 開発環境のセットアップ

```bash
npm install -g @shopify/cli @shopify/theme


shopify theme dev --store=your-store.myshopify.com
```

**学習目標:**
- [ ] Liquidの基本文法を理解する
- [ ] 既存テーマをカスタマイズできる
- [ ] セクションを自作できる

### Phase 2: JavaScript/Ajax APIの習得（1ヶ月）

EC-CUBEでもJavaScriptは使いますが、Shopifyではより重要な役割を担います。

### 2-1. Shopify Ajax API

カート操作やバリアント取得など、フロントエンドからのAPI呼び出しが必要です。

```javascript
// カートに商品を追加
fetch('/cart/add.js', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    items: [{ id: variantId, quantity: 1 }]
  })
})
.then(response => {
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  return response.json();
})
.then(data => console.log('Added to cart:', data))
.catch(error => console.error('Cart add failed:', error));
```

### 2-2. Schemaによる設定

テーマエディタからカスタマイズ可能にするためのスキーマ定義：

```liquid
{% schema %}
{
  "name": "カスタムセクション",
  "settings": [
    {
      "type": "text",
      "id": "heading",
      "label": "見出し",
      "default": "おすすめ商品"
    },
    {
      "type": "collection",
      "id": "collection",
      "label": "表示するコレクション"
    }
  ]
}
{% endschema %}
```

**学習目標:**
- [ ] Ajax APIでカート操作ができる
- [ ] Schemaで設定可能なセクションを作れる
- [ ] イベントハンドリングを実装できる

### Phase 3: アプリ開発の基礎（2〜3ヶ月）

テーマでは実現できない機能は、アプリで実装します。

### 3-1. 技術スタックの理解

```
Shopifyアプリの技術スタック
├── フロントエンド
│   ├── React（必須）
│   ├── Polaris（ShopifyのUIライブラリ）
│   └── App Bridge（Shopify管理画面との連携）
├── バックエンド
│   ├── Remix/React Router（推奨）
│   └── Node.js / Ruby / PHP も可
└── API
    └── GraphQL Admin API
```

**重要**: Shopifyは2024年にRemixを買収し、アプリ開発の推奨フレームワークとしています。

### 3-2. GraphQL Admin API

EC-CUBEのRepositoryに相当するのが、GraphQL Admin APIです。

```graphql
query {
  products(first: 10) {
    edges {
      node {
        id
        title
        variants(first: 5) {
          edges {
            node {
              id
              price
              inventoryQuantity
            }
          }
        }
      }
    }
  }
}
```

EC-CUBEの`ProductRepository->findAll()`に相当しますが、取得するフィールドを明示的に指定する必要があります。

### 3-3. アプリ開発の始め方

```bash
npm init @shopify/app@latest

cd your-app
npm run dev
```

**学習リソース:**
- [Build a Shopify app using Remix](https://shopify.dev/docs/apps/build/build?framework=remix)
- [Shopify App Template (GitHub)](https://github.com/Shopify/shopify-app-template-remix)

**学習目標:**
- [ ] Reactの基礎を理解する
- [ ] GraphQL APIでデータを取得できる
- [ ] 簡単なアプリを作成できる

### Phase 4: 発展的なスキル（3ヶ月〜）

市場価値を高めるための発展的なスキルです。

### 4-1. Hydrogen（ヘッドレスコマース）

HydrogenはShopifyのヘッドレスコマースフレームワークです。

```
従来のShopify
└── Shopifyサーバー → Liquidテンプレート → HTML

Hydrogen（ヘッドレス）
└── Storefront API → React/Hydrogen → カスタムフロントエンド
```

エンタープライズ向けや、高度にカスタマイズされたフロントエンドが必要な場合に使用します。

**学習リソース:**
- [Hydrogen公式サイト](https://hydrogen.shopify.dev/)
- [Hydrogen Update (December 2025)](https://hydrogen.shopify.dev/update/december-2025)

### 4-2. AI連携

2026年現在、ShopifyはAI機能を積極的に拡充しています：

- **Storefront MCP**: AIショッピングツール（ChatGPT、Perplexity等）からの商品発見
- **Shopify Catalog**: AIアシスタントへの商品情報提供
- **AI-driven personalization**: 個別化されたショッピング体験

## 学習期間の目安

| フェーズ | 期間 | 前提条件 |
|---------|------|---------|
| Phase 1: テーマ基礎 | 1〜2ヶ月 | HTML/CSS/JS経験あり |
| Phase 2: JavaScript/API | 1ヶ月 | Phase 1完了 |
| Phase 3: アプリ開発 | 2〜3ヶ月 | React未経験の場合 |
| Phase 4: 発展スキル | 3ヶ月〜 | Phase 3完了 |

**合計: 約6ヶ月〜1年**（学習時間: 150〜200時間）

## おすすめの学習リソース

### 公式リソース（無料）

1. **[Shopify Academy](https://www.shopifyacademy.com/)** - 公式の学習プラットフォーム
2. **[Shopify Dev Docs](https://shopify.dev/)** - 開発者向けドキュメント
3. **[Shopify Dev YouTube](https://www.youtube.com/shopifydevs)** - 動画チュートリアル

### 書籍

1. **「エンジニアのためのShopify開発バイブル」** - フィードフォース著
2. **「Hello Shopify Themes」** - テーマ開発入門

### オンラインコース

1. **[デイトラ Shopifyコース](https://daily-trial.com/shopify/)** - 日本語の体系的なコース
2. **[Camp Liquid](https://campliquid.com/)** - Liquid特化のコース
3. **[Udemy Shopifyコース](https://www.udemy.com/topic/shopify/)** - 多様なコース

## EC-CUBEエンジニアへのアドバイス

### 1. まずはテーマ開発から

アプリ開発はReactの学習が必要で、ハードルが高いです。まずはテーマ開発で、Liquidに慣れましょう。TwigとLiquidは似ているので、比較的スムーズに習得できます。

### 2. 「制約の中で最適化する」思考

EC-CUBEは「何でもできる自由度」が魅力ですが、Shopifyは「制約の中で最適化する」プラットフォームです。この思考の転換が重要です。

### 3. 両方できる強みを活かす

EC-CUBEとShopify、両方できるエンジニアは希少です。クライアントの要件に応じて最適なプラットフォームを提案できる立場は、大きな強みになります。

### 4. コミュニティに参加する

- [Shopify Partners Slack](https://shopifypartners.slack.com/)
- [Shopify Community](https://community.shopify.com/)

## EC-CUBE vs Shopify、どちらを選ぶべきか？

最後に、クライアントへの提案時の判断基準を整理します。

| 要件 | EC-CUBE向き | Shopify向き |
|------|------------|-------------|
| カスタマイズ | フルスクラッチが必要 | 標準機能+アプリで十分 |
| 運用体制 | 技術者がいる | 非エンジニアが運用 |
| 初期費用 | 抑えたい | 月額でOK |
| 越境EC | 要件次第 | Shopify向き |
| 日本特有の商習慣 | EC-CUBE向き | アプリで対応 |

**両方のスキルを持つことで、クライアントに最適な提案ができるようになります。**

## あなたはどう思いますか？

この記事を読んでいるあなたに質問です。

**Q1. EC-CUBEとShopify、今から始めるならどちらを勧めますか？**

私の意見は「両方学ぶべき」ですが、時間が限られているなら優先順位をつける必要があります。

**Q2. 5年後、EC開発の主流はどうなっていると思いますか？**

- EC-CUBEのようなオンプレ型が復権する
- Shopifyのようなサース型がさらに拡大する
- ヘッドレスコマースが主流になる

ぜひコメントで教えてください。異論・反論も大歓迎です！

## まとめ

EC-CUBEエンジニアがShopify開発者になるためのロードマップをまとめました。

1. **Phase 1**: Liquidとテーマ開発（1〜2ヶ月）
2. **Phase 2**: JavaScript/Ajax API（1ヶ月）
3. **Phase 3**: React/Remixでアプリ開発（2〜3ヶ月）
4. **Phase 4**: Hydrogen等の発展スキル（3ヶ月〜）

EC-CUBEで培ったECの業務知識やテンプレートエンジンの経験は、Shopify開発でも活きます。「考え方の転換」さえできれば、最短6ヶ月でShopify開発者としてのキャリアをスタートできます。

## 参考リンク

- [Shopify Academy - Development Fundamentals](https://www.shopifyacademy.com/path/shopify-development-fundamentals)
- [Build a Shopify app using Remix](https://shopify.dev/docs/apps/build/build?framework=remix)
- [Hydrogen: Shopify's headless commerce framework](https://hydrogen.shopify.dev/)
- [Liquid template language](https://shopify.github.io/liquid/)
- [プロのShopifyエンジニアになるための学習ロードマップ](https://dtnavi.tcdigital.jp/shopify/shopify-engineer/)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---