# 100行のセッション管理が3行に。Symfony 7.4 Form FlowsでEC-CUBEの購入フローが変わる

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論：100行のセッション管理コードが、3行になった

**「あなたのEC-CUBEプロジェクトに、こんなコードはありませんか？」**

- セッションに一時データを保存
- ステップごとにリダイレクト制御
- 戻るボタンの状態復元
- バリデーションエラー時の再表示...

**これ、全部いらなくなります。**

Symfony 7.4で導入された**Form Flows**を使えば、上記の処理がすべて自動化されます。

```php
// Before: セッションに保存、リダイレクト、状態管理...約100行
// After: たった3行
$builder->addStep('shipping', ShippingType::class);
$builder->addStep('payment', PaymentType::class);
$builder->addStep('confirm', ConfirmType::class);
```

**これだけです。**

## 前提条件

- PHP 8.2以上
- Symfony 7.4以上
- EC-CUBE 4.3以上（将来的にSymfony 7.x対応時に利用可能）

## Form Flowsの基本

### AbstractFlowTypeを継承する

通常のフォームが`AbstractType`を継承するのに対し、Form Flowsでは`AbstractFlowType`を継承します。

```php
use Symfony\Component\Form\Flow\AbstractFlowType;
use Symfony\Component\Form\Flow\FormFlowBuilderInterface;
use Symfony\Component\OptionsResolver\OptionsResolver;

class CheckoutFlowType extends AbstractFlowType
{
    public function buildFormFlow(FormFlowBuilderInterface $builder, array $options): void
    {
        // ステップを順番に追加
        $builder->addStep('shipping', ShippingType::class);
        $builder->addStep('payment', PaymentType::class);
        $builder->addStep('confirm', ConfirmType::class);

        // ナビゲーションボタン
        $builder->add('navigator', CheckoutNavigatorType::class);
    }

    public function configureOptions(OptionsResolver $resolver): void
    {
        $resolver->setDefaults([
            'data_class' => CheckoutData::class,
            'step_property_path' => 'currentStep',
        ]);
    }
}
```

### 各ステップは通常のフォーム

各ステップは普通の`AbstractType`として定義します。既存のフォームをそのまま再利用できます。

```php
use Symfony\Component\Form\AbstractType;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\Extension\Core\Type\TextType;

class ShippingType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('name01', TextType::class, ['label' => '姓'])
            ->add('name02', TextType::class, ['label' => '名'])
            ->add('postal_code', TextType::class, ['label' => '郵便番号'])
            ->add('addr01', TextType::class, ['label' => '都道府県・市区町村'])
            ->add('addr02', TextType::class, ['label' => '番地・建物名']);
    }
}
```

### コントローラーでの使い方

通常のフォームと同じ感覚で使えます。

```php
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class CheckoutController extends AbstractController
{
    #[Route('/checkout', name: 'checkout')]
    public function __invoke(Request $request): Response
    {
        $checkoutData = new CheckoutData();

        $flow = $this->createForm(CheckoutFlowType::class, $checkoutData)
            ->handleRequest($request);

        // 全ステップ完了時
        if ($flow->isSubmitted() && $flow->isValid() && $flow->isFinished()) {
            // 注文処理を実行
            return $this->redirectToRoute('checkout_complete');
        }

        return $this->render('checkout/flow.html.twig', [
            'form' => $flow->getStepForm(), // 現在のステップのフォームのみ
        ]);
    }
}
```

**ポイント:**
- `isFinished()` で全ステップ完了を判定
- `getStepForm()` で現在のステップのフォームを取得

## EC-CUBEでの実装例

### データクラスの定義

