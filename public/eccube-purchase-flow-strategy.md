---
title: 'EC-CUBE 4のPurchaseFlowを理解する - ストラテジーパターンで実現する柔軟な購入フロー'
tags:
  - EC-CUBE
  - PHP
  - Symfony
  - デザインパターン
private: false
updated_at: '2026-03-19T15:13:06+09:00'
id: c4227c8b8ce211cb788e
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4のPurchaseFlowを理解する - ストラテジーパターンで実現する柔軟な購入フロー](https://zenn.dev/kurozumi/articles/eccube-purchase-flow-strategy)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4のPurchaseFlowを理解する - ストラテジーパターンで実現する柔軟な購入フロー](https://zenn.dev/kurozumi/articles/eccube-purchase-flow-strategy)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
