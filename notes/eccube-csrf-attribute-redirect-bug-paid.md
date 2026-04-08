## EC-CUBE コアはどうしているか

EC-CUBE コア（`src/Eccube/Controller/AbstractController.php`）は `#[IsCsrfTokenValid]` 属性を使わず、`isTokenValid()` メソッドを独自実装しています。


`AccessDeniedHttpException` は `HttpException`（403）を継承しており、`AuthenticationException` とは別系統です。**ログインリダイレクトは起きません**。EC-CUBE コアがこの問題を踏まないのはこのためです。

---

## 現在のEC-CUBEプラグインでの対応方法

### 方法1：EC-CUBEの `isTokenValid()` を使う（推奨）

EC-CUBE の `AbstractController` を継承している場合、`isTokenValid()` がそのまま使えます。


EC-CUBE の `isTokenValid()` は独自のトークン名（`Constant::TOKEN_NAME`）を使うため、Twig テンプレートには EC-CUBE 標準の CSRF フラグメントを使います。


### 方法2：手動で検証して AccessDeniedHttpException を投げる

独自トークン ID を使いたい場合は、`isCsrfTokenValid()` メソッドで検証して失敗時に `AccessDeniedHttpException` を投げます。


---

## Symfony 8.1 での修正：PR #57622

Symfony PR [#57622](https://github.com/symfony/symfony/pull/57622) では、新しい例外クラス `Symfony\Component\Security\Http\Exception\InvalidCsrfTokenException` が追加されます。


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