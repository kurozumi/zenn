---
title: "Symfony 8.1のEntityExistsをEC-CUBE 4.3で今すぐ使う方法"
emoji: "🔍"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

:::details TL;DR（要約）
- EC-CUBE プラグインで DTO に外部参照 ID を受け取るとき、ID 存在確認のバリデーションが抜けがちな落とし穴がある
- `EntityType` を使えば自動で存在確認が入るが、DTO + `ValidatorInterface` では自前実装が必要
- `ConstraintValidator` を継承した `EntityExistsValidator` を実装することで、属性1行で存在チェックが書ける
- Symfony 8.1（2026年5月予定）では公式の `EntityExists` 制約が追加されるため、移行コストも最小限
- `repositoryMethod` オプションで「退会済み会員を除外」など複雑な条件にも対応できる
:::

## はじめに

**外部システムから受け取った商品 ID が存在しないまま処理が通ってしまう。**
こうしたバグは本番環境で静かに積み上がります。

**この記事では、そのリスクをゼロにする `EntityExists` カスタム Validator を、コピーして使えるコードとともに解説します。**

EC-CUBE プラグインで DTO や API リクエストのバリデーションを書くとき、`EntityType` を使ったフォームなら選択肢の検証が自動で入りますが、DTO に直接バリデーションを書く場合は自前で実装する必要があります。

**しかも Symfony 8.1 で `EntityExists` 制約が公式に追加予定（PR #63483）です。EC-CUBE 4.3（Symfony ^6.4）ではまだ使えないため、今回は同等機能を先取り実装します。**

この記事でわかること：

1. Symfony 8.1 で追加予定の `EntityExists` 制約の仕様
2. EC-CUBE 4.3 で今すぐ動く `EntityExistsValidator` の完全実装
3. DTO・FormType・カスタムリポジトリメソッドへの適用例

## Symfony 8.1 の EntityExists 制約（予告）

Symfony 8.1（2026年5月リリース予定、PR #63483）で追加される `EntityExists` 制約は、エンティティの存在確認を属性で簡潔に書けるようにします。

```php
use Symfony\Bridge\Doctrine\Validator\Constraints\EntityExists;

class ProductImportDto
{
    #[EntityExists(entityClass: Product::class)]
    public int $productId;
}
```

主なパラメーター：

| パラメーター | 説明 |
|---|---|
| `entityClass` | 検索対象エンティティクラス（必須） |
| `identifierField` | 検索フィールド名（省略時は主キー） |
| `repositoryMethod` | カスタムリポジトリメソッド名 |
| `em` | 使用するエンティティマネージャー名 |
| `message` | カスタムエラーメッセージ |

`null` や空文字列はバリデーションをスキップするため、任意フィールドにも使いやすい設計です。

`identifierField` と `repositoryMethod` は同時指定できません（`\InvalidArgumentException` が発生）。

## EC-CUBE 4.3 でのカスタム実装

EC-CUBE 4.3 は Symfony 6.4 を使用しているため、`EntityExists` は使えません。ただし Symfony の `ConstraintValidator` を継承すれば同等機能を実装できます。

EC-CUBE のコアコードでも `src/Eccube/Form/Validator/Email.php` と `EmailValidator.php` のペアで同じパターンが使われています。

### ディレクトリ構成（プラグイン例）

```
app/Plugin/MyPlugin/
├── Validator/
│   ├── EntityExists.php          # Constraint クラス
│   └── EntityExistsValidator.php # ConstraintValidator クラス
└── Form/
    └── Type/
        └── ProductImportType.php
```

### Constraint クラス

```php
<?php
// app/Plugin/MyPlugin/Validator/EntityExists.php

namespace Plugin\MyPlugin\Validator;

use Symfony\Component\Validator\Constraint;

#[\Attribute(\Attribute::TARGET_PROPERTY | \Attribute::TARGET_METHOD | \Attribute::IS_REPEATABLE)]
class EntityExists extends Constraint
{
    // Symfony の規約に従い UUID 形式のエラーコード定数を定義
    public const NOT_FOUND_ERROR = 'f7ef7fa8-4ef7-48d2-a264-b57447e1f2ad';

    protected const ERROR_NAMES = [
        self::NOT_FOUND_ERROR => 'NOT_FOUND_ERROR',
    ];

    public string $message = 'The referenced entity does not exist.';

    public function __construct(
        public readonly string $entityClass,
        public readonly ?string $identifierField = null,
        public readonly ?string $repositoryMethod = null,
        ?string $message = null,
        ?array $groups = null,
        mixed $payload = null,
        array $options = [],
    ) {
        if ($identifierField !== null && $repositoryMethod !== null) {
            throw new \InvalidArgumentException(
                'The "identifierField" and "repositoryMethod" options cannot be used simultaneously.'
            );
        }

        parent::__construct($options, $groups, $payload);

        if ($message !== null) {
            $this->message = $message;
        }
    }
}
```

