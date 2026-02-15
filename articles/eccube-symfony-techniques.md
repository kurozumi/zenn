---
title: "EC-CUBEプラグインで使えるSymfonyの技術10選"
emoji: "🎼"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE 4 は Symfony をベースに構築されているため、Symfony の豊富な機能をプラグイン開発で活用できます。この記事では、プラグイン開発で特に役立つ Symfony の技術を10個、サンプルコード付きで紹介します。

## 1. Workflow Component - 状態管理

受注ステータスやカスタムエンティティの状態遷移を管理できます。

### 設定ファイル

```yaml
# app/Plugin/YourPlugin/Resource/config/services.yaml
framework:
    workflows:
        order_review:
            type: 'state_machine'
            audit_trail:
                enabled: true
            marking_store:
                type: 'method'
                property: 'status'
            supports:
                - Plugin\YourPlugin\Entity\OrderReview
            initial_marking: pending
            places:
                - pending
                - approved
                - rejected
            transitions:
                approve:
                    from: pending
                    to: approved
                reject:
                    from: pending
                    to: rejected
```

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Controller\Admin;

use Eccube\Controller\AbstractController;
use Plugin\YourPlugin\Entity\OrderReview;
use Plugin\YourPlugin\Repository\OrderReviewRepository;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Workflow\WorkflowInterface;

class OrderReviewController extends AbstractController
{
    public function __construct(
        private WorkflowInterface $orderReviewStateMachine,
        private OrderReviewRepository $orderReviewRepository
    ) {
    }

    #[Route(
        path: '/%eccube_admin_route%/order_review/{id}/approve',
        name: 'admin_order_review_approve',
        requirements: ['id' => '\d+'],
        methods: ['POST']
    )]
    public function approve(OrderReview $review): Response
    {
        // 遷移可能かチェック
        if ($this->orderReviewStateMachine->can($review, 'approve')) {
            // 状態を遷移
            $this->orderReviewStateMachine->apply($review, 'approve');
            $this->entityManager->flush();

            $this->addSuccess('admin.common.save_complete', 'admin');
        }

        return $this->redirectToRoute('admin_order_review_list');
    }
}
```

## 2. Messenger Component - 非同期処理

メール送信や外部API連携などを非同期で処理できます。

### メッセージクラス

```php
<?php

namespace Plugin\YourPlugin\Message;

class SendNotificationMessage
{
    public function __construct(
        private int $orderId,
        private string $notificationType
    ) {
    }

    public function getOrderId(): int
    {
        return $this->orderId;
    }

    public function getNotificationType(): string
    {
        return $this->notificationType;
    }
}
```

### ハンドラークラス

```php
<?php

namespace Plugin\YourPlugin\MessageHandler;

use Eccube\Repository\OrderRepository;
use Plugin\YourPlugin\Message\SendNotificationMessage;
use Symfony\Component\Messenger\Attribute\AsMessageHandler;

#[AsMessageHandler]
class SendNotificationMessageHandler
{
    public function __construct(
        private OrderRepository $orderRepository,
        private NotificationService $notificationService
    ) {
    }

    public function __invoke(SendNotificationMessage $message): void
    {
        $order = $this->orderRepository->find($message->getOrderId());

        if ($order) {
            $this->notificationService->send(
                $order,
                $message->getNotificationType()
            );
        }
    }
}
```

### ディスパッチ

```php
<?php

use Plugin\YourPlugin\Message\SendNotificationMessage;
use Symfony\Component\Messenger\MessageBusInterface;

class OrderEventSubscriber implements EventSubscriberInterface
{
    public function __construct(
        private MessageBusInterface $messageBus
    ) {
    }

    public function onOrderComplete(EventArgs $event): void
    {
        $order = $event->getArgument('Order');

        // 非同期でメッセージを送信
        $this->messageBus->dispatch(
            new SendNotificationMessage($order->getId(), 'order_complete')
        );
    }
}
```

## 3. Rate Limiter - レート制限

ログイン試行やAPI呼び出しの回数制限を実装できます。

### 設定ファイル

```yaml
# app/Plugin/YourPlugin/Resource/config/services.yaml
framework:
    rate_limiter:
        api_limiter:
            policy: 'sliding_window'
            limit: 100
            interval: '1 hour'
        login_limiter:
            policy: 'fixed_window'
            limit: 5
            interval: '15 minutes'
