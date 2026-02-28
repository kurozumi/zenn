---
title: "EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理"
emoji: "🔄"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE 4では、受注ステータスの遷移管理にSymfony Workflow Componentを採用しています。この記事では、OrderStateMachineの仕組みを詳しく解説し、プラグインでの活用方法を紹介します。

## Symfony Workflow Componentとは

Symfony Workflow Componentは、**状態遷移**を管理するためのコンポーネントです。「ある状態から別の状態への移動ルール」を定義し、不正な遷移を防ぐことができます。

### 日常の例：信号機

信号機を例に考えてみましょう。

```
[青] → [黄] → [赤] → [青] ...
```

- 青 → 黄 ✅ OK
- 青 → 赤 ❌ NG（いきなり赤にはならない）
- 赤 → 青 ✅ OK

このような「状態の変化ルール」をコードで管理するのがWorkflow Componentです。

### WorkflowとStateMachineの違い

Symfony Workflowには2つのタイプがあります。

| タイプ | 特徴 | 用途 |
|--------|------|------|
| **Workflow** | 複数の状態を同時に持てる | 承認フロー（複数人の承認待ちなど） |
| **StateMachine** | 常に1つの状態のみ | 受注ステータスなど |

EC-CUBEのOrderStateMachineは、名前の通り**StateMachine**タイプを使用しています。

## EC-CUBEの受注ステータス

EC-CUBEでは以下の受注ステータスが定義されています。

| ID | 定数名 | 表示名 |
|----|--------|--------|
| 1 | `NEW` | 新規受付 |
| 3 | `CANCEL` | 注文取消し |
| 4 | `IN_PROGRESS` | 対応中 |
| 5 | `DELIVERED` | 発送済み |
| 6 | `PAID` | 入金済み |
| 7 | `PENDING` | 決済処理中 |
| 8 | `PROCESSING` | 購入処理中 |
| 9 | `RETURNED` | 返品 |

## ステータス遷移図

EC-CUBEで定義されているステータス遷移は以下の通りです。

```
                    ┌──────────────┐
                    │   新規受付   │
                    │    (NEW)     │
                    └──────┬───────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
          ▼                ▼                ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ 入金済み │    │  対応中  │    │ 注文取消 │
    │  (PAID)  │    │(PROGRESS)│◄───│ (CANCEL) │
    └────┬─────┘    └────┬─────┘    └──────────┘
         │               │                ▲
         └───────┬───────┘                │
                 │                        │
                 ▼                        │
          ┌──────────┐                    │
          │ 発送済み │────────────────────┘
          │(DELIVERED)
          └────┬─────┘
               │
               ▼
          ┌──────────┐
          │   返品   │
          │(RETURNED)│
          └──────────┘
```

## OrderStateMachineの設定

EC-CUBEでは、`app/config/eccube/packages/order_state_machine.php` でステータス遷移を定義しています。

```php
<?php

use Eccube\Entity\Master\OrderStatus as Status;
use Eccube\Service\OrderStateMachineContext;

$container->loadFromExtension('framework', [
    'workflows' => [
        'order' => [
            'type' => 'state_machine',
            'marking_store' => [
                'type' => 'method',
            ],
            'supports' => [
                OrderStateMachineContext::class,
            ],
            'initial_marking' => (string) Status::NEW,
            'places' => [
                (string) Status::NEW,
                (string) Status::CANCEL,
                (string) Status::IN_PROGRESS,
                (string) Status::DELIVERED,
                (string) Status::PAID,
                (string) Status::PENDING,
                (string) Status::PROCESSING,
                (string) Status::RETURNED,
            ],
            'transitions' => [
                // 入金処理
                'pay' => [
                    'from' => (string) Status::NEW,
                    'to' => (string) Status::PAID,
                ],
                // 発送準備開始
                'packing' => [
                    'from' => [(string) Status::NEW, (string) Status::PAID],
                    'to' => (string) Status::IN_PROGRESS,
                ],
                // 注文キャンセル
                'cancel' => [
                    'from' => [(string) Status::NEW, (string) Status::IN_PROGRESS, (string) Status::PAID],
                    'to' => (string) Status::CANCEL,
                ],
                // キャンセル取消し
                'back_to_in_progress' => [
                    'from' => (string) Status::CANCEL,
                    'to' => (string) Status::IN_PROGRESS,
                ],
                // 発送
                'ship' => [
                    'from' => [(string) Status::NEW, (string) Status::PAID, (string) Status::IN_PROGRESS],
                    'to' => [(string) Status::DELIVERED],
                ],
                // 返品
                'return' => [
                    'from' => (string) Status::DELIVERED,
                    'to' => (string) Status::RETURNED,
                ],
                // 返品取消し
                'cancel_return' => [
                    'from' => (string) Status::RETURNED,
                    'to' => (string) Status::DELIVERED,
                ],
            ],
        ],
    ],
]);
```

