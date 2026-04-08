## 基本的な使い方

### シンプルな例

```php
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Attribute\MapRequestHeader;
use Symfony\Component\Routing\Attribute\Route;

class ApiController extends AbstractController
{
    #[Route('/api/data')]
    public function getData(
        #[MapRequestHeader] string $accept,
        #[MapRequestHeader] ?string $authorization,
    ): Response {
        // $accept には Accept ヘッダーの値が入る
        // $authorization は Authorization ヘッダー（なければnull）
    }
}
```

### 名前の自動変換

引数名がcamelCaseの場合、自動的にkebab-caseに変換されます。

```php
public function index(
    #[MapRequestHeader] string $acceptLanguage,  // → Accept-Language
    #[MapRequestHeader] string $contentType,     // → Content-Type
    #[MapRequestHeader] string $xCustomHeader,   // → X-Custom-Header
): Response {
    // ...
}
```

これは地味に便利です。PHPの変数名規則とHTTPヘッダーの命名規則を自動的に橋渡ししてくれます。

### 明示的なヘッダー名指定

自動変換に頼りたくない場合は、明示的に指定できます。

```php
public function index(
    #[MapRequestHeader('User-Agent')] string $userAgent,
    #[MapRequestHeader('X-API-KEY')] string $apiKey,
): Response {
    // ...
}
```

## 配列としての取得

同じヘッダーが複数回送信される場合、配列で受け取れます。

```php
public function index(
    #[MapRequestHeader] array $acceptLanguage,
): Response {
    // $acceptLanguage = ['ja', 'en-US', 'en']
}
```

これは`Accept-Language: ja, en-US, en`のようなヘッダーを解析するときに便利です。

## AcceptHeaderクラスでの受け取り

Accept系ヘッダーには専用のクラスがあります。

```php
use Symfony\Component\HttpFoundation\AcceptHeader;

public function index(
    #[MapRequestHeader] AcceptHeader $accept,
    #[MapRequestHeader] AcceptHeader $acceptEncoding,
): Response {
    // $accept->has('application/json') で判定
    // $accept->all() で全エントリ取得
}
```

`AcceptHeader`クラスは品質値（q値）の解析もしてくれるので、コンテンツネゴシエーションが簡単に実装できます。

## エラーハンドリング

必須ヘッダーが見つからない場合、自動的に400エラーが返されます。

```php
public function index(
    #[MapRequestHeader] string $authorization,  // 必須
): Response {
    // Authorization ヘッダーがなければ400
}
```


### ステータスコードのカスタマイズ

401を返したい場合など、ステータスコードを変更できます。

```php
public function index(
    #[MapRequestHeader(validationFailedStatusCode: 401)] string $authorization,
): Response {
    // Authorization ヘッダーがなければ401
}
```

## EC-CUBEでの実用例

### 例1: API認証ヘッダーの処理

```php
namespace Customize\Controller\Api;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpKernel\Attribute\MapRequestHeader;
use Symfony\Component\Routing\Attribute\Route;

class ProductApiController extends AbstractController
{
    #[Route('/api/v1/products', methods: ['GET'])]
    public function list(
        #[MapRequestHeader('X-API-KEY', validationFailedStatusCode: 401)] string $apiKey,
        #[MapRequestHeader] ?string $acceptLanguage,
    ): JsonResponse {
        // APIキーの検証（タイミング攻撃対策としてhash_equalsを使用）
        if (!$this->apiKeyService->isValid($apiKey)) {
            return $this->json(['error' => 'Unauthorized'], 401);
        }

        // 言語に応じた商品データを返す
        $locale = $this->parseLocale($acceptLanguage);

        return $this->json([
            'products' => $this->productRepository->findAllLocalized($locale),
        ]);
    }
}
```

### 例2: モバイルアプリ判定

```php
namespace Customize\Controller;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Attribute\MapRequestHeader;
use Symfony\Component\Routing\Attribute\Route;

class ProductController extends AbstractController
{
    #[Route('/products/{id}')]
    public function detail(
        int $id,
        #[MapRequestHeader('User-Agent')] string $userAgent,
        #[MapRequestHeader('X-App-Version')] ?string $appVersion,
    ): Response {
        $product = $this->productRepository->find($id);

        // モバイルアプリからのアクセスか判定
        $isMobileApp = $appVersion !== null;

        // User-Agentでモバイルブラウザ判定
        $isMobileBrowser = str_contains($userAgent, 'Mobile');

        return $this->render('Product/detail.twig', [
            'Product' => $product,
            'isMobileApp' => $isMobileApp,
            'isMobileBrowser' => $isMobileBrowser,
        ]);
    }
}
```

### 例3: キャッシュ制御