```

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Controller;

use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\RateLimiter\RateLimiterFactory;

class ApiController extends AbstractController
{
    public function __construct(
        private RateLimiterFactory $apiLimiter
    ) {
    }

    public function index(Request $request): JsonResponse
    {
        // クライアントIPでレート制限
        $limiter = $this->apiLimiter->create($request->getClientIp());

        if (false === $limiter->consume(1)->isAccepted()) {
            return $this->json([
                'error' => 'リクエスト制限を超えました。しばらくお待ちください。'
            ], 429);
        }

        // 通常の処理
        return $this->json(['data' => $this->getData()]);
    }
}
```

## 4. Lock Component - 排他制御

在庫更新や重複注文防止に活用できます。

### 設定ファイル

```yaml
# app/Plugin/YourPlugin/Resource/config/services.yaml
framework:
    lock:
        inventory: '%env(LOCK_DSN)%'
```

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Service;

use Symfony\Component\Lock\LockFactory;

class InventoryService
{
    public function __construct(
        private LockFactory $lockFactory,
        private ProductClassRepository $productClassRepository
    ) {
    }

    public function decreaseStock(int $productClassId, int $quantity): bool
    {
        // 商品IDでロックを取得
        $lock = $this->lockFactory->createLock('inventory_' . $productClassId);

        // ロックを取得（最大30秒待機）
        if ($lock->acquire(true)) {
            try {
                $productClass = $this->productClassRepository->find($productClassId);
                $currentStock = $productClass->getStock();

                if ($currentStock < $quantity) {
                    return false; // 在庫不足
                }

                $productClass->setStock($currentStock - $quantity);
                $this->entityManager->flush();

                return true;
            } finally {
                // 必ずロックを解放
                $lock->release();
            }
        }

        return false;
    }
}
```

## 5. HttpClient - 外部API連携

配送状況の確認や在庫管理システムとの連携など、外部APIとの通信に使用します。

### サービス定義

```yaml
# app/Plugin/YourPlugin/Resource/config/services.yaml
services:
    Plugin\YourPlugin\Service\ShippingTrackingClient:
        arguments:
            $httpClient: '@http_client'
            $apiEndpoint: '%env(SHIPPING_API_ENDPOINT)%'
```

### 配送状況確認の例

```php
<?php

namespace Plugin\YourPlugin\Service;

use Symfony\Contracts\HttpClient\HttpClientInterface;
use Symfony\Contracts\HttpClient\Exception\ExceptionInterface;

class ShippingTrackingClient
{
    public function __construct(
        private HttpClientInterface $httpClient,
        private string $apiEndpoint
    ) {
    }

    /**
     * 送り状番号から配送状況を取得
     */
    public function getTrackingStatus(string $trackingNumber): ?array
    {
        try {
            $response = $this->httpClient->request('GET', $this->apiEndpoint . '/track', [
                'query' => [
                    'tracking_number' => $trackingNumber,
                ],
                'timeout' => 10,
            ]);

            if ($response->getStatusCode() === 200) {
                return $response->toArray();
            }

            return null;
        } catch (ExceptionInterface $e) {
            return null;
        }
    }
}
```

### 在庫同期の例

```php
<?php

namespace Plugin\YourPlugin\Service;

use Symfony\Contracts\HttpClient\HttpClientInterface;
use Symfony\Contracts\HttpClient\Exception\ExceptionInterface;

class InventorySyncClient
{
    public function __construct(
        private HttpClientInterface $httpClient,
        private string $apiEndpoint,
        private string $apiToken
    ) {
    }

    /**
     * 外部システムから在庫情報を取得
     */
    public function fetchStock(array $productCodes): array
    {
        try {
            $response = $this->httpClient->request('POST', $this->apiEndpoint . '/stock', [
                'headers' => [
                    'Authorization' => 'Bearer ' . $this->apiToken,
                    'Content-Type' => 'application/json',
                ],
                'json' => [
                    'product_codes' => $productCodes,
                ],
                'timeout' => 30,
            ]);

            return $response->toArray();
        } catch (ExceptionInterface $e) {
            throw new \RuntimeException('在庫情報の取得に失敗しました: ' . $e->getMessage());
        }
    }