### 設定の解説

| キー | 説明 |
|------|------|
| `type` | `state_machine`（1つの状態のみ持てる） |
| `marking_store` | 状態を保存/取得する方法 |
| `supports` | このワークフローが適用されるクラス |
| `initial_marking` | 初期状態 |
| `places` | 取りうるすべての状態 |
| `transitions` | 状態遷移の定義 |

## OrderStateMachineサービス

`OrderStateMachine`サービスは、受注ステータスの遷移を管理します。

### 主要なメソッド

```php
// 指定ステータスに遷移できるか判定
$canCancel = $orderStateMachine->can($Order, $CancelStatus);

// ステータスを遷移
$orderStateMachine->apply($Order, $CancelStatus);
```

### 遷移時のイベント処理

`OrderStateMachine`は`EventSubscriberInterface`を実装しており、遷移時に自動的に処理が実行されます。

```php
public static function getSubscribedEvents()
{
    return [
        // 遷移完了時
        'workflow.order.completed' => ['onCompleted'],
        // 入金処理時
        'workflow.order.transition.pay' => ['updatePaymentDate'],
        // キャンセル時
        'workflow.order.transition.cancel' => [['rollbackStock'], ['rollbackUsePoint']],
        // キャンセル取消し時
        'workflow.order.transition.back_to_in_progress' => [['commitStock'], ['commitUsePoint']],
        // 発送時
        'workflow.order.transition.ship' => [['commitAddPoint']],
        // 返品時
        'workflow.order.transition.return' => [['rollbackUsePoint'], ['rollbackAddPoint']],
        // 返品取消し時
        'workflow.order.transition.cancel_return' => [['commitUsePoint'], ['commitAddPoint']],
    ];
}
```

### 遷移ごとの処理内容

| 遷移 | 処理内容 |
|------|----------|
| `pay` | 入金日を設定 |
| `cancel` | 在庫を戻す、利用ポイントを戻す |
| `back_to_in_progress` | 在庫を減らす、利用ポイントを減らす |
| `ship` | 加算ポイントを付与 |
| `return` | 利用ポイントを戻す、加算ポイントを取り消す |
| `cancel_return` | 利用ポイントを減らす、加算ポイントを再付与 |

## プラグインでの活用

### 1. 遷移イベントをフックする

特定のステータス遷移時に独自の処理を追加できます。

```php
<?php
// app/Plugin/MyPlugin/EventSubscriber/OrderStateMachineSubscriber.php

namespace Plugin\MyPlugin\EventSubscriber;

use Eccube\Service\OrderStateMachineContext;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\Workflow\Event\Event;

class OrderStateMachineSubscriber implements EventSubscriberInterface
{
    public static function getSubscribedEvents()
    {
        return [
            // 発送時にメール送信
            'workflow.order.transition.ship' => 'onShip',
            // キャンセル時に外部APIへ通知
            'workflow.order.transition.cancel' => 'onCancel',
            // 任意の遷移完了時
            'workflow.order.completed' => 'onCompleted',
        ];
    }

    public function onShip(Event $event)
    {
        /** @var OrderStateMachineContext $context */
        $context = $event->getSubject();
        $Order = $context->getOrder();

        // 発送完了メールを送信するなど
        $this->sendShippingNotification($Order);
    }

    public function onCancel(Event $event)
    {
        /** @var OrderStateMachineContext $context */
        $context = $event->getSubject();
        $Order = $context->getOrder();

        // 外部システムにキャンセル通知
        $this->notifyExternalSystem($Order, 'cancelled');
    }

    public function onCompleted(Event $event)
    {
        /** @var OrderStateMachineContext $context */
        $context = $event->getSubject();
        $Order = $context->getOrder();

        // ステータス変更をログに記録
        $this->logStatusChange($Order, $context->getStatus());
    }
}
```

### 2. 遷移前の検証（Guard）

遷移を許可するかどうかを動的に制御できます。

```php
<?php
// app/Plugin/MyPlugin/EventSubscriber/OrderStateMachineGuard.php

namespace Plugin\MyPlugin\EventSubscriber;

use Eccube\Service\OrderStateMachineContext;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\Workflow\Event\GuardEvent;

class OrderStateMachineGuard implements EventSubscriberInterface
{
    public static function getSubscribedEvents()
    {
        return [
            // ship遷移のガード
            'workflow.order.guard.ship' => 'guardShip',
        ];
    }

    public function guardShip(GuardEvent $event)
    {
        /** @var OrderStateMachineContext $context */
        $context = $event->getSubject();
        $Order = $context->getOrder();

        // 支払いが完了していない場合は発送を禁止
        if ($Order->getPaymentDate() === null) {
            $event->setBlocked(true, '入金が確認されていません');
        }

        // 配送先が未設定の場合は発送を禁止
        if ($Order->getShippings()->isEmpty()) {
            $event->setBlocked(true, '配送先が設定されていません');
        }
    }
}
```