```php
namespace Customize\Entity;

use Symfony\Component\Validator\Constraints as Assert;

class CheckoutData
{
    public string $currentStep = 'shipping';

    #[Assert\Valid(groups: ['shipping'])]
    public ShippingData $shipping;

    #[Assert\Valid(groups: ['payment'])]
    public PaymentData $payment;

    public function __construct()
    {
        $this->shipping = new ShippingData();
        $this->payment = new PaymentData();
    }
}

class ShippingData
{
    #[Assert\NotBlank(groups: ['shipping'], message: '姓を入力してください')]
    public string $name01 = '';

    #[Assert\NotBlank(groups: ['shipping'], message: '名を入力してください')]
    public string $name02 = '';

    #[Assert\NotBlank(groups: ['shipping'], message: '郵便番号を入力してください')]
    #[Assert\Regex(pattern: '/^\d{3}-?\d{4}$/', groups: ['shipping'], message: '郵便番号の形式が正しくありません')]
    public string $postal_code = '';

    #[Assert\NotBlank(groups: ['shipping'], message: '住所を入力してください')]
    public string $addr01 = '';

    public string $addr02 = '';
}

class PaymentData
{
    #[Assert\NotBlank(groups: ['payment'], message: '支払い方法を選択してください')]
    public ?int $paymentMethodId = null;
}
```

> **バリデーショングループの自動設定**
> Form Flowsでは、ステップ名（`shipping`、`payment`など）が自動的にバリデーショングループとして使用されます。各ステップで必要なバリデーションのみが実行されます。

### ナビゲーションボタンの定義

```php
namespace Customize\Form\Type;

use Symfony\Component\Form\AbstractType;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\Extension\Core\Type\Flow\NextFlowType;
use Symfony\Component\Form\Extension\Core\Type\Flow\PreviousFlowType;
use Symfony\Component\Form\Extension\Core\Type\Flow\FinishFlowType;

class CheckoutNavigatorType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('previous', PreviousFlowType::class, [
                'label' => '戻る',
                'attr' => ['class' => 'ec-blockBtn--cancel'],
            ])
            ->add('next', NextFlowType::class, [
                'label' => '次へ',
                'attr' => ['class' => 'ec-blockBtn--action'],
            ])
            ->add('finish', FinishFlowType::class, [
                'label' => '注文する',
                'attr' => ['class' => 'ec-blockBtn--action'],
            ]);
    }
}
```

| ボタンタイプ | 用途 |
|------------|------|
| `PreviousFlowType` | 前のステップに戻る |
| `NextFlowType` | 次のステップに進む |
| `FinishFlowType` | フローを完了する |
| `ResetFlowType` | 最初からやり直す |

### 支払い方法選択フォーム

```php
namespace Customize\Form\Type;

use Eccube\Repository\PaymentRepository;
use Symfony\Component\Form\AbstractType;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\Extension\Core\Type\ChoiceType;

class PaymentType extends AbstractType
{
    public function __construct(
        private PaymentRepository $paymentRepository,
    ) {
    }

    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $payments = $this->paymentRepository->findAllArray();

        $builder->add('paymentMethodId', ChoiceType::class, [
            'label' => '支払い方法',
            'choices' => array_column($payments, 'id', 'method'),
            'expanded' => true,
            'placeholder' => false,
        ]);
    }
}
```

### 確認画面フォーム

確認画面ではフォーム入力は不要ですが、ステップとして定義します。

```php
namespace Customize\Form\Type;

use Symfony\Component\Form\AbstractType;

class ConfirmType extends AbstractType
{
    // 確認画面なのでフォーム要素は不要
    // テンプレートでデータを表示するだけ
}
```

### Twigテンプレート

