## 基本的な使い方

### シンプルな例：投稿者チェック

```php
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Security\Http\Attribute\IsGranted;
use Symfony\Component\Security\Http\Attribute\IsGrantedContext;

class PostController extends AbstractController
{
    #[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
        // 投稿の作成者のみアクセス可能
        return $context->user === $subject->getAuthor();
    }, subject: 'post')]
    public function edit(Post $post): Response
    {
        // 編集処理
    }
}
```

### IsGrantedContext が提供するもの

コーラブルには `IsGrantedContext` と `$subject` の2つのパラメータが渡されます：

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `$context` | `IsGrantedContext` | 認可コンテキスト |
| `$subject` | `mixed` | アクセス対象のオブジェクト |

`IsGrantedContext` は以下のプロパティとメソッドを提供します：

| プロパティ/メソッド | 説明 |
|-------------------|------|
| `$context->token` | 認証トークン（`TokenInterface`） |
| `$context->user` | 現在のユーザー（未認証時は `null`） |
| `$context->isGranted()` | 他のロール/パーミッションをチェック |
| `$context->isAuthenticated()` | 認証済みかどうか |
| `$context->isAuthenticatedFully()` | 完全認証済みかどうか |

## EC-CUBEでの実用例

### 例1: 商品の編集権限チェック

EC-CUBEで特定のメンバーが作成した商品のみ編集可能にする例です：

```php
namespace Customize\Controller\Admin;

use Eccube\Entity\Member;
use Eccube\Entity\Product;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;
use Symfony\Component\Security\Http\Attribute\IsGrantedContext;

class ProductController extends AbstractController
{
    #[Route('/admin/product/{id}/edit', name: 'admin_product_edit')]
    #[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
        // 管理者は全商品を編集可能
        if ($context->isGranted('ROLE_ADMIN')) {
            return true;
        }

        // メンバーでなければアクセス拒否
        if (!$context->user instanceof Member) {
            return false;
        }

        // 商品作成者のみ編集可能
        return $subject->getCreator() === $context->user;
    }, subject: 'product')]
    public function edit(Product $product): Response
    {
        // 編集フォームを表示
    }
}
```

### 例2: 注文の閲覧権限（顧客側）

マイページで自分の注文のみ閲覧可能にする例：

```php
namespace Customize\Controller;

use Eccube\Entity\Customer;
use Eccube\Entity\Order;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;
use Symfony\Component\Security\Http\Attribute\IsGrantedContext;

class MyPageOrderController extends AbstractController
{
    #[Route('/mypage/order/{id}', name: 'mypage_order_detail')]
    #[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
        // 顧客でなければアクセス拒否
        if (!$context->user instanceof Customer) {
            return false;
        }

        // 自分の注文のみ閲覧可能
        return $subject->getCustomer()?->getId() === $context->user->getId();
    }, subject: 'order')]
    public function detail(Order $order): Response
    {
        return $this->render('Mypage/order_detail.twig', [
            'Order' => $order,
        ]);
    }
}
```

### 例3: 複雑な条件分岐

公開状態に応じたアクセス制御：

```php
namespace Customize\Controller;

use Eccube\Entity\Master\ProductStatus;
use Eccube\Entity\Product;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Security\Http\Attribute\IsGranted;
use Symfony\Component\Security\Http\Attribute\IsGrantedContext;

class ProductDetailController extends AbstractController
{
    #[Route('/products/{id}', name: 'product_detail')]
    #[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
        /** @var Product $product */
        $product = $subject;

        // 公開中の商品は誰でも閲覧可能
        $status = $product->getStatus();
        if ($status !== null && $status->getId() === ProductStatus::DISPLAY_SHOW) {
            return true;
        }

        // 非公開商品は管理者のみ
        return $context->isGranted('ROLE_ADMIN');
    }, subject: 'product')]
    public function detail(Product $product): Response
    {
        return $this->render('Product/detail.twig', [
            'Product' => $product,
        ]);
    }
}
```

## subject パラメータの柔軟な指定

`subject` パラメータにもコーラブルを使用できます：

```php
#[IsGranted(
    static function (IsGrantedContext $context, mixed $subject): bool {
        return $context->user === $subject['order']->getCustomer();
    },
    subject: static function (array $args): array {
        return [
            'order' => $args['order'],
            'items' => $args['order']->getOrderItems(),
        ];
    }
)]
public function show(Order $order): Response
{
    // ...
}
```

## 従来の方法との比較

### Voter を使う場合（従来）

```php
// App/Security/Voter/ProductVoter.php
class ProductVoter extends Voter
{
    protected function supports(string $attribute, mixed $subject): bool
    {
        return $attribute === 'EDIT' && $subject instanceof Product;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $user = $token->getUser();
        return $subject->getCreator() === $user;
    }
}

// Controller
#[IsGranted('EDIT', subject: 'product')]
public function edit(Product $product): Response { }
```

### コーラブルを使う場合（Symfony 7.3+）

```php
#[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
    return $subject->getCreator() === $context->user;
}, subject: 'product')]
public function edit(Product $product): Response { }
```

### 比較表

| 観点 | Voter | コーラブル |
|------|-------|----------|
| コード量 | 多い（別ファイル必要） | 少ない（インライン） |
| 再利用性 | 高い | 低い |
| 型安全性 | あり | あり |
| IDE補完 | あり | あり |
| テスト | 単体テスト可能 | コントローラーテストで確認 |

ℹ️ **覚えておきたいルール:**
ℹ️ 複数箇所で使うなら **Voter**、1箇所だけなら **コーラブル**。
ℹ️ 迷ったらVoterを選べば間違いない。

## どっちを使う？30秒判断フローチャート

1. **そのチェック、2箇所以上で使う？**
   - Yes → Voter
   - No → 次へ

2. **ロジックが3行以下？**
   - Yes → コーラブル
   - No → Voter

3. **単体テストが必要？**
   - Yes → Voter
   - No → コーラブル

## あなたはどっち派？

この機能を見て、開発者の間で意見が分かれています：

**コーラブル推進派:**
> 「Voterを作るほどでもない小さなチェックが多い。インラインで書けるのは神機能」

**Voter維持派:**
> 「ロジックが属性に埋まると、テストしにくくなる。保守性を考えるとVoter一択」

あなたはどう思いますか？ぜひコメントで教えてください。

## まとめ

Symfony 7.3の `#[IsGranted]` コーラブル対応は、シンプルなアクセス制御を直感的に記述できる便利な機能です。

- **メリット**: コード量削減、型安全、IDE補完
- **デメリット**: 再利用性が低い、複雑なロジックには不向き
- **EC-CUBEでの活用**: 商品や注文の所有者チェックなど

EC-CUBEがSymfony 7.x系に対応した際には、ぜひ活用してみてください。

## 参考リンク

- [New in Symfony 7.3: Security Improvements](https://symfony.com/blog/new-in-symfony-7-3-security-improvements)
- [Symfony PR #59150: Allow using a callable with IsGranted](https://github.com/symfony/symfony/pull/59150)
- [PHP RFC: Closures in const expressions](https://wiki.php.net/rfc/closures_in_const_expr)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---