### 3. カスタムステータスと遷移の追加

プラグインで独自のステータスと遷移を追加する例です。

#### マイグレーションでステータスを追加

```php
<?php
// app/Plugin/MyPlugin/DoctrineMigrations/Version20240101000000.php

namespace Plugin\MyPlugin\DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20240101000000 extends AbstractMigration
{
    public function up(Schema $schema): void
    {
        // 「審査中」ステータスを追加（ID: 10）
        $this->addSql("INSERT INTO mtb_order_status (id, name, sort_no, discriminator_type) VALUES (10, '審査中', 10, 'orderstatus')");
    }

    public function down(Schema $schema): void
    {
        $this->addSql("DELETE FROM mtb_order_status WHERE id = 10");
    }
}
```

#### 遷移の追加（services.yamlで拡張）

```yaml
# app/Plugin/MyPlugin/Resource/config/services.yaml

# ワークフローの遷移を拡張
framework:
    workflows:
        order:
            transitions:
                # 審査開始
                start_review:
                    from: '1'  # NEW
                    to: '10'   # 審査中（カスタム）
                # 審査完了
                complete_review:
                    from: '10' # 審査中
                    to: '4'    # IN_PROGRESS
                # 審査却下
                reject_review:
                    from: '10' # 審査中
                    to: '3'    # CANCEL
```

### 4. Controllerでの使用例

```php
<?php

namespace Plugin\MyPlugin\Controller\Admin;

use Eccube\Controller\AbstractController;
use Eccube\Entity\Master\OrderStatus;
use Eccube\Entity\Order;
use Eccube\Service\OrderStateMachine;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Annotation\Route;

class OrderController extends AbstractController
{
    private OrderStateMachine $orderStateMachine;

    public function __construct(OrderStateMachine $orderStateMachine)
    {
        $this->orderStateMachine = $orderStateMachine;
    }

    /**
     * @Route("/admin/plugin/myorder/{id}/ship", name="my_plugin_admin_order_ship")
     */
    public function ship(Request $request, Order $Order)
    {
        $DeliveredStatus = $this->entityManager
            ->find(OrderStatus::class, OrderStatus::DELIVERED);

        // 遷移可能かチェック
        if (!$this->orderStateMachine->can($Order, $DeliveredStatus)) {
            $this->addError('この受注は発送処理できません');
            return $this->redirectToRoute('admin_order');
        }

        // ステータスを遷移
        try {
            $this->orderStateMachine->apply($Order, $DeliveredStatus);
            $this->entityManager->flush();
            $this->addSuccess('発送処理が完了しました');
        } catch (\Exception $e) {
            $this->addError('発送処理に失敗しました: ' . $e->getMessage());
        }

        return $this->redirectToRoute('admin_order');
    }
}
```

## イベント一覧

Symfony Workflowが発火するイベントの一覧です。

| イベント名 | タイミング |
|------------|------------|
| `workflow.order.guard.{transition}` | 遷移前の検証 |
| `workflow.order.leave.{place}` | 状態を離れる直前 |
| `workflow.order.transition.{transition}` | 遷移中 |
| `workflow.order.enter.{place}` | 新しい状態に入った直後 |
| `workflow.order.entered.{place}` | 新しい状態に入った後 |
| `workflow.order.completed` | 遷移完了後 |
| `workflow.order.announce.{transition}` | 遷移可能になったとき |

## デバッグ

現在の受注から遷移可能なステータスを確認できます。

```php
// Workflowサービスを直接使用
$workflow = $this->container->get('state_machine.order');
$context = new OrderStateMachineContext(
    (string) $Order->getOrderStatus()->getId(),
    $Order
);

// 可能な遷移を取得
$transitions = $workflow->getEnabledTransitions($context);
foreach ($transitions as $transition) {
    dump($transition->getName()); // 'pay', 'cancel', etc.
}
```

## まとめ

EC-CUBEのOrderStateMachineは、Symfony Workflow Componentを活用して以下を実現しています。

1. **不正な遷移の防止** - 定義されたルール以外の遷移を許可しない
2. **遷移時の自動処理** - 在庫戻し、ポイント処理などを自動実行
3. **拡張性** - プラグインで遷移のフック、ガード、カスタムステータスを追加可能

プラグインで活用する際は：

1. **イベントをフック** - `workflow.order.transition.{name}` で遷移時の処理を追加
2. **ガードで制御** - `workflow.order.guard.{name}` で遷移を動的に許可/禁止
3. **カスタムステータス** - マイグレーションと設定でステータスを追加

この仕組みを理解すれば、EC-CUBEの受注処理を柔軟にカスタマイズできます。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
