---
title: "「任せるEC」の時代到来 - EC-CUBEサイトをAIエージェント対応にする"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "ai", "ec", "ビジネス"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

2026年、ECの世界に大きな変化が起きています。

**「検索して、比較して、カートに入れて、決済する」**

この当たり前だった購買行動が、根本から変わろうとしています。

新しい購買体験は **「AIに任せる」** です。

この記事では、「エージェンティックコマース」と呼ばれる新しい潮流と、EC-CUBEサイトがどう対応すべきかを解説します。

## エージェンティックコマースとは

**エージェンティックコマース（Agentic Commerce）** とは、AIエージェントが消費者に代わって購買行動を行う商取引形態です。

従来のEC:
```
人間 → ECサイトを訪問 → 検索 → 比較 → カート → 決済
```

エージェンティックコマース:
```
人間 → AIに依頼 → AIが検索・比較・選択・決済を代行
```

マッキンゼーの予測によると、2020年代末には **米小売りに1兆ドルの売上** をもたらし、オンライン売上高全体の **約3分の1** を占める可能性があるとされています。

## 何が起きているのか

### OpenAI「Instant Checkout」

2025年9月、OpenAIは「Instant Checkout」を発表しました。ChatGPT内で会話しながら商品を探し、**チャットから離れずに購入が完結** します。

```
ユーザー: 「30代男性向けのビジネスカジュアルな靴を探して」
ChatGPT: 「〇〇がおすすめです。サイズと色を選んで購入しますか？」
ユーザー: 「黒の27cmで」
ChatGPT: 「注文が完了しました」
```

### Google「Shop with AI Mode」

Googleも対話型ショッピング機能を展開中です。写真をアップロードして試着シミュレーション（Virtual Try-On）も可能で、将来的には購入代行機能も予定されています。

### Universal Commerce Protocol（UCP）

Google、Shopify、Walmart、Targetなど大手企業が **「UCP」** という共通プロトコルを策定中です。

参加企業:
- **主導**: Google, Shopify, Etsy, Wayfair, Target, Walmart
- **賛同**: American Express, Best Buy, Macy's, Mastercard, PayPal, Stripe, Visa など20社以上

UCPにより、AIエージェントはどの店舗でも統一ルールで商取引を実行できるようになります。

## EC事業者への影響

### 「人間が訪問しないECサイト」の時代

衝撃的ですが、**人間がECサイトを訪問しなくなる** 可能性があります。

AIエージェントが:
1. 商品情報を取得
2. 在庫を確認
3. 価格を比較
4. 注文・決済を実行

すべてをAPIやデータフィードで処理するため、「きれいなデザイン」や「使いやすいUI」は **AIには関係ない** のです。

### AIが見るのは「データ」

AIは感情ではなくデータで判断します。

**AIに伝わらない例:**
```
「涼しくて着心地の良い夏向けシャツ」
```

**AIに伝わる例:**
```
素材: リネン100%
重量: 180g
対応季節: 春夏
サイズ: S/M/L/XL
JANコード: 4901234567890
```

## EC-CUBEサイトがすべき対応

### 1. 構造化データの整備

EC-CUBEの商品情報を **構造化データ（JSON-LD）** として出力することが重要です。

```php
// app/Customize/EventListener/StructuredDataListener.php

namespace Customize\EventListener;

use Eccube\Entity\Product;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpKernel\Event\ResponseEvent;
use Symfony\Component\HttpKernel\KernelEvents;

class StructuredDataListener implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            KernelEvents::RESPONSE => 'onResponse',
        ];
    }

    public function onResponse(ResponseEvent $event): void
    {
        // 商品詳細ページでJSON-LDを追加する処理
    }
}
```

Twigテンプレートで直接出力する方法:

```twig
{# app/template/default/Product/detail.twig #}

{% block json_ld %}
<script type="application/ld+json">
{
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "{{ Product.name }}",
    "description": "{{ Product.description_detail | striptags }}",
    "sku": "{{ Product.code_min }}",
    "brand": {
        "@type": "Brand",
        "name": "あなたのブランド名"
    },
    "offers": {
        "@type": "Offer",
        "url": "{{ url('product_detail', {id: Product.id}) }}",
        "priceCurrency": "JPY",
        "price": "{{ Product.getPrice02IncTaxMin }}",
        "availability": "{% if Product.stock_find %}https://schema.org/InStock{% else %}https://schema.org/OutOfStock{% endif %}",
        "seller": {
            "@type": "Organization",
            "name": "あなたのショップ名"
        }
    }
    {% if Product.ProductImage | length > 0 %},
    "image": [
        {% for img in Product.ProductImage %}"{{ asset(img, 'save_image') }}"{% if not loop.last %},{% endif %}{% endfor %}
    ]
    {% endif %}
}
</script>
{% endblock %}
```

### 2. 商品データの充実

AIが判断するために必要な情報を **項目として** 登録します。

EC-CUBEの規格や自由項目を活用:

| 項目 | 例 |
|------|-----|
| 素材 | コットン100% |
| 重量 | 250g |
| サイズ詳細 | 着丈70cm, 身幅52cm |
| JANコード | 4901234567890 |
| 原産国 | 日本 |
| 対象年齢 | 20-40代 |

```php
// 商品の自由項目を追加する Trait
// app/Customize/Entity/ProductTrait.php

namespace Customize\Entity;

use Doctrine\ORM\Mapping as ORM;
use Eccube\Annotation\EntityExtension;

/**
 * @EntityExtension("Eccube\Entity\Product")
 */
trait ProductTrait
{
    /**
     * @ORM\Column(type="string", length=255, nullable=true)
     */
    private ?string $material = null;

    /**
     * @ORM\Column(type="integer", nullable=true)
     */
    private ?int $weight = null;

    /**
     * @ORM\Column(type="string", length=13, nullable=true)
     */
    private ?string $jan_code = null;

    // getter/setter...
}
```

### 3. 在庫データのリアルタイム性

AIは **「注文後の欠品」を強く避けます** 。在庫データの信頼性がショップの評価に直結します。

```php
// 在庫をリアルタイムで返すAPI
// app/Customize/Controller/Api/StockController.php

namespace Customize\Controller\Api;

use Eccube\Repository\ProductClassRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\Routing\Annotation\Route;

class StockController extends AbstractController
{
    public function __construct(
        private ProductClassRepository $productClassRepository
    ) {
    }

    /**
     * @Route("/api/stock/{code}", name="api_stock", methods={"GET"})
     */
    public function getStock(string $code): JsonResponse
    {
        $productClass = $this->productClassRepository->findOneBy([
            'code' => $code,
        ]);

        if (!$productClass) {
            return $this->json(['error' => 'Product not found'], 404);
        }

        return $this->json([
            'sku' => $productClass->getCode(),
            'stock' => $productClass->getStock(),
            'unlimited' => $productClass->isStockUnlimited(),
            'updated_at' => (new \DateTime())->format('c'),
        ]);
    }
}
```

### 4. 商品フィード（データフィード）の提供

AIエージェントやGoogle Merchant Centerが取得できる **XMLフィード** を提供します。

```php
// app/Customize/Controller/Feed/ProductFeedController.php

namespace Customize\Controller\Feed;

use Eccube\Repository\ProductRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

class ProductFeedController extends AbstractController
{
    public function __construct(
        private ProductRepository $productRepository
    ) {
    }

    /**
     * @Route("/feed/products.xml", name="product_feed")
     */
    public function index(): Response
    {
        $products = $this->productRepository->findBy([
            'Status' => 1, // 公開中
        ]);

        $response = $this->render('Feed/products.xml.twig', [
            'products' => $products,
        ]);

        $response->headers->set('Content-Type', 'application/xml');

        return $response;
    }
}
```