### ConstraintValidator クラス

```php
<?php
// app/Plugin/MyPlugin/Validator/EntityExistsValidator.php

namespace Plugin\MyPlugin\Validator;

use Doctrine\Persistence\ManagerRegistry;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;
use Symfony\Component\Validator\Exception\UnexpectedTypeException;

class EntityExistsValidator extends ConstraintValidator
{
    public function __construct(private readonly ManagerRegistry $registry)
    {
    }

    public function validate(mixed $value, Constraint $constraint): void
    {
        if (!$constraint instanceof EntityExists) {
            throw new UnexpectedTypeException($constraint, EntityExists::class);
        }

        // null・空文字はスキップ（任意フィールド対応）
        if ($value === null || $value === '') {
            return;
        }

        $em = $this->registry->getManagerForClass($constraint->entityClass);

        if ($em === null) {
            throw new \LogicException(
                sprintf('No entity manager found for class "%s".', $constraint->entityClass)
            );
        }

        $repository = $em->getRepository($constraint->entityClass);

        if ($constraint->repositoryMethod !== null) {
            $method = $constraint->repositoryMethod;

            // 存在しないメソッド名による Error を防ぐ
            if (!method_exists($repository, $method)) {
                throw new \LogicException(
                    sprintf('Method "%s" does not exist on repository "%s".', $method, $repository::class)
                );
            }

            $result = $repository->$method($value);
        } elseif ($constraint->identifierField !== null) {
            // 指定フィールドで検索（findOneBy はパラメータバインディングを使うため SQL インジェクションは発生しない）
            $result = $repository->findOneBy([$constraint->identifierField => $value]);
        } else {
            // 主キーで検索
            $result = $repository->find($value);
        }

        if ($result === null) {
            $this->context->buildViolation($constraint->message)
                ->setParameter('{{ value }}', $this->formatValue($value))
                ->setCode(EntityExists::NOT_FOUND_ERROR)
                ->addViolation();
        }
    }
}
```

### サービス定義

`ManagerRegistry` を DI するため、サービスとして登録します。

```yaml
# app/Plugin/MyPlugin/Resource/config/services.yaml
services:
    Plugin\MyPlugin\Validator\EntityExistsValidator:
        arguments:
            - '@doctrine'
        tags:
            - { name: validator.constraint_validator }
```

### 使い方

#### DTO クラスでの使用

```php
<?php

namespace Plugin\MyPlugin\Dto;

use Eccube\Entity\Customer;
use Eccube\Entity\Product;
use Plugin\MyPlugin\Validator\EntityExists;
use Symfony\Component\Validator\Constraints as Assert;

class OrderImportDto
{
    #[Assert\NotBlank]
    #[Assert\Positive]
    #[EntityExists(entityClass: Product::class)]
    public ?int $productId = null;

    #[Assert\NotBlank]
    #[Assert\Positive]
    #[EntityExists(
        entityClass: Customer::class,
        message: '指定された会員は存在しません。'
    )]
    public ?int $customerId = null;
}
```

#### FormType での使用

```php
<?php

namespace Plugin\MyPlugin\Form\Type;

use Eccube\Entity\Product;
use Plugin\MyPlugin\Validator\EntityExists;
use Symfony\Component\Form\AbstractType;
use Symfony\Component\Form\Extension\Core\Type\IntegerType;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Validator\Constraints as Assert;

class ProductImportType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('productId', IntegerType::class, [
                'label' => '商品ID',
                'constraints' => [
                    new Assert\NotBlank(),
                    new Assert\Positive(),
                    new EntityExists(entityClass: Product::class),
                ],
            ]);
    }
}
```

