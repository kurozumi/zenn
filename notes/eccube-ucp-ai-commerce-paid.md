## はじめに：AIがショッピングを変える時代

「AIに頼んで買い物してもらう」

そんな未来が、もう目の前に来ています。

Google の AI Mode in Search や Gemini アプリでは、ユーザーが「〇〇を買いたい」と話しかけるだけで、AIエージェントが商品を探し、比較し、購入まで完了してくれる世界が実現しつつあります。

この「AIエージェントによるショッピング」を可能にするのが、**Universal Commerce Protocol（UCP）** です。

## UCPとは何か？

**UCP（Universal Commerce Protocol）** は、Google と Shopify が中心となり、Etsy、Walmart、Target、Wayfair などの業界大手と共同開発した**オープンソースのプロトコル**です。

https://ucp.dev/

### 支持・参加企業

UCP には以下のような企業が参加・支持しています：

- **共同開発**: Google、Shopify、Etsy、Wayfair、Target、Walmart
- **決済プロバイダー**: Stripe、Adyen、PayPal、Mastercard、Visa、American Express、Klarna、Affirm
- **小売企業**: Best Buy、The Home Depot、Gap、Macy's、Zalando、Flipkart

40社以上がこのプロトコルを支持しており、**事実上の業界標準**になりつつあります。

### UCPが解決する問題

従来、AIエージェントが EC サイトで買い物をするには、サイトごとに個別の連携が必要でした。これは N × N の複雑性を生み出します。

UCPは「共通言語」を定義することで、**一度の実装で、あらゆるAIエージェントと連携**できるようになります。

```
従来: AIエージェントA × ECサイト1 + AIエージェントA × ECサイト2 + ...
UCP: AIエージェント ← UCP → ECサイト（共通インターフェース）
```

### UCPの技術的特徴

- **REST / JSON-RPC** によるシンプルな API
- **OAuth 2.0** による認証
- **Agent Payments Protocol (AP2)** による安全な決済
- **Agent2Agent (A2A)** / **Model Context Protocol (MCP)** との互換性
- **`/.well-known/ucp`** マニフェストによる機能の自動検出

## なぜEC-CUBEにUCPが必要なのか？

### 1. AIショッピングの波に乗り遅れない

Shopify はすでに UCP 対応を進めています。日本の EC サイトがこの波に乗り遅れれば、**AI エージェント経由の顧客を取りこぼす**ことになります。

### 2. 日本初のUCP対応オープンソースEC

EC-CUBE が UCP に対応すれば、**日本初のUCP対応オープンソースECプラットフォーム**になる可能性があります。これは EC-CUBE コミュニティにとって大きなアドバンテージです。

### 3. グローバル展開の足がかり

UCP は国際的なプロトコルです。対応することで、日本の EC-CUBE サイトが**グローバルな AI エコシステム**に参加できるようになります。

## EC-CUBEでの実装イメージ

