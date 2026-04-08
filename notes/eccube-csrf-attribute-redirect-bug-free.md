# EC-CUBEプラグインのCSRF検証でログインページに飛ばされる罠と回避策【Symfony #[IsCsrfTokenValid]】

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

管理画面のフォームを自作したとき、CSRFトークンが不正なのになぜかログインページにリダイレクトされた——そんな経験はありませんか？

これは Symfony の `#[IsCsrfTokenValid]` 属性の設計上の問題です。**EC-CUBE コアはこれを回避する独自実装を持っています**が、プラグインで管理画面コントローラーを実装する際に踏み抜きやすい罠です。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - `#[IsCsrfTokenValid]` が失敗すると `AuthenticationException` が投げられ、ログインページにリダイレクトされることがある
ℹ️ - EC-CUBE コアは `isTokenValid()` メソッドで `AccessDeniedHttpException`（403）を投げるため影響なし
ℹ️ - Symfony PR #57622（8.1向け）で専用の `InvalidCsrfTokenException`（HTTP 403）に変わり、ログインリダイレクトが起きなくなる
ℹ️ - 現状の回避策：`#[IsCsrfTokenValid]` 属性の代わりに EC-CUBE の `isTokenValid()` を使う

## `#[IsCsrfTokenValid]` 属性とは

Symfony 6.4 で追加された、コントローラーメソッドへの属性です。フォーム送信の CSRF 検証を簡潔に書けます。


フォーム側では hidden フィールドでトークンを送ります。


一見シンプルですが、**CSRF トークンが不正なときに予期しない動作をします**。

---

## 問題：CSRF検証失敗でログインページにリダイレクトされる

`#[IsCsrfTokenValid]` が失敗したとき、内部で `Symfony\Component\Security\Core\Exception\InvalidCsrfTokenException` が投げられます。


この例外は `AuthenticationException` を継承しています。


Symfony の Security コンポーネントは `AuthenticationException` をキャッチすると**認証が必要と判断してログインページへリダイレクト**します。その結果：

- 管理画面にログイン済みのユーザーが
- CSRF トークンが不正なフォームを送信すると
- 403 エラーではなく **ログインページへのリダイレクト（301/302）** が返る

管理画面プラグインを開発するとき、この挙動は直感に反します。

---