#### カスタムリポジトリメソッドの活用

退会済み会員を除外するなど、単純な `find()` では対応できないケースにはカスタムリポジトリメソッドが使えます。

```php
<?php

namespace Eccube\Repository;

use Eccube\Entity\Customer;
use Eccube\Entity\Master\CustomerStatus;

// CustomerRepository に追加するメソッド
public function findActiveById(int $id): ?Customer
{
    return $this->createQueryBuilder('c')
        ->andWhere('c.id = :id')
        ->andWhere('c.Status = :status')
        ->setParameter('id', $id)
        ->setParameter('status', CustomerStatus::REGULAR) // 本会員
        ->getQuery()
        ->getOneOrNullResult();
}
```

```php
#[EntityExists(
    entityClass: Customer::class,
    repositoryMethod: 'findActiveById',
    message: '有効な会員が見つかりません。'
)]
public ?int $customerId = null;
```

#### コントローラーでのバリデーション実行

管理画面で使う場合は、`#[IsGranted]` による権限チェックと CSRF トークン検証を必ず実装してください。

```php
<?php

namespace Plugin\MyPlugin\Controller\Admin;

use Plugin\MyPlugin\Dto\OrderImportDto;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Security\Csrf\CsrfToken;
use Symfony\Component\Security\Csrf\CsrfTokenManagerInterface;
use Symfony\Component\Security\Http\Attribute\IsGranted;
use Symfony\Component\Validator\Validator\ValidatorInterface;

class ImportController extends AbstractController
{
    public function __construct(
        private readonly CsrfTokenManagerInterface $csrfTokenManager,
    ) {}

    #[IsGranted('ROLE_ADMIN')]
    #[Route('/admin/plugin/import', methods: ['POST'])]
    public function import(Request $request, ValidatorInterface $validator): Response
    {
        // CSRF トークン検証
        $token = new CsrfToken('import', $request->request->get('_token'));
        if (!$this->csrfTokenManager->isTokenValid($token)) {
            throw $this->createAccessDeniedException('Invalid CSRF token.');
        }

        $dto = new OrderImportDto();
        $dto->productId = $request->request->getInt('product_id');
        $dto->customerId = $request->request->getInt('customer_id');

        $violations = $validator->validate($dto);

        if (count($violations) > 0) {
            foreach ($violations as $violation) {
                $this->addFlash('danger', $violation->getMessage());
            }

            return $this->redirectToRoute('plugin_myPlugin_admin_import_index');
        }

        // バリデーション通過後の処理...

        return $this->redirectToRoute('plugin_myPlugin_admin_import_index');
    }
}
```

Twig テンプレート側で CSRF トークンを出力します。

```twig
<form method="post" action="{{ path('plugin_myPlugin_admin_import') }}">
    <input type="hidden" name="_token" value="{{ csrf_token('import') }}">
    {# フォームの内容 #}
</form>
```

## UniqueEntity との違い

EC-CUBE のコアでも使われている `UniqueEntity` と今回実装した `EntityExists` は目的が異なります。

| | EntityExists | UniqueEntity |
|---|---|---|
| **目的** | 参照先エンティティが存在するか | フィールド値が重複していないか |
| **付与対象** | プロパティ・メソッド | クラス |
| **主な用途** | DTO の外部参照 ID 検証 | エンティティの一意性制約 |
| **EC-CUBE での実例** | （今回の実装） | `Customer::loadValidatorMetadata()` |

EC-CUBE では `Customer::loadValidatorMetadata()` でメールアドレスの重複チェックに `UniqueEntity` が使われています。

## まとめ

- Symfony 8.1 で追加予定の `EntityExists` 制約は参照整合性バリデーションをシンプルに書ける便利な機能
- EC-CUBE 4.3（Symfony 6.4）では使えないが、`ConstraintValidator` を継承して同等機能を自前実装できる
- プロパティレベルで属性として付与できるため、DTO やフォームで直感的に使える
- `repositoryMethod` を使えば、退会済み会員の除外など複雑な条件にも対応できる
- 管理画面コントローラーでは `#[IsGranted]` と CSRF 検証を必ず実装すること

Symfony 8.1 がリリースされ EC-CUBE が対応するまでの橋渡しとして、ぜひ活用してみてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