    /**
     * 在庫数を外部システムに通知
     */
    public function updateStock(string $productCode, int $quantity): bool
    {
        try {
            $response = $this->httpClient->request('PUT', $this->apiEndpoint . '/stock/' . $productCode, [
                'headers' => [
                    'Authorization' => 'Bearer ' . $this->apiToken,
                ],
                'json' => [
                    'quantity' => $quantity,
                ],
            ]);

            return $response->getStatusCode() === 200;
        } catch (ExceptionInterface $e) {
            return false;
        }
    }
}
```

## 6. Validator（カスタム制約） - 独自バリデーション

独自のバリデーションルールを作成し、FormExtension でコアのフォームに適用できます。

### 制約クラス

```php
<?php

namespace Plugin\YourPlugin\Validator\Constraints;

use Symfony\Component\Validator\Constraint;

#[\Attribute(\Attribute::TARGET_PROPERTY | \Attribute::TARGET_METHOD)]
class UniqueProductCode extends Constraint
{
    public string $message = '商品コード「{{ code }}」は既に使用されています。';
    public ?int $excludeId = null;
}
```

### バリデータクラス

```php
<?php

namespace Plugin\YourPlugin\Validator\Constraints;

use Eccube\Repository\ProductRepository;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

class UniqueProductCodeValidator extends ConstraintValidator
{
    public function __construct(
        private ProductRepository $productRepository
    ) {
    }

    public function validate(mixed $value, Constraint $constraint): void
    {
        if (null === $value || '' === $value) {
            return;
        }

        $existingProduct = $this->productRepository->findOneBy(['code' => $value]);

        // 編集中の商品は除外
        if ($existingProduct && $existingProduct->getId() !== $constraint->excludeId) {
            $this->context->buildViolation($constraint->message)
                ->setParameter('{{ code }}', $value)
                ->addViolation();
        }
    }
}
```

### FormExtension で既存フォームに適用

```php
<?php

namespace Plugin\YourPlugin\Form\Extension;

use Eccube\Form\Type\Admin\ProductType;
use Plugin\YourPlugin\Validator\Constraints\UniqueProductCode;
use Symfony\Component\Form\AbstractTypeExtension;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\FormEvent;
use Symfony\Component\Form\FormEvents;

class ProductTypeExtension extends AbstractTypeExtension
{
    public static function getExtendedTypes(): iterable
    {
        yield ProductType::class;
    }

    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        // フォーム生成時に既存の商品IDを取得してバリデーションに渡す
        $builder->addEventListener(FormEvents::PRE_SET_DATA, function (FormEvent $event) {
            $product = $event->getData();
            $form = $event->getForm();

            // 既存のcodeフィールドにカスタム制約を追加
            $codeField = $form->get('code');
            $options = $codeField->getConfig()->getOptions();

            $options['constraints'][] = new UniqueProductCode(
                excludeId: $product?->getId()
            );

            $form->add('code', $codeField->getConfig()->getType()->getInnerType()::class, $options);
        });
    }
}
```

## 7. ExpressionLanguage - 動的条件評価

送料計算や割引条件など、管理画面から設定可能な動的ルールを実装できます。

### サービスクラス

```php
<?php

namespace Plugin\YourPlugin\Service;

use Symfony\Component\ExpressionLanguage\ExpressionLanguage;

class DiscountRuleEvaluator
{
    private ExpressionLanguage $expressionLanguage;

    public function __construct()
    {
        $this->expressionLanguage = new ExpressionLanguage();

        // カスタム関数を登録
        $this->expressionLanguage->register(
            'contains',
            fn($str, $needle) => sprintf('str_contains(%s, %s)', $str, $needle),
            fn($arguments, $str, $needle) => str_contains($str, $needle)
        );
    }

