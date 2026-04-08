# EC-CUBEプラグインのCSRF検証でログインページに飛ばされる罠と回避策【Symfony #[IsCsrfTokenValid]】

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

管理画面のフォームを自作したとき、CSRFトークンが不正なのになぜかログインページにリダイレクトされた——そんな経験はありませんか？

これは Symfony の `#[IsCsrfTokenValid]` 属性の設計上の問題です。**EC-CUBE コアはこれを回避する独自実装を持っています**が、プラグインで管理画面コントローラーを実装する際に踏み抜きやすい罠です。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - `#[IsCsrfTokenValid]` が失敗すると `AuthenticationException` が投げられ、ログインページにリダイレクトされることがある
ℹ️ - EC-CUBE コアは `isTokenValid()` メソッドで `AccessDeniedHttpException`（403）を投げるため影響なし
ℹ️ - Symfony PR #57622（8.1向け）で専用の `InvalidCsrfTokenException`（HTTP 403）に変わり、ログインリダイレクトが起きなくなる
ℹ️ - 現状の回避策：`#[IsCsrfTokenValid]` 属性の代わりに EC-CUBE の `isTokenValid()` を使う