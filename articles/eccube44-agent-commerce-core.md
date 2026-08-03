---
title: "EC-CUBE 4.4に2万4千行が入った。AIエージェント決済の中身を読む"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "ai"]
published: true
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.4 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## 結論: 4.4 の最大の変更は、AIエージェント向けの決済API群です

EC-CUBE 4.4 の変更を行数で並べると、上位を占めるのは Entity のリファクタでも DBAL 4 対応でもありません。**エージェントコマース**です。5本の PR で合計 **+24,788行**。

| PR | 内容 | 追加行数 |
| --- | --- | --- |
| [#6802](https://github.com/EC-CUBE/ec-cube/pull/6802) | 共通基盤 Phase 1a | +2,388 |
| [#6815](https://github.com/EC-CUBE/ec-cube/pull/6815) | Product Feed / Catalog / Discovery | +7,575 |
| [#6825](https://github.com/EC-CUBE/ec-cube/pull/6825) | CheckoutSession 中核 | +4,726 |
| [#6837](https://github.com/EC-CUBE/ec-cube/pull/6837) | **UCP checkout** コア実装 | +7,561 |
| [#6843](https://github.com/EC-CUBE/ec-cube/pull/6843) | **ACP checkout** コア実装 | +2,538 |

`src/Eccube/Service/AgentCommerce/` 配下だけで **77ファイル**。EC-CUBE 本体に、これだけの規模の新機能がまとめて入るのは珍しいことです。

「AI がECサイトで買い物する」という話は概念としてよく語られますが、4.4 には**実際に動くエンドポイントが実装されています**。この記事では、実装から何が用意されたのかを読み解きます。

**TL;DR**

- ACP と UCP という2つのプロトコルに対応。両方が並行して実装されている
- ディスカバリ（`/.well-known/ucp`、`/.well-known/acp.json`）で機能を公開する
- チェックアウトはセッション方式。作成・更新・取得・完了・キャンセルの5操作
- カタログは検索・ルックアップ・商品取得の3エンドポイント（UCP）と、フィード push（ACP）
- 決済は**タグ付きサービスとして決済プラグインが提供**する。コアは具象ハンドラを持たない
- 冪等性は DB の一意制約（`dtb_agent_checkout_idempotency`）で担保
- 署名検証は RFC 9421。既定では必須化されていない

## ACP と UCP という2つのプロトコル

まず用語です。両方ともAIエージェントが店舗と取引するためのプロトコルですが、出自と方式が違います。

**ACP（Agentic Commerce Protocol）** は、商品フィードを店舗側からプラットフォームへ **push** する方式を含みます。実装にも `AcpFeedClient` があり、外部の API に商品データを送る作りになっています。

**UCP** は、エージェントが店舗のエンドポイントに **pull** で問い合わせる方式です。カタログ検索の REST エンドポイントが用意されています。

EC-CUBE 4.4 は**どちらか一方を選ばず、両方を実装しました**。プロトコルの覇権がまだ決まっていない段階で、片方に賭けない判断です。共通化できる部分（CheckoutSession の中核、決済ハンドラのレジストリ、在庫確保のロジック）は `AgentCommerce` 配下で共有し、プロトコル固有の部分だけ `Acp/` `Ucp/` に分けています。

## 実装されたエンドポイント

実際のルート定義から拾うと、こうなっています。

### ディスカバリ

```
GET /.well-known/ucp          … UCP discovery profile
GET /.well-known/acp.json     … ACP discovery 文書
```

エージェントは最初にここを読んで、その店舗が何をサポートしているかを知ります。`UcpDiscoveryController` のコメントに、設計上の制約が書かれています。

> well-known はオリジンルート固定・1 オリジン 1 枚 (RFC 8615)

`/.well-known/` は [RFC 8615](https://datatracker.ietf.org/doc/html/rfc8615) で定義された標準的な置き場所です。サブディレクトリに EC-CUBE を設置している構成では、ここが取れるか確認が要ります。

### カタログ（UCP）

```
POST /catalog/search     … 検索
POST /catalog/lookup     … ルックアップ
POST /catalog/product    … 商品取得
```

すべて POST です。GET でなく POST なのは、検索条件が複雑になりうるためだと思われます。

### チェックアウト

UCP 側はリソース指向の REST です。

```
POST   /ucp/checkout-sessions
GET    /ucp/checkout-sessions/{sessionId}
PUT    /ucp/checkout-sessions/{sessionId}
POST   /ucp/checkout-sessions/{sessionId}/complete
POST   /ucp/checkout-sessions/{sessionId}/cancel
```

ACP 側は同じ操作を別のパス規約で持ちます。

```
POST /acp/checkout_sessions
GET  /acp/checkout_sessions/{sessionId}
POST /acp/checkout_sessions/{sessionId}
POST /acp/checkout_sessions/{sessionId}/complete
POST /acp/checkout_sessions/{sessionId}/cancel
```

**更新が UCP は `PUT`、ACP は `POST`** という違いがあります。パスの区切りもハイフンとアンダースコアで分かれています。プロトコル仕様に忠実に実装した結果で、EC-CUBE が勝手に統一していないところに実装方針が出ています。

## 決済はプラグインが担う

実装で最も重要な設計判断が、決済の扱いです。`services.yaml` を見ると分かります。

```yaml
    # Agent Commerce 決済ハンドラ (#6574 UCP / #6776 ACP)
    # 具象ハンドラは決済プラグインが agent_commerce.payment_handler タグで寄与する。
    _instanceof:
        Eccube\Service\AgentCommerce\Payment\AgentCheckoutPaymentHandlerInterface:
            tags: ['agent_commerce.payment_handler']

    # 決済ハンドラレジストリ。具象ハンドラ (決済プラグイン) は agent_commerce.payment_handler タグで寄与する。
    Eccube\Service\AgentCommerce\Payment\AgentCheckoutPaymentHandlerRegistry:
        arguments:
            $handlers: !tagged_iterator agent_commerce.payment_handler
```

**コアは具象の決済ハンドラを1つも持ちません。** `AgentCheckoutPaymentHandlerInterface` を実装したクラスが自動的にタグ付けされ、レジストリに集約される仕組みだけを提供します。

つまり **4.4 を入れただけではエージェント経由の決済は成立しません**。対応した決済プラグインが必要です。

支払方法の解決も差し替え可能になっています。

```yaml
    # エージェント注文の支払方法解決 (handler_id 駆動・sort_no 非依存)。
    # 店舗ごとに選択ロジックを変える場合は app/Customize で実装しエイリアスを差し替える。
    Eccube\Service\AgentCommerce\Payment\AgentPaymentMethodResolverInterface:
        alias: Eccube\Service\AgentCommerce\Payment\DefaultAgentPaymentMethodResolver
```

コメントの「`sort_no` 非依存」が実務的です。通常の購入フローでは支払方法の並び順が初期選択に影響しますが、エージェント経由では `handler_id` で明示的に決まります。人間が画面で選ぶわけではないので、並び順に依存しない設計が正しい。

## 会員の扱いは「ゲスト購入」から

もう1つ、現時点の割り切りが見えるのがここです。

```yaml
    # 標準はゲスト購入 (会員解決なし)。会員 ID 連携は eccube-api4#189 landing 後に差し替える。
    Eccube\Service\AgentCommerce\CheckoutSession\CustomerResolverInterface:
        alias: Eccube\Service\AgentCommerce\CheckoutSession\GuestCustomerResolver
```

エージェント経由の注文は、標準ではゲスト購入として処理されます。会員 ID との紐付けは API プラグイン側の対応待ちです。

インターフェースとエイリアスで切ってあるので、`app/Customize` で独自の `CustomerResolverInterface` 実装に差し替えれば、いまでも会員紐付けは可能です。

## 冪等性とセキュリティ

### 冪等性は DB の一意制約で

`services.yaml` に短いコメントがあります。

```yaml
    # 冪等性記録は DB 一意制約 (dtb_agent_checkout_idempotency) で管理する (EM/Repository は autowire)。
```

エージェントは自動でリトライします。ネットワークが切れれば同じリクエストがもう一度飛んできます。決済を二重に実行しないため、冪等性キーを DB の一意制約で管理する方式です。

**アプリケーション層のチェックではなく DB 制約でやる**のが堅い選択です。同時に2つのリクエストが来たとき、`SELECT` してから `INSERT` する実装では競合します。一意制約なら片方が必ず失敗します。

### 署名検証は既定オフ

```yaml
    # UCP インバウンド署名検証 (RFC 9421・api4 非依存)。許可ドメイン/必須化は運用で設定する。
    Eccube\Service\AgentCommerce\Ucp\Signature\UcpRequestSignatureVerifier:
        arguments:
            $allowedDomains: []

    Eccube\Service\AgentCommerce\Ucp\Signature\UcpSignatureSubscriber:
        arguments:
            $requireSignature: false
```

[RFC 9421](https://datatracker.ietf.org/doc/html/rfc9421)（HTTP Message Signatures）による署名検証が実装されていますが、**既定では必須化されていません**（`$requireSignature: false`、`$allowedDomains: []`）。

本番でエージェントコマースを有効にするなら、ここは運用で設定する必要があります。既定のまま公開すると、署名なしのリクエストを受け付けることになります。

### 認証は OAuth2

```yaml
    # OAuth2 トークン検証。リソースサーバー (eccube-api4#188) 未導入時は handler が null となり 503 を返す。
    Eccube\Service\AgentCommerce\Security\AgentCommerceOAuth2Authenticator:
        arguments:
            $accessTokenHandler: '@?Symfony\Component\Security\Http\AccessToken\AccessTokenHandlerInterface'
```

`@?` は「あればインジェクト、なければ null」という指定です。API プラグインが入っていなければハンドラが null になり、**503 を返します**。誤って認証なしで通ることがない作りです。

## 環境変数

`services.yaml` に既定値が入りました。

```yaml
    # Agent Commerce (#6794): 未設定時は空文字を既定とする (string 型注入で null TypeError を避ける)
    env(ECCUBE_AGENT_COMMERCE_UCP_SIGNING_KEY): ''
    env(ECCUBE_AGENT_COMMERCE_ACP_FEED_BASE_URL): ''
    env(ECCUBE_AGENT_COMMERCE_ACP_FEED_API_KEY): ''
```

未設定でも起動できるよう空文字が既定になっています。**エージェントコマースを使わない店舗でも 4.4 は普通に動く**ということです。

署名鍵は `FilesystemKeyStore` で管理され、環境変数でパスを上書きできます。

## いま何をすべきか

エージェントコマースは、すぐに全店舗が対応するものではありません。ただし、上げる前に決めておくことはあります。

**エンドポイントが増えます。** `/.well-known/ucp`、`/.well-known/acp.json`、`/catalog/*`、`/ucp/checkout-sessions/*`、`/acp/checkout_sessions/*` が追加されます。WAF やリバースプロキシでパスベースの制御をしている場合、意図せず塞ぐ、あるいは意図せず開ける可能性があります。**4.4 に上げる前に、これらのパスをどう扱うか決めておいてください。**

**使わないなら閉じる判断も要ります。** 認証は OAuth2 で守られており、API プラグイン未導入なら 503 になります。とはいえディスカバリ文書は情報を出すので、使わないなら塞いでおくのが素直です。

**決済プラグイン開発者には仕事が増えます。** `AgentCheckoutPaymentHandlerInterface` を実装すればタグ付けは自動です。エージェント経由の決済に対応する決済プラグインは、今後の差別化要素になる可能性があります。

## まとめ

- EC-CUBE 4.4 に ACP / UCP 両対応のエージェントコマース基盤が入った（5PR・合計 +24,788行・77ファイル）
- ディスカバリ、カタログ、チェックアウトセッションのエンドポイントが実装済み
- UCP は `PUT` でリソース更新、ACP は `POST`。プロトコル仕様に忠実で、EC-CUBE 側で統一していない
- **決済ハンドラはコアに存在しない**。決済プラグインがタグ付きサービスで提供する
- 標準はゲスト購入。会員紐付けは `CustomerResolverInterface` の差し替えで対応可能
- 冪等性は DB の一意制約、認証は OAuth2、署名は RFC 9421。**署名の必須化は既定オフなので運用で設定が要る**
- 使わない店舗でも起動には影響しない。ただし公開されるパスの扱いは決めておくこと

「AIがECで買い物する」という話は数年前から語られてきました。4.4 で、それが仕様書ではなく `#[Route]` 付きのコントローラとして手元に来ます。動かせる状態で読めるのは、理解するうえで大きな違いです。

:::message alert
EC-CUBE 4.4 はこの記事を書いている時点（2026年8月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。エージェントコマース関連は特に、プロトコル仕様自体が策定途上のため変更が入りやすい領域です。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
