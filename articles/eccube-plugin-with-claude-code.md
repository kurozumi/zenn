---
title: "Claude CodeでEC-CUBEプラグインを爆速開発する方法"
emoji: "🚀"
type: "tech"
topics: ["eccube", "eccube4", "claudecode", "ai", "php"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

AI を活用したコーディングツールが急速に進化しています。この記事では、Anthropic が提供する **Claude Code** を使って EC-CUBE プラグインを効率的に開発する方法を紹介します。

## Claude Code とは

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) は、Anthropic が提供するターミナルベースの AI コーディングアシスタントです。

主な特徴：
- ターミナルで直接動作
- コードベース全体を理解
- ファイルの読み書き、コマンド実行が可能
- Git 操作もサポート

## EC-CUBE プラグイン開発での活用

### 1. プラグインの雛形生成

Claude Code に指示するだけで、プラグインの基本構造を生成できます。

```
あなた: 会員ランク機能を追加するEC-CUBEプラグインを作成して
```

Claude Code は以下のファイルを自動生成します：

- `Plugin.php` - プラグインのメインクラス
- `Entity/CustomerRank.php` - 会員ランクエンティティ
- `Repository/CustomerRankRepository.php` - リポジトリ
- `Controller/Admin/CustomerRankController.php` - 管理画面
- `Form/Type/Admin/CustomerRankType.php` - フォーム
- `Resource/template/` - Twig テンプレート
- `composer.json` - 依存関係

### 2. 既存コードの理解

EC-CUBE のコアコードを理解するのにも役立ちます。

```
あなた: PurchaseFlowの仕組みを説明して
```

Claude Code は EC-CUBE のソースコードを読み込み、処理の流れを解説してくれます。

### 3. カスタマイズの実装

既存機能のカスタマイズも指示するだけで実装できます。

```
あなた: 商品一覧ページに在庫数を表示するプラグインを作って
```

## 実践例：ポイント倍率プラグインの開発

実際に Claude Code を使ってプラグインを開発してみましょう。

### ステップ1: 要件を伝える

```
あなた: 商品ごとにポイント倍率を設定できるプラグインを作成して。
       管理画面の商品編集ページに倍率入力欄を追加し、
       購入時にポイントを倍率に応じて付与する機能が欲しい。
```

### ステップ2: 生成されるコード

#### ProductTrait（エンティティ拡張）

```php
<?php

namespace Plugin\PointMultiplier\Entity;

use Doctrine\ORM\Mapping as ORM;
use Eccube\Annotation\EntityExtension;

/**
 * @EntityExtension("Eccube\Entity\Product")
 */
trait ProductTrait
{
    #[ORM\Column(type: 'decimal', precision: 3, scale: 1, nullable: true, options: ['default' => 1.0])]
    private ?string $point_multiplier = '1.0';

    public function getPointMultiplier(): float
    {
        return (float) ($this->point_multiplier ?? 1.0);
    }

    public function setPointMultiplier(?float $pointMultiplier): self
    {
        $this->point_multiplier = $pointMultiplier !== null ? (string) $pointMultiplier : '1.0';
        return $this;
    }
}
```

#### FormExtension（フォーム拡張）

```php
<?php

namespace Plugin\PointMultiplier\Form\Extension;

use Eccube\Form\Type\Admin\ProductType;
use Symfony\Component\Form\AbstractTypeExtension;
use Symfony\Component\Form\Extension\Core\Type\NumberType;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Validator\Constraints as Assert;

class ProductTypeExtension extends AbstractTypeExtension
{
    public static function getExtendedTypes(): iterable
    {
        yield ProductType::class;
    }

    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder->add('point_multiplier', NumberType::class, [
            'label' => 'ポイント倍率',
            'required' => false,
            'scale' => 1,
            'attr' => [
                'placeholder' => '1.0',
            ],
            'constraints' => [
                new Assert\Range([
                    'min' => 0.1,
                    'max' => 10.0,
                    'notInRangeMessage' => '{{ min }}〜{{ max }}の範囲で入力してください。',
                ]),
            ],
        ]);
    }
}
```

#### PurchaseFlow Processor（ポイント計算）