    /**
     * 割引ルールを評価
     *
     * @param string $expression 例: "subtotal >= 10000 and itemCount >= 3"
     * @param array $context 評価コンテキスト
     */
    public function evaluate(string $expression, array $context): bool
    {
        try {
            return (bool) $this->expressionLanguage->evaluate($expression, $context);
        } catch (\Exception $e) {
            return false;
        }
    }
}
```

### 使用例

```php
<?php

class DiscountService
{
    public function __construct(
        private DiscountRuleEvaluator $evaluator,
        private DiscountRuleRepository $ruleRepository
    ) {
    }

    public function calculateDiscount(Cart $cart): int
    {
        $context = [
            'subtotal' => $cart->getTotal(),
            'itemCount' => $cart->getQuantity(),
            'customerRank' => $cart->getCustomer()?->getRank() ?? 'guest',
        ];

        $discount = 0;
        foreach ($this->ruleRepository->findActive() as $rule) {
            // 管理画面で設定した条件式: "subtotal >= 10000 and customerRank == 'gold'"
            if ($this->evaluator->evaluate($rule->getCondition(), $context)) {
                $discount += $rule->getDiscountAmount();
            }
        }

        return $discount;
    }
}
```

## 8. Serializer - データ変換

CSV/JSON のインポート・エクスポートに活用できます。

### エンティティの設定

```php
<?php

namespace Plugin\YourPlugin\Entity;

use Symfony\Component\Serializer\Annotation\Groups;
use Symfony\Component\Serializer\Annotation\SerializedName;

class Product
{
    #[Groups(['export', 'api'])]
    private ?int $id = null;

    #[Groups(['export', 'api', 'import'])]
    #[SerializedName('商品名')]
    private ?string $name = null;

    #[Groups(['export', 'api', 'import'])]
    #[SerializedName('価格')]
    private ?int $price = null;

    #[Groups(['export'])]
    #[SerializedName('登録日')]
    private ?\DateTimeInterface $createDate = null;
}
```

### エクスポートサービス

```php
<?php

namespace Plugin\YourPlugin\Service;

use Symfony\Component\Serializer\SerializerInterface;
use Symfony\Component\Serializer\Encoder\CsvEncoder;

class ProductExportService
{
    public function __construct(
        private SerializerInterface $serializer,
        private ProductRepository $productRepository
    ) {
    }

    public function exportToCsv(): string
    {
        $products = $this->productRepository->findAll();

        return $this->serializer->serialize($products, 'csv', [
            'groups' => ['export'],
            CsvEncoder::DELIMITER_KEY => ',',
            CsvEncoder::ENCLOSURE_KEY => '"',
        ]);
    }

    public function exportToJson(): string
    {
        $products = $this->productRepository->findAll();

        return $this->serializer->serialize($products, 'json', [
            'groups' => ['api'],
            'json_encode_options' => JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT,
        ]);
    }

    public function importFromCsv(string $csvContent): array
    {
        return $this->serializer->deserialize($csvContent, Product::class . '[]', 'csv', [
            'groups' => ['import'],
        ]);
    }
}
```

## 9. Security Voter - 細かいアクセス制御

商品やカテゴリへのアクセス制限を実装できます。

### Voterクラス

```php
<?php

namespace Plugin\YourPlugin\Security\Voter;

use Eccube\Entity\Product;
use Eccube\Entity\Customer;
use Symfony\Component\Security\Core\Authentication\Token\TokenInterface;
use Symfony\Component\Security\Core\Authorization\Voter\Voter;

class ProductVoter extends Voter
{
    public const VIEW = 'PRODUCT_VIEW';
    public const PURCHASE = 'PRODUCT_PURCHASE';

    protected function supports(string $attribute, mixed $subject): bool
    {
        return in_array($attribute, [self::VIEW, self::PURCHASE])
            && $subject instanceof Product;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        /** @var Product $product */
        $product = $subject;
        $user = $token->getUser();

        // 会員限定商品のチェック
        if ($product->isMemberOnly() && !$user instanceof Customer) {
            return false;
        }

        return match ($attribute) {
            self::VIEW => $this->canView($product, $user),
            self::PURCHASE => $this->canPurchase($product, $user),
            default => false,
        };
    }

