# EC-CUBEプラグインでisValid()が常にtrueを返す罠——POST_SUBMITの落とし穴

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBEプラグインで `ShippingType` を拡張し、`POST_SUBMIT` の中で `isValid()` を呼んだとき——**バリデーションエラーがあるのに `true` が返ってくる**経験をしたことはないでしょうか。

コードは正しいはずなのに、なぜか通ってしまう。`dump()` で確認するとフォームは「valid」と言っている。

**原因は一言で言えます: `POST_SUBMIT` が発火した時点では、バリデーションがまだ実行されていない。**

子フォーム（`ShippingType`）の `POST_SUBMIT` は、親フォーム（`OrderType`）のバリデーションが走る前に呼ばれます。だから `isValid()` は正確な結果を返せません。

2022年から議論されてきた Symfony PR [#47210](https://github.com/symfony/symfony/pull/47210) では、この問題を根本的に解決する `POST_VALIDATE` イベントが追加される予定です。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - EC-CUBE の注文・カートバリデーションは FormEvents ではなく **PurchaseFlow**（独自サービス層）で実装されている
ℹ️ - プラグインから `AbstractTypeExtension` でフォームを拡張し `POST_SUBMIT` で `isValid()` を呼ぶと、ネストしたフォームでは正確な結果が返らない
ℹ️ - Symfony PR #47210（8.1向け）で `ValidatorFormEvents::POST_VALIDATE` が追加され、バリデーション完了後に正確な `isValid()` が使えるようになる
ℹ️ - 現状の回避策：`POST_SUBMIT` の優先度を低くするか、PurchaseFlow の仕組みを使う

## EC-CUBE の注文バリデーションは PurchaseFlow が担当する

まず前提として、EC-CUBE 4.3 の注文・カートのビジネスロジック検証（在庫チェック・価格変更検知・配送設定確認など）は、Symfony の FormEvents **ではなく** `PurchaseFlow`（`src/Eccube/Service/PurchaseFlow/`）という独立したサービス層で実装されています。


`OrderType.php` の `POST_SUBMIT` は支払い方法エンティティのセット、`ShippingType.php` の `POST_SUBMIT` は配送日時のエンティティへの転送が目的であり、**バリデーションは行っていません**。

この設計の理由は、FormEvents はリクエスト処理に依存するため、CLIやバッチ処理・APIから注文処理を呼び出すケースに対応しにくいからです。PurchaseFlow はフォームに依存しないため、どこからでも呼び出せます。

---

## ではいつ FormType のバリデーションイベントが必要になるか

PurchaseFlow が本体のバリデーションを担当するとしても、プラグイン開発では FormType レベルでのバリデーションが必要になるケースがあります。

**プラグインからフォームフィールドを追加する場合:**


---