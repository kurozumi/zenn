---
title: "あなたのEC-CUBEストア、ChatGPTから買えますか？UCP対応の始め方"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "php", "mcp"]
published: true
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

**あなたが管理している EC-CUBE ストアは、ChatGPT や Claude から商品を買えますか？**

2026年4月22日、Shopify は **Universal Commerce Protocol（UCP）** を全加盟店向けに本格稼働させました。Google と共同開発したこのオープンスタンダードは、Etsy・Target・Walmart・Wayfair といった大手プラットフォームも支持を表明し、AI エージェントが EC サイトを横断して商品検索〜購入を完結させる共通基盤として急速に普及しています。

Shopify 社長 Harley Finkelstein が Q3 2025 決算発表で明らかにしたデータによれば、**2025年1月以降の AI 起因の注文数は11倍、AI 由来のトラフィックは7倍に増加**しています（[TechCrunch 報道](https://techcrunch.com/2025/11/04/shopify-says-ai-traffic-is-up-7x-since-january-ai-driven-orders-are-up-11x/)）。AI エージェントが購入を完結できる環境を整えたから、AI エージェントが顧客を連れてくる——この現実が数字で示されています。

**結論を先に言います。EC-CUBE 4.3 はこの波に乗れていません。** カタログ検索は△、カート操作は❌、チェックアウト API は❌です。ただし絶望する必要はありません。MCP サーバープラグインを起点とした4段階のロードマップを実装すれば、段階的に対応できます。

:::details この記事の TL;DR（先に結論を読みたい方へ）
- 2026年4月、Shopify が UCP（AI購入プロトコル）を本格稼働。AI エージェントが EC サイトを横断して購入を完結させる時代が来た
- EC-CUBE 4.3 はカート操作・チェックアウト API が未実装で、UCP に対応できていない
- **まずやること**: MCP サーバープラグイン（`search_catalog` / `create_cart` / `get_order`）を開発する
- `/.well-known/ucp` エンドポイントを公開するだけで、AI エージェントにストアを「発見」させられる
- PHP SDK はまだ存在しない。Symfony Bundle として OSS 公開すれば EC-CUBE コミュニティへの貢献になる

| Phase | 内容 | 難易度 |
|---|---|---|
| 1 | MCP サーバープラグイン | ★★☆ |
| 2 | UCP ディスカバリーエンドポイント | ★☆☆ |
| 3 | カート・チェックアウト API | ★★★ |
| 4 | UCP 仕様準拠・PHP SDK OSS 公開 | ★★★ |
:::

この記事では UCP の技術仕様を整理したうえで、EC-CUBE 4.3 の現状ギャップを明確にし、具体的な対応ロードマップを解説します。

## UCP（Universal Commerce Protocol）とは

UCP は「AIエージェントがあらゆるマーチャントと接続・取引するためのオープンスタンダード」です。仕様は [ucp.dev](https://ucp.dev) で Apache License 2.0 の下に公開されており、誰でも実装・採用できます。

### 3層アーキテクチャ

```
[Universal Primitives]     動的ネゴシエーション・日付ベースバージョニング
[Standardized Operations]  カタログ / カート / チェックアウト / 注文追跡
[Custom Extensions]        割引・フルフィルメント・決済トークン等の独自拡張
```

Capability の名前空間はリバースドメイン形式（`dev.ucp.shopping.*`）で定義されており、中央承認機構なしに各ドメイン所有者が独自拡張を追加できます（例：`com.loyaltyprovider.points`）。

### エージェント発見の仕組み：`/.well-known/ucp`

UCP では、マーチャントが `/.well-known/ucp` に自身のケイパビリティを JSON で公開します。AI エージェントはこのエンドポイントを参照し、そのストアが何の機能を持つかを自動的に把握します。

```json
{
  "ucp": {
    "version": "2026-04-08",
    "services": {
      "dev.ucp.shopping": [
        {
          "transport": "rest",
          "endpoint": "https://shop.example.com/ucp/v1"
        }
      ]
    },
    "capabilities": {
      "dev.ucp.shopping.catalog.search": [{ "version": "2026-04-08" }],
      "dev.ucp.shopping.catalog.lookup": [{ "version": "2026-04-08" }],
      "dev.ucp.shopping.cart":           [{ "version": "2026-04-08" }],
      "dev.ucp.shopping.checkout":       [{ "version": "2026-04-08" }],
      "dev.ucp.shopping.order":          [{ "version": "2026-04-08" }]
    },
    "payment_handlers": {}
  }
}
```

サポートするトランスポートは `rest`・`mcp`・`a2a` などで、同一のケイパビリティを複数トランスポートで公開できます。

### MCP ツールとして公開されるコマース機能

Shopify が UCP のトランスポートとして MCP を採用し、以下のツールを公式に公開しています。

| カテゴリ | ツール名 |
|---|---|
| Catalog | `search_catalog` / `lookup_catalog` / `get_product` |
| Cart | `create_cart` / `get_cart` / `update_cart` / `cancel_cart` |
| Checkout | `create_checkout` / `get_checkout` / `update_checkout` / `complete_checkout` / `cancel_checkout` |
| Order | `get_order` |

### チェックアウト状態機械

エージェントが自律的に購入を完結させるために、UCP はチェックアウトの状態を以下のように定義しています。

| 状態 | 種別 | 内容 |
|---|---|---|
| `incomplete` | 非終端 | 必須情報が不足。`update_checkout` で解決、`continue_url` を含む |
| `requires_escalation` | 非終端 | API 経由では解決不可。`continue_url` へ人間を誘導 |
| `ready_for_complete` | 非終端 | 全情報収集済み。`complete_checkout` で確定可能 |
| `complete_in_progress` | 中間 | `complete_checkout` 呼び出し後の処理中 |
| `completed` | 終端 | 注文確定済み |
| `canceled` | 終端 | キャンセル済み |

Checkout API はエージェントプロファイルの認証が必須で、Cart API は認証不要という設計になっています。

---

## EC-CUBE 4.3 の現状と UCP ギャップ

EC-CUBE 4.3（PHP ^8.1、Symfony ^6.4）には公式の Web API プラグイン `eccube-api4`（v4.3.2）が存在します。GraphQL エンドポイントとして `/api` を公開し、OAuth 2.0（Authorization Code Flow）で認証します。

### 現在対応している機能

**Query（取得）**

| クエリ | 概要 |
|---|---|
| `product(id)` / `products(...)` | 商品・商品クラスの取得 |
| `order(id)` / `orders(...)` | 受注の取得 |
| `customer(id)` / `customers(...)` | 顧客の取得 |

**Mutation（更新）**

| ミューテーション | 概要 |
|---|---|
| `updateProductStock(code, stock, stock_unlimited)` | 在庫数の更新 |
| `updateShipped(id, ...)` | 出荷ステータスの更新・メール送信 |

Webhook は商品・受注・顧客の変更時に通知を送信します。

### UCP との対応ギャップ

| UCP 必須要素 | EC-CUBE 現状 |
|---|---|
| `/.well-known/ucp` ディスカバリー | ❌ 存在しない |
| カート操作 API（`dev.ucp.shopping.cart`） | ❌ 存在しない |
| チェックアウト API（`dev.ucp.shopping.checkout`） | ❌ 存在しない |
| UCP カタログ検索（`dev.ucp.shopping.catalog.search`） | △ `products` クエリはあるが UCP スキーマ非準拠 |
| GID（Global ID）形式の商品 ID | ❌ 整数 ID のみ |
| エージェント認証・信頼レベル管理 | ❌ OAuth2 のみ（UCP エージェントプロファイル未対応） |
| REST トランスポート | ❌ GraphQL のみ |

管理者向けの商品・受注・顧客取得と在庫更新は実装済みですが、**購入フロー（カート〜チェックアウト）が API として公開されておらず**、AI エージェントがユーザーに代わって購入を完結させることができません。

### EC-CUBE 公式ロードマップの実態（GitHub Issues）

EC-CUBE の公式 GitHub には、UCP・MCP 対応に関する以下の Issue が存在します。

**[Issue #6347「MCPサーバーの実装」](https://github.com/EC-CUBE/ec-cube/issues/6347)（2025年4月6日オープン）**
> EC-CUBE用のMCPサーバーがあると、AIとの開発が進む。商品やマスタデータの読取ができると良い。

オープンから1年以上経過しましたが、アサインなし・実装なしの状態が続いています。

**[Issue #6574「ユニバーサルコマースプロトコル（UCP）の対応」](https://github.com/EC-CUBE/ec-cube/issues/6574)（2026年1月15日オープン）**

チェックアウトセッション API（`POST /checkout-sessions` 等）の設計案が議論されています。設計の議論は始まっていますが、実装は未着手です。

**[Issue #6762「EC-CUBE 4.4 Roadmap」](https://github.com/EC-CUBE/ec-cube/issues/6762)（2026年5月15日オープン）**

4.4 リリースは2026年8月下旬を予定。AI 関連として計画されているのは「**リードオンリーの MCP サーバ機能**」のみです。カートへの追加・購入の完結は4.4のロードマップに含まれていません。

### 競合プラットフォームの対応状況

| プラットフォーム | MCP/UCP 対応状況 |
|---|---|
| **Shopify** | ✅ UCP 本格稼働（2026年4月）、カート・チェックアウト対応済み |
| **WooCommerce** | ✅ ネイティブ MCP サポート（2025年10月、v10.3） |
| **Adobe Commerce** | ✅ MCP サーバーを正式発表（2026年4月、Adobe Summit） |
| **EC-CUBE** | ❌ カート操作不可 / ❌ 購入完結不可 / 2026年8月に読み取り専用 MCP を計画中 |

公式対応を待つだけでは、少なくとも2026年8月まで「読み取り専用」止まりです。この間、AI 経由で流入するユーザーの購買先は UCP 対応済みのストアに流れ続けます。

---

## 対応ロードマップ

### Phase 1：EC-CUBE MCP サーバープラグインの開発（最優先）

UCP は MCP を正式トランスポートとして採用しています。Claude・ChatGPT・Gemini などの主要 AI エージェントはすでに MCP に対応しているため、**MCP サーバーの実装が最速の取っ掛かり**です。

まず実装すべきツールと、EC-CUBE `eccube-api4` GraphQL スキーマとの対応関係は以下の通りです。

| MCP ツール | EC-CUBE での実装方針 |
|---|---|
| `search_catalog` | `products` GraphQL クエリをラップ |
| `get_product` | `product(id)` GraphQL クエリをラップ |
| `get_order` | `order(id)` GraphQL クエリをラップ |
| `create_cart` / `get_cart` / `update_cart` | EC-CUBE の CartService を利用した新規実装 |
| `create_checkout` / `update_checkout` | EC-CUBE の PurchaseFlow を利用した新規実装 |

MCP サーバーは `streamable-http` トランスポートを使った PHP 実装が主流です。

:::message alert
**セキュリティ上の重要な注意事項**

以下のコードサンプルは MCP エンドポイントの基本構造を示すものであり、**認証・認可処理は省略しています**。本番環境で公開する場合は、必ず以下のいずれかの認証手段を実装してください。

- Bearer トークン検証（`Authorization: Bearer <token>` ヘッダーの確認）
- IP アドレスによるアクセス制限（社内エージェントのみの場合）
- UCP 仕様のエージェントプロファイル認証（Checkout API は必須）

**認証なしで公開した場合、誰でも MCP ツールを実行できる状態になります。** カート作成・チェックアウトを実装するフェーズ3では、未認証での注文操作が可能になるため特に危険です。
:::

```php
// src/Controller/McpController.php
use Symfony\Component\Routing\Attribute\Route;

#[Route('/mcp', name: 'eccube_mcp_endpoint', methods: ['POST'])]
public function handle(Request $request): JsonResponse
{
    // 本番実装では必ず認証トークンを検証すること
    // $token = $request->headers->get('Authorization');
    // if (!$this->isValidToken($token)) {
    //     return $this->jsonRpcError(-32600, 'Unauthorized', 401);
    // }

    $body = json_decode($request->getContent(), true);
    if (!is_array($body)) {
        return $this->jsonRpcError(-32700, 'Parse error');
    }

    $method = $body['method'] ?? '';
    $params = $body['params'] ?? [];

    return match ($method) {
        'tools/list'   => $this->toolsList(),
        'tools/call'   => $this->toolsCall($params),
        default        => $this->jsonRpcError(-32601, 'Method not found'),
    };
}
```

レスポンスは JSON-RPC 2.0 形式で返す必要があります（UCP の Checkout MCP は `result.structuredContent` に格納）。

既存の `eccube-api4` プラグインの GraphQL クライアントを内部で呼び出す構成にすれば、重複実装を避けられます。

### Phase 2：`/.well-known/ucp` エンドポイントの実装

MCP サーバーが動いたら、ディスカバリーエンドポイントを追加します。

```php
// src/Controller/UcpWellKnownController.php
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Routing\Generator\UrlGeneratorInterface;

#[Route('/.well-known/ucp', name: 'eccube_ucp_discovery', methods: ['GET'])]
public function profile(): JsonResponse
{
    return new JsonResponse([
        'ucp' => [
            'version' => '2026-04-08',
            'services' => [
                'dev.ucp.shopping' => [[
                    'transport' => 'mcp',
                    'endpoint'  => $this->generateUrl(
                        'eccube_mcp_endpoint',
                        [],
                        UrlGeneratorInterface::ABSOLUTE_URL
                    ),
                ]],
            ],
            'capabilities' => [
                'dev.ucp.shopping.catalog.search' => [['version' => '2026-04-08']],
                'dev.ucp.shopping.cart'           => [['version' => '2026-04-08']],
                'dev.ucp.shopping.order'          => [['version' => '2026-04-08']],
            ],
            'payment_handlers' => (object) [],
        ],
    ]);
}
```

この JSON を公開するだけで、UCP 対応エージェントが EC-CUBE ストアを自動発見できるようになります。

:::message
**`/.well-known/ucp` 公開時の注意点**

- このエンドポイントは認証不要で公開されますが、`endpoint` に記載した MCP エンドポイントの URL が外部に露出します。MCP 側に必ず認証を実装してください。
- 大量アクセス対策として、Nginx や Symfony の `Cache-Control` ヘッダーでキャッシュを設定することを推奨します（例: `max-age=3600`）。
- ステージング・開発環境での不用意な公開を避けるため、本番環境のみで有効化するよう `.env` や `services.yaml` で環境ごとに制御してください。
:::

### Phase 3：カート・チェックアウト API の整備

Phase 1 の `create_cart` / `create_checkout` 等は EC-CUBE の内部サービスを直接呼び出す新規実装が必要です。

EC-CUBE のカート処理は `Eccube\Service\CartService`、購入フローは `Eccube\Service\PurchaseFlow\PurchaseFlow` が中心です。これらを MCP ツールのハンドラから呼び出し、UCP のチェックアウト状態機械（`incomplete` → `ready_for_complete` → `completed`）にマッピングします。

配送先や支払い方法が未入力の場合は `incomplete` を返し、`continue_url` としてストアのチェックアウト画面 URL を渡します。これにより、API だけでは解決できないケースで人間のブラウザ操作にフォールバックできます。

:::message alert
**カート・チェックアウト API のセキュリティ要件**

UCP 仕様では Checkout API への**エージェントプロファイルの認証が必須**とされています。実装時は以下の点を必ず対処してください。

- **認証の必須化**: `create_checkout` / `update_checkout` / `complete_checkout` は Bearer トークンまたは UCP エージェントプロファイルで認証済みのリクエストのみ受け付けるようにする
- **CSRF 対策**: REST エンドポイントとして公開する場合は Symfony の CSRF トークン検証または `SameSite` Cookie ポリシーを設定する
- **カートの所有者検証**: `get_cart` / `update_cart` では、リクエスト元が当該カートの所有者であることを必ず検証する（他ユーザーのカートを操作されないようにする）
- **レートリミット**: `complete_checkout` は決済確定を伴うため、短時間の大量リクエストを防ぐレートリミットを設ける
:::


### Phase 4：UCP 仕様への正式準拠宣言（長期目標）

最終的には [github.com/universal-commerce-protocol/ucp](https://github.com/universal-commerce-protocol/ucp) の仕様に完全準拠し、`dev.ucp.shopping.checkout` を含む全 Capability を実装することを目標とします。Python SDK・Node.js SDK が公式提供されており、PHP SDK は現時点では存在しないため、Symfony Bundle として開発・OSS 公開することで EC-CUBE コミュニティへの貢献にもなります。

---

## まとめ

UCP は「AIエージェントがどの EC サイトでも同じプロトコルで商品を買える世界」を実現する仕様です。Shopify・Google・Etsy・Target・Walmart・Wayfair が参加し、2026年4月に本格稼働しました。

EC-CUBE 4.3 は商品・受注・顧客の読み取りと在庫更新は API 化されていますが、カート〜チェックアウトの API は未実装でギャップが大きい状況です。まず**MCP サーバープラグインを開発して Claude や ChatGPT から接続可能にする**ことが、最もコスト対効果の高い第一歩です。

| Phase | 内容 | 難易度 |
|---|---|---|
| 1 | MCP サーバープラグイン（search/cart/order ツール） | ★★☆ |
| 2 | `/.well-known/ucp` ディスカバリーエンドポイント | ★☆☆ |
| 3 | カート・チェックアウト API の整備 | ★★★ |
| 4 | UCP 仕様への正式準拠・PHP SDK の OSS 公開 | ★★★ |

AI エージェントがコマースの主要チャネルになりつつある今、EC-CUBE がこの波に乗り遅れないよう、段階的な対応を進めていきましょう。

---

**あなたはどう思いますか？**

EC-CUBE の UCP 対応について、コミュニティとして取り組むべき優先度や、MCPサーバープラグインとして欲しい機能があればぜひコメントで教えてください。実装の方向性の参考にします。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
