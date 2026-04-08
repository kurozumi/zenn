## 問題：ネストしたフォームで `POST_SUBMIT` の `isValid()` が信頼できない

EC-CUBE の注文フォームはネスト構造を持っています。`OrderType` が親フォームで、配送先ごとに `ShippingType` が子フォームとして含まれます。

```
OrderType（親）
  └→ ShippingType（子）
       └→ （プラグインが追加したフィールド）
```

Symfony のフォームは `submit()` が呼ばれると、子フォームから順番に `POST_SUBMIT` イベントを発火させます。**バリデーションはルートフォームの `POST_SUBMIT` 時にまとめて実行**されます。

```
POST_SUBMIT（子: ShippingType） ← ここではまだバリデーションが実行されていない
POST_SUBMIT（親: OrderType）    ← バリデーションはここで実行される
```

つまり `ShippingType` の `POST_SUBMIT` リスナー内で `$form->isValid()` を呼んでも、この時点ではバリデーションが走っていないため `true` が返ってしまいます。

現在の Symfony 6.4 に `POST_VALIDATE` イベントは存在しません（`FormEvents` に定義されているのは `PRE_SET_DATA`, `POST_SET_DATA`, `PRE_SUBMIT`, `SUBMIT`, `POST_SUBMIT` の5つのみ）。

### 現状の回避策

`POST_SUBMIT` の実行優先度を下げることで、バリデーションより後に処理を走らせる方法があります。

```php
// 優先度を負の値にすることでバリデーション後に実行させる（ハック的）
$builder->addEventListener(
    FormEvents::POST_SUBMIT,
    function (FormEvent $event) {
        // バリデーション後（優先度が低いため後に実行される）
        if ($event->getForm()->isValid()) {
            // 処理...
        }
    },
    -1000 // 優先度を下げる
);
```

ただしこれはバリデーションの実行タイミングに依存したハックであり、フォーム構造の変化で壊れる可能性があります。

---

## Symfony 8.1 での解決策：`ValidatorFormEvents::POST_VALIDATE`

Symfony PR [#47210](https://github.com/symfony/symfony/pull/47210) では、バリデーション専用のイベントが追加されます。

```php
// Symfony 8.1 以降（予定）
use Symfony\Component\Form\Extension\Validator\ValidatorFormEvents;
use Symfony\Component\Form\Extension\Validator\Event\PostValidateEvent;

$builder->addEventListener(
    ValidatorFormEvents::POST_VALIDATE,
    function (PostValidateEvent $event) { // FormEvent でも動作する（PR公式サンプルは FormEvent を使用）
        $form = $event->getForm();

        // バリデーション完了後なので isValid() が正確に機能する
        if ($form->isValid()) {
            // このフォームの全フィールドが有効な場合の処理
        }

        // ルートフォーム全体の有効性も確認できる
        if ($form->getRoot()->isValid()) {
            // 注文フォーム全体が有効な場合の処理
        }
    }
);
```

### 追加されるクラス・定数

| 追加物 | 内容 |
|---|---|
| `ValidatorFormEvents::PRE_VALIDATE` | バリデーション開始前のイベント文字列 |
| `ValidatorFormEvents::POST_VALIDATE` | バリデーション完了後のイベント文字列 |
| `PreValidateEvent` | `FormEvent` を継承した final クラス |
| `PostValidateEvent` | `FormEvent` を継承した final クラス |

既存の `FormEvents` クラスには追加されず、バリデーター拡張専用の `ValidatorFormEvents` クラスとして分離されます。

### イベント発火の順序

```
POST_SUBMIT（子: ShippingType）
POST_SUBMIT（親: OrderType）      ← バリデーション実行
POST_VALIDATE（子: ShippingType） ← 子フォームでも isValid() が正確
POST_VALIDATE（親: OrderType）
```


---

## EC-CUBEプラグインでの実践：現時点での推奨パターン

### パターン1：フォームバリデーションは Symfony Constraints に任せる

フィールドの入力値チェックは Constraints として宣言的に書き、ビジネスロジック検証は PurchaseFlow に追加します。`POST_SUBMIT` は「バリデーション結果を見て何かする」用途に使わないのが安全です。

```php
class ShippingTypeExtension extends AbstractTypeExtension
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder->add('gift_message', TextareaType::class, [
            'mapped' => false,
            'required' => false,
            'constraints' => [
                // バリデーションは Constraints で宣言的に書く
                new Length(['max' => 200]),
                // XSSの根本対策は出力時のエスケープ（Twigの {{ }} 自動エスケープ等）で行うこと
            // これはサーバー側での入力の補助的チェックに過ぎない
            new Regex(['pattern' => '/^[^<>]*$/', 'message' => 'HTMLタグは使用できません']),
            ],
        ]);

        // POST_SUBMIT はエンティティへのデータ転送のみに使う
        $builder->addEventListener(FormEvents::POST_SUBMIT, function (FormEvent $event) {
            $data = $event->getForm()->get('gift_message')->getData();
            $event->getData()?->setGiftMessage($data);
        });
    }

    public static function getExtendedTypes(): iterable
    {
        return [ShippingType::class];
    }
}
```

### パターン2：ビジネスロジック検証は PurchaseFlow に追加する

在庫・価格・配送に関するビジネスロジックの検証は PurchaseFlow の Processor として実装します。

```php
// app/Plugin/AcmePlugin/Service/PurchaseFlow/Validator/GiftMessageValidator.php
use Eccube\Service\PurchaseFlow\ItemValidator;
use Eccube\Service\PurchaseFlow\PurchaseContext;

class GiftMessageValidator extends ItemValidator
{
    protected function validate(ItemInterface $item, PurchaseContext $context): void
    {
        // ここにビジネスルールを書く
    }
}
```

---

## まとめ

| | 現在（Symfony 6.4） | PR #47210後（Symfony 8.1〜） |
|---|---|---|
| バリデーション後のイベント | なし（`POST_SUBMIT` で代替） | `ValidatorFormEvents::POST_VALIDATE` |
| 子フォームでの `isValid()` | 不正確（バリデーション前） | 正確（バリデーション後） |
| EC-CUBE コアの検証 | PurchaseFlow（FormEvents を使わない） | 変わらず |
| プラグインの推奨パターン | Constraints + PurchaseFlow Processor | 変わらず（`POST_VALIDATE` が選択肢として加わる） |

EC-CUBE のビジネスロジック検証は PurchaseFlow が担当しているため、`POST_VALIDATE` の恩恵を受けるのは主に「フォームバリデーション後に UI フィードバックを調整する」プラグインや、Symfony のフォームシステムに慣れた開発者が書くフォーム拡張コードです。

プラグインで `POST_SUBMIT` の `isValid()` が思った通りに動かないと感じたことがあれば、コメントで教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---