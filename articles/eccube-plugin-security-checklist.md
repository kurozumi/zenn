---
title: "EC-CUBEプラグイン開発者が押さえるべきセキュリティチェックリスト"
emoji: "🔐"
type: "tech"
topics: ["eccube", "security", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBEでプラグインを開発する際、セキュリティは最も重要な要素の一つです。この記事では、プラグイン開発時に必ずチェックすべきセキュリティ項目をまとめました。

## 1. SQLインジェクション対策

### チェックポイント
- ユーザー入力をそのままSQLクエリに埋め込んでいないか
- DoctrineのQueryBuilderまたはDQLを使用しているか
- プレースホルダ（バインドパラメータ）を使用しているか

### 悪い例
```php
// 危険: ユーザー入力を直接クエリに埋め込んでいる
$sql = "SELECT * FROM dtb_product WHERE name = '" . $request->get('name') . "'";
```

### 良い例
```php
// 安全: QueryBuilderとパラメータバインディングを使用
$qb = $this->createQueryBuilder('p')
    ->where('p.name = :name')
    ->setParameter('name', $request->get('name'));
```

## 2. クロスサイトスクリプティング（XSS）対策

### チェックポイント
- Twigテンプレートで `{{ }}` を使用しているか（自動エスケープ）
- `|raw` フィルターを不用意に使用していないか
- JavaScriptに動的な値を埋め込む際はエスケープしているか

### 悪い例
```twig
{# 危険: rawフィルターでエスケープを無効化 #}
{{ user_input|raw }}
```

### 良い例
```twig
{# 安全: 自動エスケープが適用される #}
{{ user_input }}

{# HTMLを許可する場合は、サニタイズしてから #}
{{ sanitized_html|raw }}
```

## 3. クロスサイトリクエストフォージェリ（CSRF）対策

### チェックポイント
- フォームにCSRFトークンを含めているか
- POST/PUT/DELETEリクエストでトークンを検証しているか
- Symfonyの `CsrfTokenManagerInterface` を活用しているか

### 良い例
```php
// Controllerでの検証
use Symfony\Component\Security\Csrf\CsrfTokenManagerInterface;

public function delete(Request $request, CsrfTokenManagerInterface $csrfTokenManager)
{
    $token = new CsrfToken('delete_item', $request->request->get('_token'));
    if (!$csrfTokenManager->isTokenValid($token)) {
        throw new InvalidCsrfTokenException();
    }
    // 処理を続行
}
```

```twig
{# Twigテンプレートでのトークン埋め込み #}
<input type="hidden" name="_token" value="{{ csrf_token('delete_item') }}">
```

## 4. 認証・認可の適切な実装

### チェックポイント
- 管理画面のControllerに適切なアクセス制御があるか
- `@Route` のセキュリティ設定は適切か
- ユーザーが他のユーザーのデータにアクセスできないか

### 良い例
```php
use Sensio\Bundle\FrameworkExtraBundle\Configuration\IsGranted;

/**
 * @Route("/admin/plugin/sample")
 * @IsGranted("ROLE_ADMIN")
 */
class SampleController extends AbstractController
{
    // 管理者のみアクセス可能
}
```

## 5. ファイルアップロードのセキュリティ

### チェックポイント
- 許可するファイル拡張子を制限しているか
- MIMEタイプを検証しているか
- アップロード先ディレクトリはWebルート外か
- ファイル名をランダム化しているか

### 良い例
```php
$allowedExtensions = ['jpg', 'jpeg', 'png', 'gif'];
$extension = $file->guessExtension();

if (!in_array($extension, $allowedExtensions)) {
    throw new \Exception('許可されていないファイル形式です');
}

// ファイル名をランダム化
$newFilename = bin2hex(random_bytes(16)) . '.' . $extension;
```

## 6. セッション管理

### チェックポイント
- セッションIDは認証後に再生成しているか
- セッションのタイムアウトは適切か
- セッションCookieにSecure/HttpOnly属性が設定されているか

### 設定例（config/packages/framework.yaml）
```yaml
framework:
    session:
        cookie_secure: auto
        cookie_httponly: true
        cookie_samesite: lax
```

## 7. 機密情報の取り扱い

### チェックポイント
- APIキーや認証情報をコードにハードコードしていないか
- 環境変数または `.env` ファイルを使用しているか
- ログに機密情報を出力していないか
- エラーメッセージで内部情報を漏らしていないか

### 良い例
```php
// .envファイルから取得
$apiKey = $_ENV['EXTERNAL_API_KEY'];

// ログ出力時は機密情報をマスク
$this->logger->info('API呼び出し', [
    'endpoint' => $endpoint,
    // 'api_key' => $apiKey,  // 絶対にログに出力しない
]);
```

## 8. 入力値のバリデーション

### チェックポイント
- すべてのユーザー入力をバリデーションしているか
- サーバーサイドでのバリデーションを実装しているか（クライアントサイドのみに頼らない）
- 型、長さ、形式を適切にチェックしているか

### 良い例
```php
use Symfony\Component\Validator\Constraints as Assert;

class SampleType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options)
    {
        $builder->add('email', EmailType::class, [
            'constraints' => [
                new Assert\NotBlank(),
                new Assert\Email(),
                new Assert\Length(['max' => 255]),
            ],
        ]);
    }
}
```

## 9. 依存パッケージの脆弱性管理

### チェックポイント
- `composer audit` で脆弱性をチェックしているか
- 定期的にパッケージを更新しているか
- 使用していないパッケージを削除しているか

### 実行コマンド
```bash
# 脆弱性チェック
composer audit

# パッケージ更新
composer update --with-all-dependencies
```

## 10. ログとモニタリング

### チェックポイント
- セキュリティ関連のイベントをログに記録しているか
- ログファイルへのアクセス権限は適切か
- 異常なアクセスパターンを検知できるか

### 良い例
```php
// 認証失敗をログに記録
$this->logger->warning('認証失敗', [
    'ip_address' => $request->getClientIp(),
    'attempted_user' => $username,
    'timestamp' => new \DateTime(),
]);
```

## まとめ

EC-CUBEプラグイン開発において、セキュリティは「後から対応する」ものではなく、**設計段階から組み込むべき要素**です。

このチェックリストを開発の各フェーズで活用し、安全なプラグインを提供しましょう。

### 最低限守るべき3つの原則

1. **ユーザー入力を信用しない** - すべての入力値はバリデーションとサニタイズを行う
2. **最小権限の原則** - 必要最小限の権限のみを付与する
3. **多層防御** - 一つの対策に頼らず、複数の防御層を設ける

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
