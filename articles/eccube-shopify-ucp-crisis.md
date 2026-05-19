---
title: "ShopifyのAI注文が11倍になった今、EC-CUBEは「読み取り専用」のまま"
emoji: "🚨"
type: "tech"
topics: ["eccube", "eccube4", "php", "mcp"]
published: false
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

今日、あなたの EC-CUBE ストアには何件の AI 経由の注文が入りましたか。

おそらくゼロです。それはあなたの運営が悪いのではなく、**EC-CUBE が AI に注文させる機能を持っていないから**です。

2025年1月以降、Shopify における AI 起因の注文数は **11倍**になりました。AI 由来のトラフィックは **7倍**増。Shopify 社長 Harley Finkelstein が Q3 2025 決算発表で公表し、[TechCrunch が報じた](https://techcrunch.com/2025/11/04/shopify-says-ai-traffic-is-up-7x-since-january-ai-driven-orders-are-up-11x/)データです。

そして2026年4月、Shopify は Universal Commerce Protocol（UCP）を全加盟店向けに本格稼働させました。Claude・ChatGPT・Gemini などの AI エージェントが、数十億の商品を検索し、カートを作成し、チェックアウトまで完結できる環境が整いました。

**一方、EC-CUBE の最速対応は2026年8月下旬。しかも「読み取り専用」のみです。**

---

## Shopify で何が起きているか

Shopify CEO の Tobi Lutke は2026年4月、X（旧 Twitter）にこう投稿しました。

> "New version of Universal Commerce Protocol (UCP 2026-04-08) just got finalized. Carts (!), Catalog discovery features, Order status, Signals support... Big step function upgrade for agentic commerce. Coming soon to every Shopify storefront."

「Carts (!)」という感嘆符付きの表現が示すように、AI エージェントがカートを操作できるようになったことは、Shopify 陣営にとってマイルストーンでした。

現在 Shopify では、AI エージェントが以下の操作を UCP / MCP 経由でそのまま実行できます。

| 操作 | Shopify（UCP 稼働済み） |
|---|---|
| 数十億商品の横断検索 | ✅ `search_catalog` |
| 商品詳細・在庫の取得 | ✅ `get_product` |
| カートの作成・更新 | ✅ `create_cart` / `update_cart` |
| チェックアウト開始・完結 | ✅ `create_checkout` / `complete_checkout` |
| 注文状況の確認 | ✅ `get_order` |

「AI に話しかけたら商品を買ってくれた」という体験が、数百万の Shopify 加盟店でデフォルトになっています。

---

## EC-CUBE の現実

EC-CUBE 4.3 には公式の Web API プラグイン（eccube-api4 v4.3.2）が存在します。GraphQL で商品・受注・顧客情報を取得でき、在庫更新・出荷ステータス更新の Mutation も実装されています。

しかし**カートに商品を追加する API は存在しません。チェックアウトを開始する API も存在しません。** AI エージェントが EC-CUBE ストアで購入を完結させる手段は、現時点で一切ありません。

### EC-CUBE GitHub の Issue が物語る現状

GitHub には以下の Issue が存在します。

**Issue #6347「MCPサーバーの実装」（2025年4月6日オープン）**
> EC-CUBE用のMCPサーバーがあると、AIとの開発が進む。商品やマスタデータの読取ができると良い。

オープンから1年以上。アサインなし、実装なし。

**Issue #6574「ユニバーサルコマースプロトコル（UCP）の対応」（2026年1月15日オープン）**

チェックアウトセッション API の設計案が議論されています。

> `POST /checkout-sessions`
> `PUT /checkout-sessions/{id}`
> `POST /checkout-sessions/{id}/complete`

設計の議論は始まっています。しかし実装着手の証拠はありません。

**Issue #6762「EC-CUBE 4.4 Roadmap」（2026年5月15日オープン）**

4.4 リリースは2026年8月下旬を予定。AI 関連機能として計画されているのは：

- ACP/UCP 対応のサイト・商品フィード機能
- **リードオンリーの MCP サーバ機能**

「リードオンリー」です。カートへの追加も、購入の完結も、4.4 のロードマップに含まれていません。

---

## 競合はどこにいるか

| プラットフォーム | MCP/UCP 対応状況 |
|---|---|
| **Shopify** | ✅ UCP 本格稼働済み（2026年4月）、カート・チェックアウト対応 |
| **WooCommerce** | ✅ ネイティブ MCP サポート（2025年10月、v10.3） |
| **Adobe Commerce** | ✅ MCP サーバーを正式発表（2026年4月、Adobe Summit） |
| **EC-CUBE** | ❌ カート操作不可 / ❌ 購入完結不可 / 2026年8月に「検討中」 |

WooCommerce はすでに2025年10月、バージョン 10.3 でネイティブの MCP サポートを追加しています。Adobe Commerce（旧 Magento）は2026年4月の Adobe Summit で MCP サーバーを正式発表しました。

EC-CUBE は最速で2026年8月、それも「読み取り専用」止まりです。

---

## 見逃しているものの大きさ

AI エージェント経由の購買者は、従来型トラフィックと比べてコンバージョン率が大幅に高いというデータが複数の市場調査から報告されています。Shopify の AI 注文が1年で11倍になったのは偶然ではありません。

**AI エージェントが購入を完結できる環境を整えたから、AI エージェントが顧客を連れてくる**のです。

EC-CUBE 運営者にとって、これは「将来の話」ではありません。今この瞬間、ChatGPT や Claude を使ってショッピングをしているユーザーの購買先は、UCP 対応済みの Shopify ストアに流れています。

---

## 「公式対応を待つ」という選択の意味

「公式対応を待つ」という選択は、**2026年8月まで競合に AI 経由の顧客を渡し続けることと同義**です。

しかも2026年8月時点の EC-CUBE 4.4 で実装されるのは「読み取り専用」。カートに入れて買ってもらえるようになるのは、さらにその先の話です。

UCP の仕様は Apache License 2.0 でオープンに公開されています。`/.well-known/ucp` エンドポイントを公開し、MCP サーバーとして商品検索・カート・チェックアウトツールを実装すること自体は、技術的に難しくありません。具体的な実装方針は以下の記事で解説しています。

→ [あなたのEC-CUBEストア、ChatGPTから買えますか？UCP対応の始め方](https://zenn.dev/kurozumi/articles/eccube-ucp-mcp-agent-commerce)

EC-CUBE コミュニティには、この問題を認識して動こうとしているメンバーがいます（Issue #6347、#6574）。公式が動く前に、プラグインとして先行実装して公開する開発者が出てくることを期待しています。

待つか、先行実装するか。選択肢は「今すぐ使えるかどうか」だけです。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
