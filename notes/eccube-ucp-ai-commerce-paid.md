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


### 1. セッション作成 (`POST /checkout-sessions`)

AIエージェントが「この商品を買いたい」とリクエストすると、EC-CUBE がチェックアウトセッションを作成します。


### 2. セッション更新 (`PUT /checkout-sessions/{id}`)

配送先住所が更新されたら、送料や税金を再計算します。


### 3. セッション完了 (`POST /checkout-sessions/{id}/complete`)

ユーザーが「注文する」と言ったら、注文を確定します。


### 必要な新規エンティティ


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