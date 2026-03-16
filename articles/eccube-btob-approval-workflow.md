---
title: "EC-CUBE 4でBtoB EC機能を実装する - 承認ワークフローと企業アカウント管理"
emoji: "🏢"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "btob"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

BtoB EC市場は514兆円を超え、企業間取引のオンライン化が急速に進んでいます。EC-CUBEでもBtoB向けプラグインが充実してきましたが、競合のBtoB専用ECサービス（Bカート、ecbeing BtoB、AladdinECなど）と比較すると、まだ不足している機能があります。

この記事では、EC-CUBEの既存B2B機能を整理した上で、不足している「多段階承認ワークフロー」と「親子アカウント（企業アカウント管理）」の実装アイデアを解説します。

## EC-CUBEの既存B2B機能

まず、プラグインを含めたEC-CUBEの現状を整理します。

### プラグインでカバーされている機能

| 機能 | プラグイン例 |
|------|-------------|
| 会員グループ管理 | [会員グループ管理プラグイン](https://www.ec-cube.net/products/detail.php?product_id=2439) |
| グループ別商品・カテゴリ表示制限 | 同上 |
| グループ別価格・掛率設定 | [会員グループ価格管理アドオン](https://www.ec-cube.net/products/detail.php?product_id=2440) |
| 見積機能 | 見積プラグイン各種 |
| 掛け払い決済 | EC-CUBE Payment Plus B2B |
| 会員制サイト（ログイン必須） | 会員制サイトプラグイン |

これらを組み合わせることで、基本的なBtoB ECサイトは構築可能です。

### 競合サービスにあってEC-CUBEにない機能

| 機能 | 概要 | 競合での対応 |
|------|------|-------------|
| **多段階承認ワークフロー** | 金額や商品に応じた承認フロー | Bカート、ecbeing等で標準機能 |
| **親子アカウント管理** | 企業配下に複数担当者を管理 | 多くのB2B ECで標準機能 |
| 与信・取引限度額管理 | 企業ごとの与信枠設定 | 一部サービスで対応 |
| 購買予算管理 | 部門別予算の設定と管理 | 一部サービスで対応 |

特に「多段階承認ワークフロー」と「親子アカウント管理」は、中堅以上の企業との取引で必須となる機能です。

## 実装1: 親子アカウント（企業アカウント管理）

### 概要

BtoB取引では、1つの企業内に複数の担当者が存在します。

- 購買担当者（発注を行う）
- 承認者（発注を承認する）
- 経理担当者（請求書を確認する）
- 管理者（担当者の追加・削除を行う）

これを実現するため、「企業（Company）」エンティティを作成し、既存のCustomerと紐付けます。

### Entityの設計

```php
<?php
// app/Entity/Company.php

namespace Customize\Entity;

use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;
use Eccube\Entity\Customer;

#[ORM\Entity]
#[ORM\Table(name: 'plg_company')]
class Company
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name;

    #[ORM\Column(type: 'string', length: 255, nullable: true)]
    private ?string $corporateNumber = null; // 法人番号

    #[ORM\Column(type: 'integer', options: ['default' => 0])]
    private int $creditLimit = 0; // 与信限度額

    #[ORM\Column(type: 'string', length: 50, nullable: true)]
    private ?string $paymentTerms = null; // 支払条件（月末締め翌月払い等）

    #[ORM\OneToMany(targetEntity: CompanyMember::class, mappedBy: 'company', cascade: ['persist', 'remove'])]
    private Collection $members;

    public function __construct()
    {
        $this->members = new ArrayCollection();
    }

    // getter/setter省略
}
```

```php
<?php
// app/Entity/CompanyMember.php

namespace Customize\Entity;

use Doctrine\ORM\Mapping as ORM;
use Eccube\Entity\Customer;

#[ORM\Entity]
#[ORM\Table(name: 'plg_company_member')]
class CompanyMember
{
    public const ROLE_ADMIN = 'admin';       // 管理者
    public const ROLE_APPROVER = 'approver'; // 承認者
    public const ROLE_BUYER = 'buyer';       // 購買担当
    public const ROLE_VIEWER = 'viewer';     // 閲覧のみ

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Company::class, inversedBy: 'members')]
    #[ORM\JoinColumn(nullable: false)]
    private Company $company;

    #[ORM\ManyToOne(targetEntity: Customer::class)]
    #[ORM\JoinColumn(nullable: false)]
    private Customer $customer;

    #[ORM\Column(type: 'string', length: 20)]
    private string $role = self::ROLE_BUYER;

    #[ORM\Column(type: 'integer', nullable: true)]
    private ?int $orderLimit = null; // 発注上限金額（この金額以上は承認必要）

    #[ORM\Column(type: 'boolean', options: ['default' => true])]
    private bool $isActive = true;

    // getter/setter省略

    public function canApprove(): bool
    {
        return in_array($this->role, [self::ROLE_ADMIN, self::ROLE_APPROVER], true);
    }

    public function canOrder(): bool
    {
        return in_array($this->role, [self::ROLE_ADMIN, self::ROLE_APPROVER, self::ROLE_BUYER], true);
    }
}
```

### CustomerへのTraitによる拡張

```php
<?php
// app/Entity/CustomerTrait.php

namespace Customize\Entity;

use Doctrine\ORM\Mapping as ORM;

trait CustomerTrait
{
    #[ORM\OneToOne(targetEntity: CompanyMember::class, mappedBy: 'customer')]
    private ?CompanyMember $companyMember = null;

    public function getCompanyMember(): ?CompanyMember
    {
        return $this->companyMember;
    }

    public function getCompany(): ?Company
    {
        return $this->companyMember?->getCompany();
    }

    public function isCompanyAdmin(): bool
    {
        return $this->companyMember?->getRole() === CompanyMember::ROLE_ADMIN;
    }
}
```

## 実装2: 多段階承認ワークフロー

### 概要

企業の購買プロセスでは、金額に応じた承認フローが必要です。

例：
- 10万円未満：承認不要
- 10万円以上50万円未満：課長承認
- 50万円以上：部長承認

### Entityの設計

```php
<?php
// app/Entity/ApprovalFlow.php

namespace Customize\Entity;

use Doctrine\Common\Collections\ArrayCollection;
use Doctrine\Common\Collections\Collection;
use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'plg_approval_flow')]
class ApprovalFlow
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Company::class)]
    #[ORM\JoinColumn(nullable: false)]
    private Company $company;

    #[ORM\Column(type: 'string', length: 255)]
    private string $name; // フロー名（例：「標準承認フロー」）

    #[ORM\Column(type: 'integer')]
    private int $minAmount = 0; // 適用下限金額

    #[ORM\Column(type: 'integer', nullable: true)]
    private ?int $maxAmount = null; // 適用上限金額（nullは上限なし）

    #[ORM\OneToMany(targetEntity: ApprovalStep::class, mappedBy: 'flow', cascade: ['persist', 'remove'])]
    #[ORM\OrderBy(['stepOrder' => 'ASC'])]
    private Collection $steps;

    #[ORM\Column(type: 'boolean', options: ['default' => true])]
    private bool $isActive = true;

    public function __construct()
    {
        $this->steps = new ArrayCollection();
    }

    public function isApplicable(int $amount): bool
    {
        if ($amount < $this->minAmount) {
            return false;
        }
        if ($this->maxAmount !== null && $amount > $this->maxAmount) {
            return false;
        }
        return true;
    }
}
```

```php
<?php
// app/Entity/ApprovalStep.php

namespace Customize\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'plg_approval_step')]
class ApprovalStep
{
    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: ApprovalFlow::class, inversedBy: 'steps')]
    #[ORM\JoinColumn(nullable: false)]
    private ApprovalFlow $flow;

    #[ORM\Column(type: 'integer')]
    private int $stepOrder; // 承認順序

    #[ORM\Column(type: 'string', length: 255)]
    private string $name; // ステップ名（例：「課長承認」）

    #[ORM\Column(type: 'string', length: 20)]
    private string $approverRole; // 承認者の役割

    #[ORM\ManyToOne(targetEntity: CompanyMember::class)]
    private ?CompanyMember $specificApprover = null; // 特定の承認者（指定する場合）
}
```

```php
<?php
// app/Entity/OrderApproval.php

namespace Customize\Entity;

use Doctrine\ORM\Mapping as ORM;
use Eccube\Entity\Order;

#[ORM\Entity]
#[ORM\Table(name: 'plg_order_approval')]
class OrderApproval
{
    public const STATUS_PENDING = 'pending';   // 承認待ち
    public const STATUS_APPROVED = 'approved'; // 承認済み
    public const STATUS_REJECTED = 'rejected'; // 却下
    public const STATUS_CANCELLED = 'cancelled'; // キャンセル

    #[ORM\Id]
    #[ORM\GeneratedValue]
    #[ORM\Column(type: 'integer')]
    private ?int $id = null;

    #[ORM\ManyToOne(targetEntity: Order::class)]
    #[ORM\JoinColumn(nullable: false)]
    private Order $order;

    #[ORM\ManyToOne(targetEntity: ApprovalStep::class)]
    #[ORM\JoinColumn(nullable: false)]
    private ApprovalStep $step;

    #[ORM\Column(type: 'string', length: 20)]
    private string $status = self::STATUS_PENDING;

    #[ORM\ManyToOne(targetEntity: CompanyMember::class)]
    private ?CompanyMember $approvedBy = null;

    #[ORM\Column(type: 'datetime', nullable: true)]
    private ?\DateTimeInterface $approvedAt = null;

    #[ORM\Column(type: 'text', nullable: true)]
    private ?string $comment = null; // 承認・却下コメント

    #[ORM\Column(type: 'datetime')]
    private \DateTimeInterface $createdAt;

    public function __construct()
    {
        $this->createdAt = new \DateTimeImmutable();
    }
}
```

### 承認ワークフローサービス

```php
<?php
// app/Service/ApprovalWorkflowService.php

namespace Customize\Service;

use Customize\Entity\ApprovalFlow;
use Customize\Entity\ApprovalStep;
use Customize\Entity\CompanyMember;
use Customize\Entity\OrderApproval;
use Customize\Repository\ApprovalFlowRepository;
use Customize\Repository\OrderApprovalRepository;
use Doctrine\ORM\EntityManagerInterface;
use Eccube\Entity\Order;
use Eccube\Entity\Master\OrderStatus;
use Eccube\Repository\Master\OrderStatusRepository;

class ApprovalWorkflowService
{
    public function __construct(
        private EntityManagerInterface $entityManager,
        private ApprovalFlowRepository $approvalFlowRepository,
        private OrderApprovalRepository $orderApprovalRepository,
        private OrderStatusRepository $orderStatusRepository,
    ) {
    }

    /**
     * 注文に対して承認フローを開始する
     */
    public function startApprovalFlow(Order $order, CompanyMember $requester): void
    {
        $company = $requester->getCompany();
        $amount = (int) $order->getPaymentTotal();

        // 適用される承認フローを取得
        $flow = $this->approvalFlowRepository->findApplicableFlow($company, $amount);

        if ($flow === null) {
            // 承認フローなし = 即時確定
            return;
        }

        // 注文ステータスを「承認待ち」に変更
        $pendingStatus = $this->orderStatusRepository->find(OrderStatus::PENDING);
        $order->setOrderStatus($pendingStatus);

        // 最初のステップの承認レコードを作成
        $firstStep = $flow->getSteps()->first();
        if ($firstStep) {
            $this->createApprovalRequest($order, $firstStep);
        }

        $this->entityManager->flush();
    }

    /**
     * 承認処理
     */
    public function approve(
        OrderApproval $approval,
        CompanyMember $approver,
        ?string $comment = null
    ): void {
        $approval->setStatus(OrderApproval::STATUS_APPROVED);
        $approval->setApprovedBy($approver);
        $approval->setApprovedAt(new \DateTimeImmutable());
        $approval->setComment($comment);

        // 次のステップがあるかチェック
        $nextStep = $this->getNextStep($approval->getStep());

        if ($nextStep !== null) {
            // 次のステップの承認リクエストを作成
            $this->createApprovalRequest($approval->getOrder(), $nextStep);
        } else {
            // 全ステップ完了 = 注文確定
            $this->finalizeOrder($approval->getOrder());
        }

        $this->entityManager->flush();
    }

    /**
     * 却下処理
     */
    public function reject(
        OrderApproval $approval,
        CompanyMember $approver,
        string $comment
    ): void {
        $approval->setStatus(OrderApproval::STATUS_REJECTED);
        $approval->setApprovedBy($approver);
        $approval->setApprovedAt(new \DateTimeImmutable());
        $approval->setComment($comment);

        // 注文をキャンセル状態に
        $cancelStatus = $this->orderStatusRepository->find(OrderStatus::CANCEL);
        $approval->getOrder()->setOrderStatus($cancelStatus);

        $this->entityManager->flush();
    }

    private function createApprovalRequest(Order $order, ApprovalStep $step): void
    {
        $approval = new OrderApproval();
        $approval->setOrder($order);
        $approval->setStep($step);

        $this->entityManager->persist($approval);

        // TODO: 承認者にメール通知
    }

    private function getNextStep(ApprovalStep $currentStep): ?ApprovalStep
    {
        $flow = $currentStep->getFlow();
        $steps = $flow->getSteps();
        $currentOrder = $currentStep->getStepOrder();

        foreach ($steps as $step) {
            if ($step->getStepOrder() > $currentOrder) {
                return $step;
            }
        }

        return null;
    }

    private function finalizeOrder(Order $order): void
    {
        $newStatus = $this->orderStatusRepository->find(OrderStatus::NEW);
        $order->setOrderStatus($newStatus);
    }
}
```

### EventSubscriberで注文時に自動起動

```php
<?php
// app/EventSubscriber/OrderApprovalSubscriber.php

namespace Customize\EventSubscriber;

use Customize\Entity\CompanyMember;
use Customize\Service\ApprovalWorkflowService;
use Eccube\Event\EccubeEvents;
use Eccube\Event\EventArgs;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\Security\Core\Authentication\Token\Storage\TokenStorageInterface;

class OrderApprovalSubscriber implements EventSubscriberInterface
{
    public function __construct(
        private ApprovalWorkflowService $workflowService,
        private TokenStorageInterface $tokenStorage,
    ) {
    }

    public static function getSubscribedEvents(): array
    {
        return [
            EccubeEvents::FRONT_SHOPPING_COMPLETE_INITIALIZE => 'onShoppingComplete',
        ];
    }

    public function onShoppingComplete(EventArgs $event): void
    {
        $order = $event->getArgument('Order');
        $customer = $this->tokenStorage->getToken()?->getUser();

        if (!$customer instanceof \Eccube\Entity\Customer) {
            return;
        }

        $companyMember = $customer->getCompanyMember();

        if ($companyMember === null) {
            // 企業アカウントでない場合はスキップ
            return;
        }

        // 承認ワークフローを開始
        $this->workflowService->startApprovalFlow($order, $companyMember);
    }
}
```

## マイページへの承認画面追加

### Controller

```php
<?php
// app/Controller/Mypage/ApprovalController.php

namespace Customize\Controller\Mypage;

use Customize\Entity\OrderApproval;
use Customize\Repository\OrderApprovalRepository;
use Customize\Service\ApprovalWorkflowService;
use Eccube\Controller\AbstractController;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Template;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Annotation\Route;

class ApprovalController extends AbstractController
{
    public function __construct(
        private OrderApprovalRepository $approvalRepository,
        private ApprovalWorkflowService $workflowService,
    ) {
    }

    #[Route('/mypage/approval', name: 'mypage_approval', methods: ['GET'])]
    #[Template('@user_data/mypage/approval_list.twig')]
    public function index(): array
    {
        $customer = $this->getUser();
        $companyMember = $customer->getCompanyMember();

        if ($companyMember === null || !$companyMember->canApprove()) {
            throw $this->createAccessDeniedException();
        }

        $pendingApprovals = $this->approvalRepository
            ->findPendingByCompany($companyMember->getCompany());

        return [
            'approvals' => $pendingApprovals,
        ];
    }

    #[Route('/mypage/approval/{id}/approve', name: 'mypage_approval_approve', methods: ['POST'])]
    public function approve(Request $request, OrderApproval $approval): Response
    {
        $customer = $this->getUser();
        $companyMember = $customer->getCompanyMember();

        if (!$companyMember->canApprove()) {
            throw $this->createAccessDeniedException();
        }

        $comment = $request->request->get('comment');
        $this->workflowService->approve($approval, $companyMember, $comment);

        $this->addFlash('success', '承認しました。');

        return $this->redirectToRoute('mypage_approval');
    }

    #[Route('/mypage/approval/{id}/reject', name: 'mypage_approval_reject', methods: ['POST'])]
    public function reject(Request $request, OrderApproval $approval): Response
    {
        $customer = $this->getUser();
        $companyMember = $customer->getCompanyMember();

        if (!$companyMember->canApprove()) {
            throw $this->createAccessDeniedException();
        }

        $comment = $request->request->get('comment');

        if (empty($comment)) {
            $this->addFlash('error', '却下理由を入力してください。');
            return $this->redirectToRoute('mypage_approval');
        }

        $this->workflowService->reject($approval, $companyMember, $comment);

        $this->addFlash('warning', '却下しました。');

        return $this->redirectToRoute('mypage_approval');
    }
}
```

### Twigテンプレート

```twig
{# app/template/user_data/mypage/approval_list.twig #}

{% extends 'Mypage/index.twig' %}

{% block main %}
<h2>承認待ち一覧</h2>

{% if approvals is empty %}
    <p>承認待ちの注文はありません。</p>
{% else %}
    <table class="table">
        <thead>
            <tr>
                <th>注文番号</th>
                <th>申請者</th>
                <th>金額</th>
                <th>申請日</th>
                <th>操作</th>
            </tr>
        </thead>
        <tbody>
        {% for approval in approvals %}
            <tr>
                <td>{{ approval.order.orderNo }}</td>
                <td>{{ approval.order.customer.name01 }} {{ approval.order.customer.name02 }}</td>
                <td>{{ approval.order.paymentTotal|price }}</td>
                <td>{{ approval.createdAt|date('Y/m/d H:i') }}</td>
                <td>
                    <form action="{{ url('mypage_approval_approve', {id: approval.id}) }}" method="post" style="display: inline;">
                        <button type="submit" class="btn btn-success btn-sm">承認</button>
                    </form>
                    <button type="button" class="btn btn-danger btn-sm"
                            onclick="showRejectModal({{ approval.id }})">却下</button>
                </td>
            </tr>
        {% endfor %}
        </tbody>
    </table>
{% endif %}

{# 却下モーダル #}
<div id="rejectModal" class="modal" style="display: none;">
    <form id="rejectForm" method="post">
        <label>却下理由（必須）</label>
        <textarea name="comment" required></textarea>
        <button type="submit" class="btn btn-danger">却下する</button>
        <button type="button" onclick="closeRejectModal()">キャンセル</button>
    </form>
</div>

<script>
function showRejectModal(id) {
    document.getElementById('rejectForm').action = '{{ url('mypage_approval_reject', {id: '__ID__'}) }}'.replace('__ID__', id);
    document.getElementById('rejectModal').style.display = 'block';
}
function closeRejectModal() {
    document.getElementById('rejectModal').style.display = 'none';
}
</script>
{% endblock %}
```

## まとめ

この記事では、EC-CUBEにおけるBtoB EC機能の現状を整理し、不足している「親子アカウント管理」と「多段階承認ワークフロー」の実装アイデアを紹介しました。

### 実装のポイント

1. **親子アカウント管理**: Company エンティティを作成し、CustomerとCompanyMemberで紐付ける
2. **多段階承認**: ApprovalFlow/ApprovalStep/OrderApprovalの3つのエンティティで柔軟なワークフローを実現
3. **EventSubscriber**: 注文完了時に自動で承認フローを開始

### 発展的な機能

本記事で紹介した基本実装をベースに、以下の機能も追加できます：

- メール通知（承認依頼・承認完了・却下通知）
- 承認履歴の監査ログ
- 代理承認機能
- 承認期限と自動エスカレーション
- Slack/Teams連携

BtoB ECの需要は今後も拡大が予想されます。EC-CUBEの柔軟なカスタマイズ性を活かして、企業のニーズに合ったBtoB ECサイトを構築してみてください。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