```twig
{# templates/checkout/flow.html.twig #}
{% extends 'default_frame.twig' %}

{% block main %}
<div class="ec-role">
    <div class="ec-pageHeader">
        <h1>ご注文手続き</h1>
    </div>

    {# ステップインジケーター #}
    <ol class="ec-progress">
        <li class="{{ form.vars.data.currentStep == 'shipping' ? 'is-complete' : '' }}">
            お届け先
        </li>
        <li class="{{ form.vars.data.currentStep == 'payment' ? 'is-complete' : '' }}">
            お支払い方法
        </li>
        <li class="{{ form.vars.data.currentStep == 'confirm' ? 'is-complete' : '' }}">
            ご注文確認
        </li>
    </ol>

    {{ form_start(form) }}

    {# 現在のステップに応じた表示 #}
    {% if form.vars.data.currentStep == 'shipping' %}
        <div class="ec-borderedDefs">
            {{ form_row(form.name01) }}
            {{ form_row(form.name02) }}
            {{ form_row(form.postal_code) }}
            {{ form_row(form.addr01) }}
            {{ form_row(form.addr02) }}
        </div>
    {% elseif form.vars.data.currentStep == 'payment' %}
        <div class="ec-borderedDefs">
            {{ form_row(form.paymentMethodId) }}
        </div>
    {% elseif form.vars.data.currentStep == 'confirm' %}
        {# 確認画面：入力内容を表示 #}
        <div class="ec-orderConfirm">
            <h2>お届け先</h2>
            <p>{{ form.vars.data.shipping.name01 }} {{ form.vars.data.shipping.name02 }}</p>
            <p>〒{{ form.vars.data.shipping.postal_code }}</p>
            <p>{{ form.vars.data.shipping.addr01 }} {{ form.vars.data.shipping.addr02 }}</p>
        </div>
    {% endif %}

    {# ナビゲーションボタン #}
    <div class="ec-registerRole__actions">
        {% if form.vars.data.currentStep != 'shipping' %}
            {{ form_widget(form.navigator.previous) }}
        {% endif %}

        {% if form.vars.data.currentStep == 'confirm' %}
            {{ form_widget(form.navigator.finish) }}
        {% else %}
            {{ form_widget(form.navigator.next) }}
        {% endif %}
    </div>

    {{ form_end(form) }}
</div>
{% endblock %}
```

## 条件付きステップ

特定の条件でステップをスキップすることも可能です。

```php
public function buildFormFlow(FormFlowBuilderInterface $builder, array $options): void
{
    $builder->addStep('shipping', ShippingType::class);
    $builder->addStep('payment', PaymentType::class);

    // 代引き選択時のみ表示するステップ（paymentの後に配置）
    $builder->addStep('cod_confirm', CodConfirmType::class, [
        'include_if' => function (CheckoutData $data): bool {
            // 支払い方法が代引き（ID: 4）の場合のみ表示
            return $data->payment->paymentMethodId === 4;
        },
    ]);

    $builder->addStep('confirm', ConfirmType::class);
}
```

## 従来の方法との比較

| 観点 | 従来（セッション管理） | Form Flows |
|------|---------------------|------------|
| コード量 | 多い | 少ない |
| 状態管理 | 手動でセッション操作 | 自動 |
| バリデーション | 各ステップで個別に実装 | グループで自動分離 |
| 戻る機能 | リダイレクト制御が必要 | ボタン1つで完了 |
| テスト | セッションのモックが必要 | フォームテストで完結 |

## EC-CUBEのPurchaseFlowとの組み合わせ

**「Form FlowsはPurchaseFlowを置き換えるの？」**

いいえ、**両者は異なる層を担当**しており、**組み合わせて使う**のが正解です。

### 役割の違い

| 層 | Form Flows | PurchaseFlow |
|----|------------|--------------|
| **担当** | UI/UX（フォーム遷移） | ビジネスロジック（集計・在庫・決済） |
| **処理内容** | ステップ管理、入力値の保持 | 金額計算、在庫チェック、ポイント処理 |
| **メソッド** | `addStep()`, `isFinished()` | `calculateAll()`, `commit()`, `rollback()` |

### PurchaseFlowの構造（おさらい）

EC-CUBEのPurchaseFlowは、集計処理とバリデーションを統一的に管理するフレームワークです。

```
PurchaseFlow
├── ItemValidator（明細単位の検証：価格変更、公開ステータス）
├── ItemHolderValidator（全体検証：在庫、販売制限数）
├── ItemHolderPreprocessor（送料・手数料追加）
├── DiscountProcessor（値引き処理）
├── ItemHolderPostValidator（最終検証：マイナスチェック）
└── PurchaseProcessor（在庫・ポイント更新）
```

### 組み合わせた実装例

Form FlowsでUI遷移を管理し、各ステップでPurchaseFlowを呼び出します。