```php
<?php

namespace Plugin\PointMultiplier\Service\PurchaseFlow\Processor;

use Eccube\Annotation\ShoppingFlow;
use Eccube\Entity\ItemHolderInterface;
use Eccube\Entity\Order;
use Eccube\Service\PurchaseFlow\ItemHolderPreprocessor;
use Eccube\Service\PurchaseFlow\PurchaseContext;

/**
 * @ShoppingFlow
 */
class PointMultiplierProcessor implements ItemHolderPreprocessor
{
    public function process(ItemHolderInterface $itemHolder, PurchaseContext $context): void
    {
        if (!$itemHolder instanceof Order) {
            return;
        }

        $totalPoint = 0;
        foreach ($itemHolder->getProductOrderItems() as $orderItem) {
            $product = $orderItem->getProduct();
            if ($product === null) {
                continue;
            }

            $basePoint = $orderItem->getPoint() ?? 0;
            $multiplier = $product->getPointMultiplier();
            $totalPoint += (int) floor($basePoint * $multiplier);
        }

        $itemHolder->setAddPoint($totalPoint);
    }
}
```

### ステップ3: テストコードも生成

```
あなた: このプラグインのPHPUnitテストを作成して
```

```php
<?php

namespace Plugin\PointMultiplier\Tests;

use Eccube\Tests\EccubeTestCase;
use Plugin\PointMultiplier\Entity\ProductTrait;

class PointMultiplierTest extends EccubeTestCase
{
    public function testPointMultiplierDefault(): void
    {
        $Product = $this->createProduct();
        $this->assertEquals(1.0, $Product->getPointMultiplier());
    }

    public function testPointMultiplierSet(): void
    {
        $Product = $this->createProduct();
        $Product->setPointMultiplier(2.5);
        $this->assertEquals(2.5, $Product->getPointMultiplier());
    }
}
```

## Claude Code を使う際のコツ

### 1. CLAUDE.md を活用する

プロジェクトルートに `CLAUDE.md` を配置すると、Claude Code がプロジェクトのルールを理解します。

```markdown
# EC-CUBE プラグイン開発ルール

## 対象バージョン
- EC-CUBE 4.3 以上
- PHP 8.1 以上

## コーディング規約
- PSR-12 に準拠
- 型宣言を必ず使用
- コアエンティティは Trait で拡張
- コアフォームは FormExtension で拡張
```

### 2. 具体的な指示を出す

```
❌ 悪い例: 会員機能を作って

✅ 良い例: 会員にVIP/通常の2種類のランクを設定できる機能を作って。
          管理画面で会員ごとにランクを変更でき、
          VIP会員は全商品10%オフで購入できるようにして。
```

### 3. 段階的に開発する

一度に全てを作ろうとせず、段階的に機能を追加していきます。

```
1回目: まず会員ランクのエンティティとマイグレーションを作成して
2回目: 管理画面で会員ランクを編集できるようにして
3回目: VIP会員の割引処理を実装して
```

### 4. EC-CUBE のドキュメントを参照させる

```
あなた: EC-CUBE公式ドキュメント https://doc4.ec-cube.net/ を参照して、
       正しいプラグインの作り方で実装して
```

## スラッシュコマンドの活用

Claude Code には便利なスラッシュコマンドがあります。

| コマンド | 説明 |
|---------|------|
| `/init` | CLAUDE.md を生成 |
| `/compact` | 会話履歴を要約してコンテキストを節約 |
| `/clear` | 会話をリセット |
| `/cost` | 現在のセッションのコストを表示 |

## 注意点

### セキュリティの確認

AI が生成したコードは必ずセキュリティ面を確認してください。

- SQLインジェクション対策
- XSS対策
- CSRF対策

EC-CUBE には `@csrf_token_check` アノテーションなど、セキュリティ機能が用意されています。

### 動作確認は必須

生成されたコードは必ず実際に動作確認を行ってください。AI は完璧ではなく、EC-CUBE 固有の仕様を誤解している場合があります。

### バージョン互換性

EC-CUBE 4.2 と 4.3 では一部の API が異なります。対象バージョンを明確に伝えましょう。

## まとめ

Claude Code を活用することで、EC-CUBE プラグイン開発を大幅に効率化できます。

- 雛形生成の時間短縮
- EC-CUBE の仕様理解をサポート
- テストコードの自動生成
- リファクタリングの提案

ただし、AI は補助ツールです。最終的な品質は開発者自身が責任を持って確認しましょう。

## 参考リンク

- [Claude Code 公式ドキュメント](https://docs.anthropic.com/en/docs/claude-code)
- [EC-CUBE 4 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [EC-CUBE プラグイン仕様](https://doc4.ec-cube.net/plugin)
