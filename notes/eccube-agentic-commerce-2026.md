# Shopifyは準備完了、EC-CUBEは未対応。2026年AIエージェント決済を生き残る方法

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論から言います

**EC-CUBEは、2026年以降の「エージェント決済」時代に対応できていません。**

Shopifyはすでに「Checkout Kit」と「Universal Commerce Protocol」で準備完了。EC-CUBEは未対応。このまま何もしなければ、顧客を奪われる可能性があります。

でも、**今から準備すれば間に合います**。

---

**EC-CUBE開発者への質問:**
- 商品検索APIはありますか？
- AIが決済を完了できるAPIはありますか？
- schema.org形式の構造化データは出力していますか？

3つともNoなら、この記事を読む価値があります。

## 2026年、AIエージェントが購買を変える

**「この条件なら買っていいよ」**

ユーザーがAIにそう伝えるだけで、商品の検索から比較、決済まで自動で完了する。そんな時代が2026年に本格到来します。

これを**エージェント決済**（Agentic Commerce）と呼びます。

McKinseyの予測では、このチャネルは2030年までに**3〜5兆ドル規模**に成長するとされています。また、Gartnerは2026年末までに企業ソフトウェア購入の**25%**がAIエージェントを介すると予測しています。

> **「人間はECサイトを見ない。AIがAPIを叩く。」**
> これが2026年以降の購買体験です。

## エージェント決済とは何か

### 従来のEC vs エージェント決済

| 項目 | 従来のEC | エージェント決済 |
|------|---------|----------------|
| **購買者** | 人間がブラウザで操作 | AIエージェントが代行 |
| **商品発見** | 検索、カテゴリ、広告 | API経由で構造化データを取得 |
| **比較検討** | ユーザーが複数サイトを閲覧 | AIがリアルタイムで最適解を算出 |
| **決済** | ユーザーがフォーム入力 | AIが条件内で自動完了 |

### 具体的なシナリオ

```
ユーザー: 「ランニングシューズ、2万円以下で評価4以上のやつ、
          在庫があったら買っておいて」

AIエージェント:
  1. 複数ECサイトのAPIを叩いて商品を検索
  2. 条件に合う商品を比較
  3. 最適な商品を選定
  4. 自動で決済を完了
  5. ユーザーに結果を報告
```

**人間はECサイトを見ない。AIがAPIを叩く。**

これが2026年以降の購買体験です。

## 2大プロトコルの登場

### Google UCP（Universal Commerce Protocol）

2026年1月に発表。Walmart、Target、Shopify、Etsy など20社以上がパートナー。

- オープンプロトコル
- インテントベースの商品発見
- 構造化データによる商品情報提供

### OpenAI ACP（Agentic Commerce Protocol）

ChatGPT Instant Checkout を支える基盤。Stripe決済と連携。

- オープンスタンダード
- 会話ベースの商品発見
- リアルタイムの状態管理

```
// ACPの基本的な流れ
1. エージェントが商品を検索（API）
2. チェックアウトを作成（API）
3. 状態を確認：incomplete / requires_escalation / ready_for_complete
4. 決済を完了（API）
```

## EC-CUBEの現状と課題

### 現状：人間向けに最適化されている

EC-CUBEは優れたECパッケージですが、**人間がブラウザで操作する**ことを前提に設計されています。

```
現在のEC-CUBEの構造
├── フロント画面（Twig）← 人間が見る
├── 管理画面（Twig）← 人間が操作
├── Controller（HTTP）← ブラウザからのリクエスト
└── API（限定的）← 外部連携用
```

### 課題1: APIファーストではない

エージェント決済では、AIは**HTMLを解析しない**。APIで構造化データを取得します。

```php
// AIエージェントが求めるもの
GET /api/products?price_max=20000&rating_min=4&in_stock=true

// 返ってくるべきもの
{
  "products": [
    {
      "id": "123",
      "name": "ランニングシューズ Pro",
      "price": 18000,
      "currency": "JPY",
      "rating": 4.5,
      "stock": 10,
      "checkout_url": "https://..."
    }
  ]
}
```

EC-CUBEの現在のAPIはここまで整備されていません。