EC-CUBE の GitHub に、すでに [UCP 対応の Issue](https://github.com/EC-CUBE/ec-cube/issues/6574) が立てられています。

### 必要な3つのエンドポイント

UCPでは、以下の3つのエンドポイントを実装します：

```
POST   /checkout-sessions           # セッション作成
PUT    /checkout-sessions/{id}      # セッション更新（配送先変更など）
POST   /checkout-sessions/{id}/complete  # 注文確定
```

### 1. セッション作成 (`POST /checkout-sessions`)

AIエージェントが「この商品を買いたい」とリクエストすると、EC-CUBE がチェックアウトセッションを作成します。

```php
// イメージ（実際の実装は要設計）
#[Route('/checkout-sessions', name: 'ucp_checkout_session_create', methods: ['POST'])]
public function createSession(Request $request): JsonResponse
{
    $data = json_decode($request->getContent(), true);

    // カートを作成
    $cart = $this->cartService->createCartFromUCP($data['cart']);

    // セッションを作成
    $session = new CheckoutSession();
    $session->setCart($cart);
    $session->setStatus('incomplete');
    $session->setExpiresAt(new \DateTime('+30 minutes'));

    $this->entityManager->persist($session);
    $this->entityManager->flush();

    return $this->json([
        'id' => $session->getSessionId(),
        'total' => $this->formatAmount($cart->getTotal()),
        'currency' => 'JPY',
        'links' => [
            ['rel' => 'privacy_policy', 'href' => $this->baseInfo->getPrivacyPolicyUrl()],
            ['rel' => 'terms_of_service', 'href' => $this->baseInfo->getTermsOfServiceUrl()],
        ],
    ]);
}
```

### 2. セッション更新 (`PUT /checkout-sessions/{id}`)

配送先住所が更新されたら、送料や税金を再計算します。

```php
#[Route('/checkout-sessions/{id}', name: 'ucp_checkout_session_update', methods: ['PUT'])]
public function updateSession(string $id, Request $request): JsonResponse
{
    $session = $this->checkoutSessionRepository->findBySessionId($id);
    $data = json_decode($request->getContent(), true);

    // 配送先を更新
    if (isset($data['fulfillment']['address'])) {
        $session->setFulfillmentData($data['fulfillment']);

        // PurchaseFlow で送料・税金を再計算
        $this->purchaseFlow->calculate($session->getCart());
    }

    return $this->json([
        'id' => $session->getSessionId(),
        'subtotal' => $this->formatAmount($session->getSubtotal()),
        'tax' => $this->formatAmount($session->getTax()),
        'shipping' => $this->formatAmount($session->getShipping()),
        'total' => $this->formatAmount($session->getTotal()),
        'shipping_options' => $this->getShippingOptions($session),
    ]);
}
```

### 3. セッション完了 (`POST /checkout-sessions/{id}/complete`)

ユーザーが「注文する」と言ったら、注文を確定します。

```php
#[Route('/checkout-sessions/{id}/complete', name: 'ucp_checkout_session_complete', methods: ['POST'])]
public function completeSession(string $id, Request $request): JsonResponse
{
    $session = $this->checkoutSessionRepository->findBySessionId($id);

    // 注文を作成
    $order = $this->orderHelper->createOrderFromCheckoutSession($session);

    // PurchaseFlow で購入処理
    $this->purchaseFlow->commit($order);

    $session->setOrder($order);
    $session->setStatus('completed');

    $this->entityManager->flush();

    return $this->json([
        'order_id' => $order->getOrderNo(),
        'order_url' => $this->generateUrl('mypage_history', [
            'order_no' => $order->getOrderNo()
        ], UrlGeneratorInterface::ABSOLUTE_URL),
    ]);
}
```

### 必要な新規エンティティ

```php
#[ORM\Entity(repositoryClass: CheckoutSessionRepository::class)]
#[ORM\Table(name: 'dtb_checkout_session')]
class CheckoutSession
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column]
    private ?int $id = null;

    #[ORM\Column(length: 255, unique: true)]
    private string $sessionId;

    #[ORM\Column(length: 20)]
    private string $status = 'incomplete';

    #[ORM\Column(length: 3)]
    private string $currency = 'JPY';

    #[ORM\Column(type: 'datetime')]
    private \DateTimeInterface $expiresAt;

    #[ORM\ManyToOne(targetEntity: Order::class)]
    private ?Order $Order = null;

    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $buyerData = null;

    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $fulfillmentData = null;

    #[ORM\Column(type: 'json', nullable: true)]
    private ?array $paymentData = null;

    // ... getter/setter
}
```

## 実装ロードマップ（提案）

### Phase 1: 基盤構築
- `CheckoutSession` エンティティの設計・実装
- データベースマイグレーション作成
- 基本的なリポジトリ実装

### Phase 2: API 実装
- 3つのエンドポイントの実装
- 既存の `PurchaseFlow` との連携
- 住所フォーマット変換（EC-CUBE ⇔ UCP）

### Phase 3: セキュリティ・認証
- OAuth 2.0 認証の実装
- リクエストバリデーション
- レート制限

### Phase 4: テスト・ドキュメント
- ユニットテスト / 統合テスト
- `/.well-known/ucp` マニフェスト
- 設定ドキュメント

## みんなで開発しませんか？

**EC-CUBE を AI 時代に対応させるチャンス**です。

この機能は、一人で作るには大きすぎます。でも、コミュニティの力を合わせれば実現できます。

### 参加方法

1. **GitHub Issue にコメント**
   https://github.com/EC-CUBE/ec-cube/issues/6574
   アイデアや意見をぜひ共有してください。

2. **プルリクエストを送る**
   小さな機能から始めてもOKです。

3. **テストに協力する**
   実装ができたら、テストに協力してください。

4. **ドキュメントを書く**
   技術文書の翻訳や、設定手順の作成も重要な貢献です。

### 議論したいこと

- 認証方式はどうするか？（OAuth 2.0? APIキー?）
- プラグインとして実装するか、コアに組み込むか？
- Google Pay 以外の決済プロバイダーへの対応は？
- MCP (Model Context Protocol) との連携は？

## まとめ

**AI がショッピングを代行する時代**が来ています。

EC-CUBE が UCP に対応すれば、日本の EC サイトがこの新しい時代に乗り遅れることはありません。

技術的には挑戦的ですが、EC-CUBE の強力なコミュニティなら実現できると信じています。

**一緒に、EC-CUBE を AI 時代の EC プラットフォームにしましょう！**

## 参考リンク

- [Universal Commerce Protocol 公式サイト](https://ucp.dev/)
- [Google UCP ドキュメント](https://developers.google.com/merchant/ucp)
- [Google Developers Blog: Under the Hood UCP](https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/)
- [EC-CUBE UCP 対応 Issue #6574](https://github.com/EC-CUBE/ec-cube/issues/6574)
- [Shopify UCP 対応記事](https://shopify.engineering/ucp)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---