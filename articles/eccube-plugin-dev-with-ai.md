---
title: "EC-CUBEプラグイン開発をAIで効率化してみた"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "ai"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE 4 系プラグイン開発において、AI（Claude Code）を活用して効率化を試みた事例を紹介します。設計フェーズとレビューフェーズで特に役立ったので、具体的な活用方法を共有します。

## 背景と課題

EC-CUBE 4 は Symfony ベースのため、プラグイン開発では以下の知識が求められます。

- Symfony のアーキテクチャ（DI、Form、Validator など）
- EC-CUBE 固有の拡張ポイント（Event、FormExtension など）
- PSR 準拠のコーディング規約

特に**設計フェーズ**と**コードレビュー対応**で時間がかかっていました。

| フェーズ | 従来の課題 |
|---------|-----------|
| 設計 | サービス分割の判断に迷う、責務が曖昧になりがち |
| 実装 | 既存コードとの整合性確認に時間がかかる |
| レビュー | 指摘への対応で手戻りが多い |

## 今回やったこと

### 対象

管理画面への機能追加プラグインを開発しました。

```
Plugin/
└── YourPlugin/
    ├── Controller/Admin/
    │   └── SampleController.php
    ├── Entity/
    │   └── Sample.php
    ├── Form/Type/Admin/
    │   └── SampleType.php
    ├── Repository/
    │   └── SampleRepository.php
    └── Service/
        └── SampleService.php
```

### 条件

- PHP 8.2
- PSR-12 準拠
- 既存の EC-CUBE プラグイン構造に合わせる

## AI活用の具体例

### 1. 設計相談

#### サービス分割の判断

**質問例:**
> このプラグインで外部API連携、データ加工、メール送信を行います。サービスクラスをどう分割すべきですか？

**AIの提案:**

```php
<?php

// 1. 外部API連携は専用クライアントに分離
namespace Plugin\YourPlugin\Service;

class ExternalApiClient
{
    public function __construct(
        private HttpClientInterface $httpClient,
        private string $apiEndpoint
    ) {
    }

    public function fetchData(string $id): array
    {
        $response = $this->httpClient->request('GET', $this->apiEndpoint . '/' . $id);
        return $response->toArray();
    }
}
```

```php
<?php

// 2. データ加工はトランスフォーマーとして分離
namespace Plugin\YourPlugin\Service;

class DataTransformer
{
    public function transform(array $rawData): ProcessedData
    {
        // 加工ロジック
        return new ProcessedData(/* ... */);
    }
}
```

```php
<?php

// 3. メール送信は通知サービスとして分離
namespace Plugin\YourPlugin\Service;

class NotificationService
{
    public function __construct(
        private MailService $mailService
    ) {
    }

    public function sendCompletionNotice(Customer $customer, ProcessedData $data): void
    {
        // メール送信ロジック
    }
}
```

```php
<?php

// 4. オーケストレーションは専用サービスで
namespace Plugin\YourPlugin\Service;

class SampleOrchestrator
{
    public function __construct(
        private ExternalApiClient $apiClient,
        private DataTransformer $transformer,
        private NotificationService $notification
    ) {
    }

    public function execute(string $id, Customer $customer): void
    {
        $rawData = $this->apiClient->fetchData($id);
        $processedData = $this->transformer->transform($rawData);
        $this->notification->sendCompletionNotice($customer, $processedData);
    }
}
```

単一責任の原則に基づいた分割案を即座に提示してもらえました。

#### Voter の要否判断

**質問例:**
> 管理者ロールによってアクセス制限をかけたいのですが、Voter を使うべきですか？

**AIの回答:**

```php
<?php

// シンプルなロールチェックなら #[IsGranted] で十分
namespace Plugin\YourPlugin\Controller\Admin;

use Symfony\Component\Security\Http\Attribute\IsGranted;

class SampleController extends AbstractController
{
    #[Route(
        path: '/%eccube_admin_route%/sample',
        name: 'admin_sample_index'
    )]
    #[IsGranted('ROLE_ADMIN')]
    public function index(): Response
    {
        // ...
    }
}
```

```php
<?php

// 複雑な条件（リソースの所有者チェックなど）がある場合は Voter を使う
namespace Plugin\YourPlugin\Security\Voter;

use Symfony\Component\Security\Core\Authorization\Voter\Voter;

class SampleVoter extends Voter
{
    public const EDIT = 'SAMPLE_EDIT';

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $attribute === self::EDIT && $subject instanceof Sample;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $user = $token->getUser();

        // リソースの作成者のみ編集可能
        return $subject->getCreatedBy() === $user;
    }
}
```

要件に応じた使い分けの基準を明確にできました。

### 2. リファクタ提案

#### 120行メソッドの分割

**Before（問題のあるコード）:**

```php
<?php

public function register(Request $request): Response
{
    // フォーム処理（20行）
    $form = $this->createForm(SampleType::class);
    $form->handleRequest($request);
    // ...validation...

    // データ取得（25行）
    $existingData = $this->repository->findBy([/* ... */]);
    // ...filtering...
    // ...sorting...

    // 計算処理（30行）
    $total = 0;
    foreach ($items as $item) {
        // ...complex calculation...
    }

    // 外部API連携（25行）
    $response = $this->httpClient->request(/* ... */);
    // ...error handling...

    // DB保存（20行）
    $entity = new Sample();
    // ...setting properties...
    $this->entityManager->persist($entity);
    $this->entityManager->flush();

    return $this->redirectToRoute('admin_sample_index');
}
```

**After（リファクタ後）:**

