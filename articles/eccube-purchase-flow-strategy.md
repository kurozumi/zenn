---
title: "EC-CUBE 4のPurchaseFlowを理解する - ストラテジーパターンで実現する柔軟な購入フロー"
emoji: "🛒"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "デザインパターン"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE 4の購入処理を支える「PurchaseFlow」は、ストラテジーパターンを活用した柔軟な設計になっています。この記事では、デザインパターンの基礎から実際のカスタマイズ方法まで、順を追って解説します。

## ストラテジーパターンとは？

まず、PurchaseFlowを理解するために「ストラテジーパターン」について説明します。

### 日常の例で理解する

レストランの注文を考えてみましょう。お客さんが料理を注文すると、以下のような処理が必要です。

1. 在庫確認
2. 調理
3. 会計

通常のプログラミングでは、こうなりがちです：

```php
// 悪い例：処理が全部ベタ書き
class Order
{
    public function process()
    {
        // 在庫確認
        if ($this->item->stock < 1) {
            throw new Exception('在庫切れです');
        }

        // 調理（ラーメンの場合）
        $noodle = $this->boilNoodle();
        $soup = $this->makeSoup();
        $dish = $this->combine($noodle, $soup);

        // 会計
        $total = $this->item->price * 1.10;
        // ...
    }
}
```

この書き方の問題点は、**料理の種類が増えるたびにコードを修正する必要がある**ことです。

### ストラテジーパターンで解決

ストラテジーパターンでは、**処理を小さな部品（ストラテジー）に分割**します：

```php
// 良い例：処理を部品化
interface CookingStrategy
{
    public function cook(): Dish;
}

class RamenStrategy implements CookingStrategy
{
    public function cook(): Dish
    {
        // ラーメンの調理
    }
}

class CurryStrategy implements CookingStrategy
{
    public function cook(): Dish
    {
        // カレーの調理
    }
}

class Order
{
    private CookingStrategy $cookingStrategy;

    public function setCookingStrategy(CookingStrategy $strategy)
    {
        $this->cookingStrategy = $strategy;
    }

    public function process()
    {
        // どの料理でも同じ呼び出し方
        return $this->cookingStrategy->cook();
    }
}
```

これにより、**新しい料理を追加しても、既存のコードを変更せずに済みます**。

## EC-CUBEのPurchaseFlowとは

PurchaseFlowは、EC-CUBEの購入処理を担当するシステムです。カート投入から注文完了まで、様々な処理（在庫チェック、送料計算、ポイント計算など）を**部品化して組み合わせる**ストラテジーパターンで実装されています。

### 3種類のPurchaseFlow

EC-CUBEには、場面に応じた3つのPurchaseFlowがあります：

| フロー | 用途 | 使用場面 |
|--------|------|----------|
| `cart` | カートの処理 | 商品をカートに入れたとき |
| `shopping` | 購入フローの処理 | 購入手続き中 |
| `order` | 受注管理の処理 | 管理画面での受注編集 |

### 処理の全体像

```
PurchaseFlow
├── ItemValidator          # 商品1つずつをチェック
├── ItemHolderValidator    # カート/注文全体をチェック
├── ItemPreprocessor       # 商品1つずつを前処理
├── ItemHolderPreprocessor # カート/注文全体を前処理（送料計算など）
├── DiscountProcessor      # 割引処理
├── ItemHolderPostValidator# 最終チェック
└── PurchaseProcessor      # 購入確定処理
```

## Processorの種類と役割

### 1. ItemValidator - 商品単位の検証

商品1つ1つに対して検証を行います。

**例：在庫チェック（StockValidator）**

```php
class StockValidator extends ItemValidator
{
    protected function validate(ItemInterface $item, PurchaseContext $context)
    {
        // 商品以外はスキップ
        if (!$item->isProduct()) {
            return;
        }

        // 在庫無制限ならスキップ
        if ($item->getProductClass()->isStockUnlimited()) {
            return;
        }

        $stock = $item->getProductClass()->getStock();
        $quantity = $item->getQuantity();

        // 在庫が0なら
        if ($stock == 0) {
            $this->throwInvalidItemException('front.shopping.out_of_stock_zero', $item->getProductClass());
        }

        // 在庫が足りなければエラー
        if ($stock < $quantity) {
            $this->throwInvalidItemException('front.shopping.out_of_stock', $item->getProductClass());
        }
    }

    // エラー時の後処理：数量を在庫数に合わせる
    protected function handle(ItemInterface $item, PurchaseContext $context)
    {
        $stock = $item->getProductClass()->getStock();
        $item->setQuantity($stock);
    }
}
```