```php
namespace Customize\Controller;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Attribute\MapRequestHeader;
use Symfony\Component\Routing\Attribute\Route;

class CatalogController extends AbstractController
{
    #[Route('/catalog')]
    public function index(
        #[MapRequestHeader('If-None-Match')] ?string $ifNoneMatch,
        #[MapRequestHeader('If-Modified-Since')] ?string $ifModifiedSince,
    ): Response {
        $lastModified = $this->catalogService->getLastModified();
        $etag = $this->catalogService->getEtag();

        // クライアントキャッシュが有効か判定（hash_equalsでタイミング攻撃対策）
        if ($ifNoneMatch !== null && hash_equals($etag, $ifNoneMatch)) {
            return new Response('', 304);
        }

        if ($ifModifiedSince !== null) {
            try {
                if (new \DateTime($ifModifiedSince) >= $lastModified) {
                    return new Response('', 304);
                }
            } catch (\Exception) {
                // 無効な日付形式は無視してコンテンツを返す
            }
        }

        $response = $this->render('Catalog/index.twig', [
            'products' => $this->catalogService->getProducts(),
        ]);

        $response->setEtag($etag);
        $response->setLastModified($lastModified);

        return $response;
    }
}
```

### 例4: コンテンツネゴシエーション

```php
namespace Customize\Controller\Api;

use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\AcceptHeader;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\HttpKernel\Attribute\MapRequestHeader;
use Symfony\Component\Routing\Attribute\Route;

class ExportController extends AbstractController
{
    #[Route('/api/v1/products/export')]
    public function export(
        #[MapRequestHeader] AcceptHeader $accept,
    ): Response {
        $products = $this->productRepository->findAll();

        // Accept ヘッダーに基づいてフォーマットを決定
        if ($accept->has('text/csv')) {
            return $this->exportCsv($products);
        }

        if ($accept->has('application/xml')) {
            return $this->exportXml($products);
        }

        // デフォルトはJSON
        return $this->json(['products' => $products]);
    }
}
```

ℹ️ **注意**: `#[MapRequestHeader]` は型の安全性を提供しますが、ヘッダーの内容の検証は行いません。APIキーや認証トークンなど、セキュリティに関わるヘッダーは必ず追加の検証を行ってください。

## 従来の方法との比較

### コード量: 75%削減

従来6行必要だった処理が、属性を使えば**引数宣言だけ**で完結します。

### Before（従来）

```php
public function index(Request $request): Response
{
    $accept = $request->headers->get('Accept');
    $authorization = $request->headers->get('Authorization');
    $userAgent = $request->headers->get('User-Agent');
    $acceptLanguage = $request->headers->get('Accept-Language');

    if ($authorization === null) {
        throw new HttpException(401, 'Authorization required');
    }

    // 処理...
}
```

### After（Symfony 8.1）

```php
public function index(
    #[MapRequestHeader] string $accept,
    #[MapRequestHeader(validationFailedStatusCode: 401)] string $authorization,
    #[MapRequestHeader('User-Agent')] string $userAgent,
    #[MapRequestHeader] ?string $acceptLanguage,
): Response {
    // 処理...
}
```

### 比較表

| 観点 | 従来 | #[MapRequestHeader] |
|------|------|---------------------|
| コード量 | 多い | 少ない |
| 型安全性 | 手動で担保 | 自動 |
| null処理 | 手動 | 型で表現 |
| エラーハンドリング | 手動 | 自動 |
| IDE補完 | なし | あり |
| テスタビリティ | Request必須 | 引数で注入 |

## 関連する属性たち

Symfony 8.1では、リクエストデータをコントローラー引数にマップする属性が充実しています。

| 属性 | 用途 |
|-----|------|
| `#[MapQueryParameter]` | クエリパラメータ |
| `#[MapRequestPayload]` | リクエストボディ（JSON等） |
| `#[MapQueryString]` | クエリ文字列全体をDTO化 |
| `#[MapRequestHeader]` | HTTPヘッダー ← **NEW!** |

これらを組み合わせると、コントローラーの引数だけでリクエストの全データにアクセスできます。

```php
public function create(
    #[MapRequestPayload] ProductDto $product,
    #[MapQueryParameter] int $categoryId,
    #[MapRequestHeader('X-API-KEY')] string $apiKey,
): Response {
    // $request を一切触らずに全データにアクセス
}
```

## まとめ

Symfony 8.1の`#[MapRequestHeader]`は、HTTPヘッダーの取得をシンプルかつ型安全にします。

- **コード量削減**: `$request->headers->get()` の繰り返しが不要
- **型安全**: string, array, AcceptHeader など適切な型で受け取り
- **自動変換**: camelCase → kebab-case の自動変換
- **エラー処理**: 必須ヘッダーの検証が自動化

EC-CUBEがSymfony 8.x系に対応した際には、API開発やモバイル対応で活躍する機能です。

> 「コントローラーの引数を見れば、そのエンドポイントが何を必要としているか一目でわかる」

これがSymfony 8.x時代のコントローラーです。

## どう思いますか？

この機能について、ご意見があればコメントで教えてください：

- **すぐ使いたい派**: EC-CUBEのSymfony 8.x対応が待ち遠しい
- **様子見派**: 既存コードとの兼ね合いが気になる
- **他に欲しい機能**: `#[MapCookie]` とか欲しくないですか？

## 参考リンク

- [MapRequestHeader PR #51379 (GitHub)](https://github.com/symfony/symfony/commit/3e03afd7f9b2abe59063f156c44a28d64e90be0d)
- [A Week of Symfony #1002](https://symfony.com/blog/a-week-of-symfony-1002-march-9-15-2026)
- [Symfony 8.1 Release](https://symfony.com/releases/8.1)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---