```xml
{# app/template/default/Feed/products.xml.twig #}
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:g="http://base.google.com/ns/1.0">
    <title>商品フィード</title>
    <link href="{{ url('homepage') }}"/>
    <updated>{{ 'now' | date('c') }}</updated>

    {% for product in products %}
    <entry>
        <g:id>{{ product.id }}</g:id>
        <g:title>{{ product.name }}</g:title>
        <g:description>{{ product.description_detail | striptags }}</g:description>
        <g:link>{{ url('product_detail', {id: product.id}) }}</g:link>
        <g:price>{{ product.getPrice02IncTaxMin }} JPY</g:price>
        <g:availability>{% if product.stock_find %}in stock{% else %}out of stock{% endif %}</g:availability>
        <g:condition>new</g:condition>
    </entry>
    {% endfor %}
</feed>
```

#### プラグインで簡単に実装する

自作が面倒な場合は、**商品データフィードプラグイン** を使うと簡単です。

https://www.ec-cube.net/products/detail.php?product_id=3209

**商品データフィードプラグイン（Google/Meta/LINE/TikTok対応）** は、以下のプラットフォーム向けのフィードを管理画面から簡単に生成できます。

| 対応サービス | 用途 |
|-------------|------|
| Google Merchant Center | Google ショッピング広告、無料リスティング |
| Meta（Facebook/Instagram） | Facebook/Instagramショップ |
| LINE | LINE広告 |
| TikTok | TikTok広告 |

Google Merchant Centerの商品データ仕様とEC-CUBEのデータ項目の対応表も用意されており、GMC対応に必要な項目（GTIN、商品カテゴリ、状態、送料など）をEC-CUBEの管理画面から設定できます。

AIエージェント時代に備えて、まずはGoogle Merchant Centerへの登録から始めるのがおすすめです。

### 5. 会話型コマースへの対応

将来的には、EC-CUBEサイト自体にチャットボットを組み込むことも検討できます。

```javascript
// チャットウィジェットの組み込み例（OpenAI API使用）
// 注: 実際の実装ではセキュリティに十分注意してください

async function chat(message) {
    const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });
    return response.json();
}
```

## 中小EC事業者のチャンス

この変化は **脅威ではなくチャンス** です。

### なぜチャンスなのか

1. **広告費競争からの解放**: AIは広告ではなくデータで判断
2. **商品力の正当な評価**: 良い商品を正確に記述すれば選ばれる
3. **大手との差別化**: ニッチな商品はAIに「発見」されやすい

### 今すぐできること

| 優先度 | アクション |
|--------|-----------|
| 高 | 商品情報の構造化（素材、サイズ、重量等） |
| 高 | JSON-LD構造化データの実装 |
| 中 | 在庫データのリアルタイム同期 |
| 中 | 商品フィードの提供 |
| 低 | UCP対応の動向ウォッチ |

## まとめ

「任せるEC」の時代が到来しています。

- **AIエージェントが購買を代行** する時代へ
- **人間ではなくAIに選ばれる** ECサイトが勝つ
- EC-CUBEサイトは **構造化データと在庫精度** で勝負

ECサイトの役割は「人間に商品を見せる場所」から「AIに商品情報を提供する場所」へと変化しつつあります。

今のうちに準備を始めましょう。

## 参考リンク

- [2026年ネット通販のトレンド10選](https://netshop.impress.co.jp/e/2026/01/08/15390)
- [エージェンティックコマースとは](https://next-engine.net/ec-blog/agentic-commerce/)
- [Universal Commerce Protocol（UCP）](https://www.publickey1.jp/blog/26/ecaiuniversal_commerce_protocolucp.html)
- [2026年の新EC戦略｜生成AIショッピング](https://omokaji-web.co.jp/strategy/ec-ai-shopping-2026/)
- [会話型コマース市場規模](https://www.gii.co.jp/report/moi1934914-conversational-commerce-market-share-analysis.html)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