```php
<?php

namespace Plugin\YourPlugin\Controller\Admin;

class SampleController extends AbstractController
{
    public function __construct(
        private SampleService $sampleService
    ) {
    }

    #[Route(
        path: '/%eccube_admin_route%/sample/register',
        name: 'admin_sample_register',
        methods: ['GET', 'POST']
    )]
    public function register(Request $request): Response
    {
        $form = $this->createForm(SampleType::class);
        $form->handleRequest($request);

        if ($form->isSubmitted() && $form->isValid()) {
            try {
                $this->sampleService->register($form->getData());
                $this->addSuccess('admin.common.save_complete', 'admin');

                return $this->redirectToRoute('admin_sample_index');
            } catch (SampleException $e) {
                $this->addError($e->getMessage(), 'admin');
            }
        }

        return $this->render('@YourPlugin/admin/sample_register.twig', [
            'form' => $form->createView(),
        ]);
    }
}
```

```php
<?php

namespace Plugin\YourPlugin\Service;

class SampleService
{
    public function __construct(
        private SampleRepository $repository,
        private Calculator $calculator,
        private ExternalApiClient $apiClient,
        private EntityManagerInterface $entityManager
    ) {
    }

    public function register(SampleDto $dto): Sample
    {
        $existingData = $this->fetchExistingData($dto);
        $calculatedValue = $this->calculator->calculate($existingData);
        $externalData = $this->apiClient->fetch($dto->getExternalId());

        $sample = $this->createSample($dto, $calculatedValue, $externalData);

        $this->entityManager->persist($sample);
        $this->entityManager->flush();

        return $sample;
    }

    private function fetchExistingData(SampleDto $dto): array
    {
        return $this->repository->findByConditions($dto->toSearchCriteria());
    }

    private function createSample(
        SampleDto $dto,
        int $calculatedValue,
        array $externalData
    ): Sample {
        $sample = new Sample();
        $sample->setName($dto->getName());
        $sample->setValue($calculatedValue);
        $sample->setExternalData($externalData);

        return $sample;
    }
}
```

Controller は薄く保ち、ビジネスロジックは Service に移動しました。

#### DI の整理

**Before:**

```php
<?php

public function __construct(
    private EntityManagerInterface $entityManager,
    private SampleRepository $sampleRepository,
    private AnotherRepository $anotherRepository,
    private MailService $mailService,
    private HttpClientInterface $httpClient,
    private LoggerInterface $logger,
    private TranslatorInterface $translator,
    private RouterInterface $router
) {
}
```

**After:**

```php
<?php

// コントローラーには本当に必要なものだけ
public function __construct(
    private SampleService $sampleService
) {
}
```

```php
<?php

// サービス側で必要な依存を持つ
namespace Plugin\YourPlugin\Service;

class SampleService
{
    public function __construct(
        private SampleRepository $sampleRepository,
        private NotificationService $notificationService,
        private ExternalApiClient $apiClient
    ) {
    }
}
```

依存の数が減り、テストも書きやすくなりました。

### 3. PR 説明文の改善

#### Why の補強

**Before:**

```markdown
## 変更内容
- SampleService を追加
- SampleController を修正
- SampleType を追加
```

**After:**

```markdown
## 背景・目的

現状、サンプル登録処理がコントローラーに集中しており、以下の問題がありました。

- テストが書きにくい（HTTP リクエストが必要）
- 処理の再利用ができない
- 変更時の影響範囲が把握しにくい

本 PR では、ビジネスロジックをサービス層に分離し、保守性を向上させます。

## 変更内容

### 新規追加
- `SampleService`: 登録ロジックを担当
- `SampleType`: バリデーション定義

### 修正
- `SampleController`: サービス呼び出しに変更（ロジック削除）

## 影響範囲

- 管理画面 > サンプル管理 > 登録機能
- 既存データへの影響なし
- 外部連携への影響なし
```

レビュアーが「なぜこの変更が必要か」を理解しやすくなりました。

## 効果が大きかった場面

### 1. 既存コードとの整合性確認

AI にプロジェクトの既存コードを読み込ませた上で質問すると、既存の命名規則やディレクトリ構造に合わせた提案をしてくれました。

### 2. Symfony ドキュメントの要約

「Rate Limiter の設定方法を教えて」と聞くと、EC-CUBE プラグインの文脈に合わせた具体的なコード例を提示してくれました。

### 3. エラーメッセージの解読

Symfony の長いスタックトレースを貼り付けると、原因と解決策を提示してくれました。

## 注意点

AI を活用する際の注意点もあります。

1. **提案の検証は必須**: AI の提案をそのまま使わず、動作確認とコードレビューは必ず行う
2. **セキュリティの確認**: 特に認証・認可周りは人間の目でチェック
3. **EC-CUBE 固有の仕様**: EC-CUBE 特有の Event や PurchaseFlow などは、公式ドキュメントと照らし合わせる

## まとめ

| 活用シーン | 効果 |
|-----------|------|
| 設計相談 | 迷いが減り、判断が早くなる |
| リファクタ提案 | 客観的な改善案が得られる |
| PR 説明文作成 | レビュアー視点の補強ができる |

AI はペアプログラミングの相手として優秀です。特に「この設計でいいのか？」という迷いを解消するのに役立ちました。

ただし、最終的な判断は人間が行う必要があります。AI の提案を鵜呑みにせず、チームのコーディング規約や EC-CUBE の仕様と照らし合わせて採用するかどうかを決めてください。

## 参考リンク

- [EC-CUBE 4 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [Symfony Documentation](https://symfony.com/doc/current/index.html)
- [Claude Code](https://claude.ai/claude-code)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