### 課題2: チェックアウトAPIがない

Shopifyには「Checkout Kit」があり、AIエージェントがプログラマティックに決済を完了できます。

```
Shopifyのチェックアウト状態
├── incomplete（情報不足 → APIで解決試行）
├── requires_escalation（人間の介入が必要 → ブラウザにハンドオフ）
└── ready_for_complete（完了可能 → APIで決済実行）
```

EC-CUBEには、このような**ステートマシンとしてのチェックアウトAPI**がありません。

### 課題3: 構造化データの不足

AIエージェントは、schema.org形式の構造化データを重視します。

```html
<!-- 必要な構造化データ -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "ランニングシューズ Pro",
  "offers": {
    "@type": "Offer",
    "price": "18000",
    "priceCurrency": "JPY",
    "availability": "https://schema.org/InStock"
  }
}
</script>
```

EC-CUBEのデフォルトテンプレートには、これが十分に含まれていません。

## EC-CUBEが生き残るために必要なこと

### 1. Product Feed APIの整備

AIエージェントが商品を検索できるAPIが必要です。

```php
namespace Customize\Controller\Api;

use Eccube\Entity\Master\ProductStatus;
use Eccube\Repository\ProductRepository;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Attribute\Route;

class ProductFeedController extends AbstractController
{
    public function __construct(
        private ProductRepository $productRepository,
    ) {}

    #[Route('/api/v1/products', name: 'api_products', methods: ['GET'])]
    public function index(Request $request): JsonResponse
    {
        // 入力値のバリデーション
        $priceMax = $request->query->get('price_max');
        $priceMin = $request->query->get('price_min');

        if ($priceMax !== null && !ctype_digit($priceMax)) {
            return $this->json(['error' => 'Invalid price_max'], 400);
        }

        // QueryBuilderで商品を検索
        $qb = $this->productRepository->createQueryBuilder('p')
            ->innerJoin('p.ProductClasses', 'pc')
            ->where('p.Status = :status')
            ->setParameter('status', ProductStatus::DISPLAY_SHOW);

        if ($priceMax !== null) {
            $qb->andWhere('pc.price02 <= :price_max')
               ->setParameter('price_max', (int) $priceMax);
        }
        if ($priceMin !== null) {
            $qb->andWhere('pc.price02 >= :price_min')
               ->setParameter('price_min', (int) $priceMin);
        }
        if ($request->query->getBoolean('in_stock')) {
            $qb->andWhere('pc.stock > 0 OR pc.stock_unlimited = true');
        }

        $products = $qb->getQuery()->getResult();

        return $this->json([
            'products' => array_map(fn($p) => [
                'id' => $p->getId(),
                'name' => $p->getName(),
                'price' => $p->getPrice02IncTaxMin(),
                'currency' => 'JPY',
                'stock' => $p->getStockMin(),
                'url' => $this->generateUrl('product_detail', ['id' => $p->getId()]),
                'image' => $p->getMainListImage(),
            ], $products),
        ]);
    }
}
```



### 2. Checkout APIの実装

AIエージェントが決済を完了できるAPIが必要です。

```php
namespace Customize\Controller\Api;

use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\Routing\Attribute\Route;

class CheckoutApiController extends AbstractController
{
    #[Route('/api/v1/checkout', name: 'api_checkout_create', methods: ['POST'])]
    public function create(Request $request): JsonResponse
    {
        // カートを作成し、チェックアウトセッションを開始
        $checkout = $this->checkoutService->create($request->toArray());

        return $this->json([
            'checkout_id' => $checkout->getId(),
            'status' => $checkout->getStatus(), // incomplete, requires_escalation, ready
            'total' => $checkout->getTotal(),
            'currency' => 'JPY',
            'required_fields' => $checkout->getMissingFields(),
            'continue_url' => $checkout->getContinueUrl(), // 人間にハンドオフする場合
        ]);
    }

    #[Route('/api/v1/checkout/{id}', name: 'api_checkout_update', methods: ['PATCH'])]
    public function update(string $id, Request $request): JsonResponse
    {
        // 住所、支払い方法などを更新
        $checkout = $this->checkoutService->update($id, $request->toArray());

        return $this->json([
            'checkout_id' => $checkout->getId(),
            'status' => $checkout->getStatus(),
            'required_fields' => $checkout->getMissingFields(),
        ]);
    }

    #[Route('/api/v1/checkout/{id}/complete', name: 'api_checkout_complete', methods: ['POST'])]
    public function complete(string $id): JsonResponse
    {
        // 決済を完了
        $order = $this->checkoutService->complete($id);

        return $this->json([
            'order_id' => $order->getId(),
            'status' => 'completed',
            'total' => $order->getPaymentTotal(),
        ]);
    }
}
```

