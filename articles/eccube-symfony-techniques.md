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

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Service;

use Eccube\Repository\ProductClassRepository;
use Doctrine\ORM\EntityManagerInterface;
use Symfony\Component\Lock\LockFactory;
use Symfony\Component\Lock\Store\FlockStore;

class InventoryService
{
    private LockFactory $lockFactory;

    public function __construct(
        private ProductClassRepository $productClassRepository,
        private EntityManagerInterface $entityManager
    ) {
        // ファイルベースのロックを使用
        $store = new FlockStore();
        $this->lockFactory = new LockFactory($store);
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

use Eccube\Repository\ProductClassRepository;
use Symfony\Component\Validator\Constraint;
use Symfony\Component\Validator\ConstraintValidator;

class UniqueProductCodeValidator extends ConstraintValidator
{
    public function __construct(
        private ProductClassRepository $productClassRepository
    ) {
    }

    public function validate(mixed $value, Constraint $constraint): void
    {
        if (null === $value || '' === $value) {
            return;
        }

        $existingProductClass = $this->productClassRepository->findOneBy(['code' => $value]);

        // 編集中の規格は除外
        if ($existingProductClass && $existingProductClass->getId() !== $constraint->excludeId) {
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

use Eccube\Form\Type\Admin\ProductClassEditType;
use Plugin\YourPlugin\Validator\Constraints\UniqueProductCode;
use Symfony\Component\Form\AbstractTypeExtension;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\FormEvent;
use Symfony\Component\Form\FormEvents;

class ProductClassEditTypeExtension extends AbstractTypeExtension
{
    public static function getExtendedTypes(): iterable
    {
        yield ProductClassEditType::class;
    }

    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder->addEventListener(FormEvents::PRE_SET_DATA, function (FormEvent $event) {
            $productClass = $event->getData();
            $form = $event->getForm();

            // 既存のcodeフィールドにカスタム制約を追加
            $codeField = $form->get('code');
            $options = $codeField->getConfig()->getOptions();

            $options['constraints'][] = new UniqueProductCode(
                excludeId: $productClass?->getId()
            );

            $form->add('code', $codeField->getConfig()->getType()->getInnerType()::class, $options);
        });
    }
}
```

## 7. ExpressionLanguage - 動的条件評価

条件式を文字列で記述し、動的に評価できます。

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Service;

use Eccube\Entity\Cart;
use Symfony\Component\ExpressionLanguage\ExpressionLanguage;

class ShippingFeeCalculator
{
    private ExpressionLanguage $expressionLanguage;

    public function __construct()
    {
        $this->expressionLanguage = new ExpressionLanguage();
    }

    /**
     * カートの内容に応じて送料無料かどうかを判定
     */
    public function isFreeShipping(Cart $cart): bool
    {
        $context = [
            'total' => $cart->getTotalPrice(),
            'quantity' => $cart->getTotalQuantity(),
        ];

        // 合計10,000円以上、または5個以上で送料無料
        return $this->expressionLanguage->evaluate(
            'total >= 10000 or quantity >= 5',
            $context
        );
    }
}
```

## 8. Serializer - データ変換

カスタム Normalizer を使って、コアエンティティを任意の形式に変換できます。

### カスタム Normalizer

```php
<?php

namespace Plugin\YourPlugin\Serializer\Normalizer;

use Eccube\Entity\Product;
use Symfony\Component\Serializer\Normalizer\NormalizerInterface;

class ProductNormalizer implements NormalizerInterface
{
    public function normalize(mixed $object, ?string $format = null, array $context = []): array
    {
        /** @var Product $object */
        return [
            'id' => $object->getId(),
            '商品名' => $object->getName(),
            '商品コード' => $object->getCodeMin(),
            '価格' => $object->getPrice02Min(),
            '登録日' => $object->getCreateDate()->format('Y-m-d'),
        ];
    }

    public function supportsNormalization(mixed $data, ?string $format = null, array $context = []): bool
    {
        return $data instanceof Product;
    }

    public function getSupportedTypes(?string $format): array
    {
        return [Product::class => true];
    }
}
```

### エクスポートサービス

```php
<?php

namespace Plugin\YourPlugin\Service;

use Eccube\Repository\ProductRepository;
use Symfony\Component\Serializer\Encoder\CsvEncoder;
use Symfony\Component\Serializer\Serializer;
use Plugin\YourPlugin\Serializer\Normalizer\ProductNormalizer;

class ProductExportService
{
    public function __construct(
        private ProductRepository $productRepository
    ) {
    }

    public function exportToCsv(): string
    {
        $serializer = new Serializer(
            [new ProductNormalizer()],
            [new CsvEncoder()]
        );

        $products = $this->productRepository->findAll();

        return $serializer->serialize($products, 'csv');
    }
}
```

## 9. Security Voter - 購入制限

会員のみ購入可能な商品など、購入制限を実装できます。

### Voterクラス

```php
<?php

namespace Plugin\YourPlugin\Security\Voter;

use Eccube\Entity\Product;
use Eccube\Entity\Customer;
use Symfony\Component\Security\Core\Authentication\Token\TokenInterface;
use Symfony\Component\Security\Core\Authorization\Voter\Voter;

class ProductPurchaseVoter extends Voter
{
    public const PURCHASE = 'PRODUCT_PURCHASE';

    protected function supports(string $attribute, mixed $subject): bool
    {
        return $attribute === self::PURCHASE && $subject instanceof Product;
    }

    protected function voteOnAttribute(string $attribute, mixed $subject, TokenInterface $token): bool
    {
        $user = $token->getUser();

        // 会員のみ購入可能
        return $user instanceof Customer;
    }
}
```

### 使用例

```php
<?php

namespace Plugin\YourPlugin\Controller;

use Eccube\Controller\AbstractController;
use Eccube\Entity\Product;
use Plugin\YourPlugin\Security\Voter\ProductPurchaseVoter;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;
use Symfony\Component\Security\Core\Authorization\AuthorizationCheckerInterface;

class ProductController extends AbstractController
{
    public function __construct(
        private AuthorizationCheckerInterface $authChecker
    ) {
    }

    #[Route(path: '/plugin/product/{id}', name: 'plugin_product_detail')]
    public function detail(Product $product): Response
    {
        $canPurchase = $this->authChecker->isGranted(ProductPurchaseVoter::PURCHASE, $product);

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

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