```php
namespace Customize\Controller;

use Eccube\Service\PurchaseFlow\PurchaseContext;
use Eccube\Service\PurchaseFlow\PurchaseFlow;
use Symfony\Bundle\FrameworkBundle\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class CheckoutController extends AbstractController
{
    public function __construct(
        private PurchaseFlow $cartPurchaseFlow,
    ) {}

    #[Route('/checkout', name: 'checkout')]
    public function __invoke(Request $request, Cart $cart): Response
    {
        $checkoutData = new CheckoutData();

        // Form Flowsでフォーム遷移を管理
        $flow = $this->createForm(CheckoutFlowType::class, $checkoutData)
            ->handleRequest($request);

        // 各ステップでPurchaseFlowの集計処理を実行
        if ($flow->isSubmitted() && $flow->isValid()) {
            $context = new PurchaseContext($cart, $this->getUser());
            $result = $this->cartPurchaseFlow->validate($cart, $context);

            if ($result->hasError()) {
                // PurchaseFlowのエラーをフォームに追加
                foreach ($result->getErrors() as $error) {
                    $this->addFlash('eccube.front.error', $error->getMessage());
                }
                return $this->redirectToRoute('cart');
            }
        }

        // 全ステップ完了時：注文確定
        if ($flow->isFinished()) {
            // PurchaseFlowで確定処理
            $this->cartPurchaseFlow->commit($cart, $context);

            return $this->redirectToRoute('checkout_complete');
        }

        return $this->render('checkout/flow.html.twig', [
            'form' => $flow->getStepForm(),
            'Cart' => $cart,
        ]);
    }
}
```

### 各ステップでの処理分担

| ステップ | Form Flowsの役割 | PurchaseFlowの役割 |
|---------|-----------------|-------------------|
| **お届け先** | 住所入力フォームの表示・バリデーション | 送料の再計算 |
| **支払い方法** | 支払い選択フォームの表示 | 手数料の追加、支払い方法の妥当性検証 |
| **確認** | 入力内容の表示 | 最終的な金額集計、在庫の最終チェック |
| **完了** | 完了画面へリダイレクト | `commit()`で在庫減算、ポイント付与 |

> **ポイント**
> Form FlowsはEC-CUBEの**セッション管理とリダイレクト制御を置き換える**もので、**PurchaseFlowのビジネスロジックはそのまま活用**します。

## セキュリティに関する補足

> **実装時の注意点**
> - Twigの `{{ }}` 構文はデフォルトでHTMLエスケープされるため、XSS攻撃から保護されています
> - 支払い方法IDは、コントローラー側でデータベースに存在するか必ず確認してください
> - 入力フィールドには適切な文字数制限（`Assert\Length`）を設定することを推奨します

```php
// コントローラーでの支払い方法検証（重要）
if ($flow->isSubmitted() && $flow->isValid() && $flow->isFinished()) {
    // 支払い方法の存在確認
    $payment = $this->paymentRepository->find($checkoutData->payment->paymentMethodId);
    if (!$payment) {
        throw $this->createNotFoundException('無効な支払い方法です');
    }

    // 注文処理を実行
}
```

## まとめ

Symfony 7.4のForm Flowsは、マルチステップフォームの実装を劇的にシンプルにします。

- **宣言的なステップ定義**: `addStep()`でステップを追加するだけ
- **自動バリデーショングループ**: ステップ名がそのままバリデーショングループに
- **条件付きステップ**: `include_if`で動的なフロー制御
- **標準のナビゲーション**: 次へ/戻る/完了ボタンを標準提供

EC-CUBEがSymfony 7.x系に対応した際には、購入フローや会員登録フローの改善に活用できます。

## あなたの意見を聞かせてください

Form Flowsについて、こんな疑問はありませんか？

- **セッション vs Hidden Field**: Form Flowsは内部でHidden Fieldを使用します。大量のデータを扱う場合、セッションの方が適切なケースもある？
- **既存コードの移行コスト**: 既に動いているセッションベースの実装を、Form Flowsに移行する価値はある？
- **EC-CUBEのSymfony 7.x対応時期**: いつ頃対応されると思いますか？

ぜひコメントで教えてください。

## 参考リンク

- [New in Symfony 7.4: Multi-Step Forms](https://symfony.com/blog/new-in-symfony-7-4-multi-step-forms)
- [FormFlow Demo](https://github.com/yceruto/formflow-demo)
- [FormFlow: Build Stunning Multistep Forms (Speaker Deck)](https://speakerdeck.com/yceruto/formflow-build-stunning-multistep-forms)
- [購入フローのカスタマイズ - EC-CUBE 4 Developers](https://doc4.ec-cube.net/customize_service)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---