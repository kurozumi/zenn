## EC-CUBE コアはどうしているか

EC-CUBE コア（`src/Eccube/Controller/AbstractController.php`）は `#[IsCsrfTokenValid]` 属性を使わず、`isTokenValid()` メソッドを独自実装しています。

```php
// src/Eccube/Controller/AbstractController.php（実際のコード）
protected function isTokenValid()
{
    $request = $this->container->get('request_stack')->getCurrentRequest();
    $token = $request->get(Constant::TOKEN_NAME)
        ? $request->get(Constant::TOKEN_NAME)
        : $request->headers->get('ECCUBE-CSRF-TOKEN');

    if (!$this->isCsrfTokenValid(Constant::TOKEN_NAME, $token)) {
        throw new AccessDeniedHttpException('CSRF token is invalid.');
    }

    return true;
}
```

`AccessDeniedHttpException` は `HttpException`（403）を継承しており、`AuthenticationException` とは別系統です。**ログインリダイレクトは起きません**。EC-CUBE コアがこの問題を踏まないのはこのためです。

---

## 現在のEC-CUBEプラグインでの対応方法

### 方法1：EC-CUBEの `isTokenValid()` を使う（推奨）

EC-CUBE の `AbstractController` を継承している場合、`isTokenValid()` がそのまま使えます。

```php
use Eccube\Controller\AbstractController;

class AdminFooController extends AbstractController
{
    #[Route('/admin/foo/{id}/delete', methods: ['POST'])]
    public function delete(Request $request, Foo $foo): Response
    {
        $this->isTokenValid(); // 失敗時は AccessDeniedHttpException（403）

        $this->entityManager->remove($foo);
        $this->entityManager->flush();

        return $this->redirectToRoute('admin_foo_list');
    }
}
```

EC-CUBE の `isTokenValid()` は独自のトークン名（`Constant::TOKEN_NAME`）を使うため、Twig テンプレートには EC-CUBE 標準の CSRF フラグメントを使います。

```twig
<form method="post">
    {{ include('@EC-CUBE/default/fragment/csrf.html.twig') }}
    <button type="submit">削除</button>
</form>
```

### 方法2：手動で検証して AccessDeniedHttpException を投げる

独自トークン ID を使いたい場合は、`isCsrfTokenValid()` メソッドで検証して失敗時に `AccessDeniedHttpException` を投げます。

```php
use Symfony\Component\HttpKernel\Exception\AccessDeniedHttpException;

public function delete(Request $request, Foo $foo): Response
{
    if (!$this->isCsrfTokenValid('delete-foo', $request->request->get('_token'))) {
        throw new AccessDeniedHttpException('CSRF token is invalid.');
    }

    // ...
}
```

---

## Symfony 8.1 での修正：PR #57622

Symfony PR [#57622](https://github.com/symfony/symfony/pull/57622) では、新しい例外クラス `Symfony\Component\Security\Http\Exception\InvalidCsrfTokenException` が追加されます。

```php
// Symfony 8.1 以降（予定）：新しい InvalidCsrfTokenException
namespace Symfony\Component\Security\Http\Exception;

use Symfony\Component\HttpKernel\Exception\HttpException;

class InvalidCsrfTokenException extends HttpException
{
    public function __construct(string $message = 'Invalid CSRF token.', ?\Throwable $previous = null, int $code = 0, array $headers = [])
    {
        parent::__construct(403, $message, $previous, $headers, $code);
    }
}
```

`HttpException`（403）を継承するため、ログインリダイレクトは起きなくなります。`#[IsCsrfTokenValid]` 属性のリスナーも新しい例外クラスを使うよう変更されます。



---

## まとめ

| | 現在（Symfony 6.4） | PR #57622後（Symfony 8.1〜） |
|---|---|---|
| `#[IsCsrfTokenValid]` 失敗時の例外 | `Security\Core\Exception\InvalidCsrfTokenException` | `Security\Http\Exception\InvalidCsrfTokenException` |
| 例外の親クラス | `AuthenticationException` | `HttpException`（403） |
| ログインリダイレクト | 起きることがある | 起きない |
| EC-CUBE コアの実装 | `isTokenValid()` → `AccessDeniedHttpException` | 変わらず |

EC-CUBE プラグインで管理画面コントローラーを実装する場合は、`#[IsCsrfTokenValid]` 属性の代わりに EC-CUBE の `isTokenValid()` メソッドを使うか、手動で `AccessDeniedHttpException` を投げる実装にしておくのが安全です。

管理画面プラグインを作るとき「ログインページに飛ばされる」で詰まった経験があれば、ぜひコメントで教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---