    private function canView(Product $product, mixed $user): bool
    {
        // 公開中の商品は誰でも閲覧可能
        if ($product->isPublic()) {
            return true;
        }

        // 非公開商品はゴールド会員以上のみ
        if ($user instanceof Customer) {
            return $user->getRank() === 'gold' || $user->getRank() === 'platinum';
        }

        return false;
    }

    private function canPurchase(Product $product, mixed $user): bool
    {
        if (!$this->canView($product, $user)) {
            return false;
        }

        // 購入は会員のみ
        return $user instanceof Customer;
    }
}
```

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Controller;

use Symfony\Component\Security\Core\Authorization\AuthorizationCheckerInterface;

class ProductController extends AbstractController
{
    public function __construct(
        private AuthorizationCheckerInterface $authChecker
    ) {
    }

    public function detail(Product $product): Response
    {
        // 閲覧権限チェック
        if (!$this->authChecker->isGranted(ProductVoter::VIEW, $product)) {
            throw $this->createAccessDeniedException('この商品を閲覧する権限がありません。');
        }

        $canPurchase = $this->authChecker->isGranted(ProductVoter::PURCHASE, $product);

        return $this->render('@YourPlugin/Product/detail.twig', [
            'Product' => $product,
            'canPurchase' => $canPurchase,
        ]);
    }
}
```

## 10. Service Subscriber - 遅延読み込み

必要な時だけサービスを読み込み、パフォーマンスを向上させます。

### Service Subscriberの実装

```php
<?php

namespace Plugin\YourPlugin\Service;

use Eccube\Service\MailService;
use Eccube\Service\PurchaseFlow\PurchaseFlow;
use Psr\Container\ContainerInterface;
use Symfony\Contracts\Service\ServiceSubscriberInterface;

class OrderProcessService implements ServiceSubscriberInterface
{
    public function __construct(
        private ContainerInterface $locator
    ) {
    }

    public static function getSubscribedServices(): array
    {
        return [
            // 必要な時だけインスタンス化される
            MailService::class,
            PurchaseFlow::class,
            'payment.service' => PaymentService::class,
            '?logger' => LoggerInterface::class, // オプショナル
        ];
    }

    public function process(Order $order): void
    {
        // PurchaseFlowはここで初めてインスタンス化
        $purchaseFlow = $this->locator->get(PurchaseFlow::class);
        $purchaseFlow->commit($order, new PurchaseContext());

        // 条件付きでメールサービスを取得
        if ($order->shouldSendMail()) {
            $mailService = $this->locator->get(MailService::class);
            $mailService->sendOrderMail($order);
        }

        // エイリアスで取得
        $paymentService = $this->locator->get('payment.service');
        $paymentService->capture($order);
    }

    public function log(string $message): void
    {
        // オプショナルなサービスの安全な取得
        if ($this->locator->has('logger')) {
            $this->locator->get('logger')->info($message);
        }
    }
}
```

### サービス定義

```yaml
# app/Plugin/YourPlugin/Resource/config/services.yaml
services:
    Plugin\YourPlugin\Service\OrderProcessService:
        arguments:
            $locator: '@Psr\Container\ContainerInterface'
        tags:
            - { name: 'container.service_subscriber' }
```

## まとめ

| 技術 | 主な用途 |
|------|----------|
| Workflow | 受注・会員ステータスの状態管理 |
| Messenger | メール送信・外部連携の非同期処理 |
| Rate Limiter | ログイン・API呼び出しの回数制限 |
| Lock | 在庫更新の排他制御 |
| HttpClient | 決済・配送サービスとの連携 |
| Validator | 商品コード重複などの独自検証 |
| ExpressionLanguage | 動的な割引・送料ルール |
| Serializer | CSV/JSONインポート・エクスポート |
| Security Voter | 商品・カテゴリへのアクセス制御 |
| Service Subscriber | サービスの遅延読み込み |

これらの技術を組み合わせることで、より堅牢で拡張性の高いプラグインを開発できます。Symfony の公式ドキュメントも併せて参照してください。

## 参考リンク

- [Symfony Documentation](https://symfony.com/doc/current/index.html)
- [EC-CUBE 4 開発者向けドキュメント](https://doc4.ec-cube.net/)