### 3. 構造化データの自動出力

商品詳細ページに構造化データを追加するカスタマイズです。

```twig
{# app/template/default/Product/detail.twig #}

{% block json_ld %}
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "{{ Product.name }}",
  "description": "{{ Product.description_detail|striptags|slice(0, 500) }}",
  "image": "{{ asset(Product.MainListImage|no_image_product, 'save_image') }}",
  "sku": "{{ Product.code_min }}",
  "brand": {
    "@type": "Brand",
    "name": "{{ BaseInfo.shop_name }}"
  },
  "offers": {
    "@type": "Offer",
    "url": "{{ url('product_detail', {id: Product.id}) }}",
    "price": "{{ Product.getPrice02IncTaxMin }}",
    "priceCurrency": "JPY",
    "availability": "{{ Product.StockMin > 0 ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock' }}",
    "seller": {
      "@type": "Organization",
      "name": "{{ BaseInfo.shop_name }}"
    }
  }
}
</script>
{% endblock %}
```

### 4. MCP（Model Context Protocol）対応

Shopifyは「Shopify MCP Server」を提供し、AIエージェントとの標準化されたインターフェースを実現しています。EC-CUBEも同様の対応が必要かもしれません。

## 現実的なロードマップ

### Phase 1: 構造化データの整備（今すぐ）

- 商品ページにschema.org形式のJSON-LDを追加
- Google Merchant Centerへの商品フィード連携
- サイトマップの最適化

### Phase 2: 読み取り専用APIの実装（短期）

- 商品検索API
- 在庫確認API
- 価格取得API

### Phase 3: チェックアウトAPIの実装（中期）

- カート作成API
- 配送先設定API
- 決済完了API
- Webhookによる注文通知

### Phase 4: プロトコル対応（長期）

- Google UCP対応
- OpenAI ACP対応
- MCP Server実装

## EC-CUBEコミュニティへの提言

エージェント決済は「いつか来る未来」ではありません。Gartnerの予測では**2026年末までに企業ソフトウェア購入の25%**がAIエージェント経由になるとされています。

EC-CUBEが生き残るためには：

1. **APIファースト設計への転換**が必要
2. **プラグインとしてのエージェント対応**が現実的な第一歩
3. **コミュニティでの議論**を今すぐ始めるべき

Shopifyはすでに対応を完了しています。EC-CUBEが同じ土俵に立つには、今から準備を始める必要があります。

## あなたはどちら派？

**本体派:** EC-CUBE本体でAPIファースト設計に転換すべき
**プラグイン派:** プラグインで対応すればいい、本体は現状維持

この選択は、EC-CUBEの今後5年を決める重要な分岐点です。

また、こんな疑問もあるでしょう：

- 日本市場でエージェント決済は本当に普及するのか？
- Shopifyに勝てないなら、EC-CUBEの存在意義は何になるのか？
- 小規模ECサイトにAPIファースト設計は必要か？

ぜひコメントで議論しましょう。**EC-CUBEの未来を一緒に考えませんか？**

## 参考リンク

- [2026年はエージェント決済元年？（ECzine）](https://eczine.jp/article/detail/17683)
- [Agentic Commerce Protocol - OpenAI](https://developers.openai.com/commerce)
- [Shopify Agentic Commerce](https://shopify.dev/docs/agents)
- [Building the Universal Commerce Protocol - Shopify Engineering](https://shopify.engineering/ucp)
- [The rise of agentic commerce（nshift）](https://nshift.com/blog/agentic-commerce-ai-shopping-agents-2026)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---