### 2. ItemHolderPreprocessor - 注文全体の前処理

カートや注文全体に対して処理を行います。

**例：送料計算（DeliveryFeePreprocessor）**

```php
class DeliveryFeePreprocessor implements ItemHolderPreprocessor
{
    public function process(ItemHolderInterface $itemHolder, PurchaseContext $context)
    {
        // 既存の送料明細を削除
        $this->removeDeliveryFeeItem($itemHolder);

        // 新しい送料明細を追加
        $this->saveDeliveryFeeItem($itemHolder);
    }

    private function saveDeliveryFeeItem(ItemHolderInterface $itemHolder)
    {
        foreach ($itemHolder->getShippings() as $Shipping) {
            // 都道府県と配送方法から送料を取得
            $DeliveryFee = $this->deliveryFeeRepository->findOneBy([
                'Delivery' => $Shipping->getDelivery(),
                'Pref' => $Shipping->getPref(),
            ]);

            // 送料の明細行を作成して追加
            $OrderItem = new OrderItem();
            $OrderItem->setProductName('送料')
                ->setPrice($DeliveryFee->getFee())
                ->setQuantity(1)
                ->setOrderItemType($DeliveryFeeType);

            $itemHolder->addItem($OrderItem);
        }
    }
}
```

### 3. DiscountProcessor - 割引処理

クーポンやポイント値引きなどの割引処理を行います。

### 4. PurchaseProcessor - 購入確定処理

注文の仮確定・確定・取り消しを行います。

```php
interface PurchaseProcessor
{
    // 仮確定（在庫の仮押さえなど）
    public function prepare(ItemHolderInterface $target, PurchaseContext $context);

    // 確定（実際に在庫を減らすなど）
    public function commit(ItemHolderInterface $target, PurchaseContext $context);

    // 取り消し（仮押さえの解除など）
    public function rollback(ItemHolderInterface $target, PurchaseContext $context);
}
```

## プラグインでPurchaseFlowをカスタマイズする

### 方法1：アノテーションを使う（推奨）

クラスにアノテーションを付けるだけで、自動的にPurchaseFlowに組み込まれます。

```php
<?php

namespace Plugin\MyPlugin\Service\PurchaseFlow\Processor;

use Eccube\Annotation\ShoppingFlow;
use Eccube\Entity\ItemInterface;
use Eccube\Service\PurchaseFlow\ItemValidator;
use Eccube\Service\PurchaseFlow\PurchaseContext;

/**
 * @ShoppingFlow  ← これだけで購入フローに追加される
 */
class MyCustomValidator extends ItemValidator
{
    protected function validate(ItemInterface $item, PurchaseContext $context)
    {
        // カスタム検証ロジック
    }
}
```

**利用可能なアノテーション：**

| アノテーション | 対象フロー |
|---------------|-----------|
| `@CartFlow` | カートフロー |
| `@ShoppingFlow` | 購入フロー |
| `@OrderFlow` | 受注管理フロー |

### 方法2：services.yamlで設定する

より細かい制御（優先度指定など）が必要な場合は、`services.yaml`で設定します。

```yaml
# app/Plugin/MyPlugin/Resource/config/services.yaml
services:
    Plugin\MyPlugin\Service\PurchaseFlow\Processor\MyCustomValidator:
        tags:
            - { name: eccube.item.validator, flow_type: shopping, priority: 100 }
```

**タグ一覧：**

| タグ名 | Processor種類 |
|--------|---------------|
| `eccube.item.validator` | ItemValidator |
| `eccube.item.holder.validator` | ItemHolderValidator |
| `eccube.item.preprocessor` | ItemPreprocessor |
| `eccube.item.holder.preprocessor` | ItemHolderPreprocessor |
| `eccube.discount.processor` | DiscountProcessor |
| `eccube.item.holder.post.validator` | ItemHolderPostValidator |
| `eccube.purchase.processor` | PurchaseProcessor |

**flow_type：**
- `cart` - カートフロー
- `shopping` - 購入フロー
- `order` - 受注管理フロー

**priority：** 数値が大きいほど先に実行されます（デフォルト: 0）

## 実践例：購入数量の上限を設定する

商品1つあたりの購入数量を10個までに制限するValidatorを作成してみましょう。

### 1. Validatorクラスの作成

