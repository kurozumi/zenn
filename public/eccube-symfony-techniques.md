---
title: 'EC-CUBEプラグインで使えるSymfonyの技術10選'
tags:
  - EC-CUBE
  - PHP
  - Symfony
private: false
updated_at: '2026-03-19T15:13:05+09:00'
id: 29391614825540b1a049
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBEプラグインで使えるSymfonyの技術10選](https://zenn.dev/kurozumi/articles/eccube-symfony-techniques)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBEプラグインで使えるSymfonyの技術10選](https://zenn.dev/kurozumi/articles/eccube-symfony-techniques)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
