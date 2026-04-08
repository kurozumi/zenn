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

## `#[IsCsrfTokenValid]` 属性とは

Symfony 6.4 で追加された、コントローラーメソッドへの属性です。フォーム送信の CSRF 検証を簡潔に書けます。

```php
use Symfony\Component\Security\Http\Attribute\IsCsrfTokenValid;

class AdminFooController extends AbstractController
{
    #[Route('/admin/foo/{id}/delete', methods: ['POST'])]
    #[IsCsrfTokenValid('delete-foo')]
    public function delete(Foo $foo): Response
    {
        // CSRFトークンが有効な場合のみここに到達する
        $this->entityManager->remove($foo);
        $this->entityManager->flush();

        return $this->redirectToRoute('admin_foo_list');
    }
}
```

フォーム側では hidden フィールドでトークンを送ります。

```twig
<form method="post" action="{{ path('admin_foo_delete', {id: foo.id}) }}">
    <input type="hidden" name="_token" value="{{ csrf_token('delete-foo') }}">
    <button type="submit">削除</button>
</form>
```

一見シンプルですが、**CSRF トークンが不正なときに予期しない動作をします**。

---

## 問題：CSRF検証失敗でログインページにリダイレクトされる

`#[IsCsrfTokenValid]` が失敗したとき、内部で `Symfony\Component\Security\Core\Exception\InvalidCsrfTokenException` が投げられます。

```php
// Symfony 6.4 の IsCsrfTokenValidAttributeListener.php（実際のコード）
use Symfony\Component\Security\Core\Exception\InvalidCsrfTokenException;

if (!$csrfTokenManager->isTokenValid($csrfToken)) {
    throw new InvalidCsrfTokenException();
}
```

この例外は `AuthenticationException` を継承しています。

```
InvalidCsrfTokenException（Security\Core）
  ↳ AuthenticationException
      ↳ RuntimeException
```

Symfony の Security コンポーネントは `AuthenticationException` をキャッチすると**認証が必要と判断してログインページへリダイレクト**します。その結果：

- 管理画面にログイン済みのユーザーが
- CSRF トークンが不正なフォームを送信すると
- 403 エラーではなく **ログインページへのリダイレクト（301/302）** が返る

管理画面プラグインを開発するとき、この挙動は直感に反します。

---