```php
<?php
// app/Plugin/MyPlugin/Service/PurchaseFlow/Processor/QuantityLimitValidator.php

namespace Plugin\MyPlugin\Service\PurchaseFlow\Processor;

use Eccube\Annotation\CartFlow;
use Eccube\Annotation\ShoppingFlow;
use Eccube\Entity\ItemInterface;
use Eccube\Service\PurchaseFlow\InvalidItemException;
use Eccube\Service\PurchaseFlow\ItemValidator;
use Eccube\Service\PurchaseFlow\PurchaseContext;

/**
 * 購入数量の上限チェック
 *
 * @CartFlow
 * @ShoppingFlow
 */
class QuantityLimitValidator extends ItemValidator
{
    private const MAX_QUANTITY = 10;

    protected function validate(ItemInterface $item, PurchaseContext $context)
    {
        // 商品以外はスキップ
        if (!$item->isProduct()) {
            return;
        }

        if ($item->getQuantity() > self::MAX_QUANTITY) {
            $this->throwInvalidItemException(
                '1商品あたり'.self::MAX_QUANTITY.'個までしか購入できません。',
                $item->getProductClass()
            );
        }
    }

    protected function handle(ItemInterface $item, PurchaseContext $context)
    {
        // エラー時は上限値に修正
        $item->setQuantity(self::MAX_QUANTITY);
    }
}
```

### 2. サービス登録（自動登録の場合は不要）

```yaml
# app/Plugin/MyPlugin/Resource/config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true

    Plugin\MyPlugin\Service\PurchaseFlow\Processor\:
        resource: '../../Service/PurchaseFlow/Processor/*'
```

これだけで、カートと購入フローで数量制限が有効になります。

## 実践例：特定の条件で送料無料にする

5,000円以上の購入で送料を無料にするPreprocessorを作成します。

```php
<?php
// app/Plugin/MyPlugin/Service/PurchaseFlow/Processor/FreeShippingBySubtotalPreprocessor.php

namespace Plugin\MyPlugin\Service\PurchaseFlow\Processor;

use Eccube\Annotation\ShoppingFlow;
use Eccube\Entity\ItemHolderInterface;
use Eccube\Entity\Order;
use Eccube\Service\PurchaseFlow\ItemHolderPreprocessor;
use Eccube\Service\PurchaseFlow\PurchaseContext;

/**
 * 5,000円以上で送料無料
 *
 * @ShoppingFlow
 */
class FreeShippingBySubtotalPreprocessor implements ItemHolderPreprocessor
{
    private const FREE_SHIPPING_THRESHOLD = 5000;

    public function process(ItemHolderInterface $itemHolder, PurchaseContext $context)
    {
        if (!$itemHolder instanceof Order) {
            return;
        }

        // 小計を取得
        $subTotal = $itemHolder->getSubTotal();

        // 5,000円未満なら何もしない
        if ($subTotal < self::FREE_SHIPPING_THRESHOLD) {
            return;
        }

        // 送料の明細を0円にする
        foreach ($itemHolder->getItems() as $item) {
            if ($item->isDeliveryFee()) {
                $item->setPrice(0);
            }
        }
    }
}
```

:::message
**注意**: このProcessorは `DeliveryFeePreprocessor` より後に実行される必要があります。priorityを調整するか、`services.yaml`で順序を制御してください。
:::

## PurchaseFlowのデバッグ

現在のPurchaseFlowにどのProcessorが登録されているか確認できます。

```php
// Controllerなどで
$purchaseFlow = $this->container->get('eccube.purchase.flow.shopping');
dump($purchaseFlow->dump());
```

出力例：
```
shopping flow
├─ItemValidator
│├─StockValidator
│└─QuantityLimitValidator  ← 追加したValidator
├─ItemHolderValidator
│└─EmptyItemsValidator
├─ItemPreprocessor
├─ItemHolderPreprocessor
│├─DeliveryFeePreprocessor
│└─FreeShippingBySubtotalPreprocessor  ← 追加したPreprocessor
...
```

## まとめ

EC-CUBEのPurchaseFlowは、ストラテジーパターンにより以下のメリットを実現しています：

1. **柔軟性** - 処理を追加・削除しても他に影響しない
2. **再利用性** - 同じProcessorを複数のフローで使い回せる
3. **テスト容易性** - 各Processorを個別にテストできる
4. **保守性** - 処理の追加・変更が容易

プラグインでカスタマイズする際は：

1. 適切なProcessor種類（Validator/Preprocessor等）を選ぶ
2. アノテーションまたはservices.yamlでフローに登録する
3. 必要に応じてpriorityで実行順序を制御する

この仕組みを理解すれば、EC-CUBEの購入フローを自由自在にカスタマイズできます。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
