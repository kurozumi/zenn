---
title: 'EC-CUBE大量商品サイトの高速化テクニック10選'
tags:
  - EC-CUBE
  - PHP
  - performance
private: false
updated_at: '2026-03-17T22:47:07+09:00'
id: 1d35483cdbe258493f44
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE大量商品サイトの高速化テクニック10選](https://zenn.dev/and_and/articles/eccube-performance-tuning)**

---

商品数が数万件を超えると、EC-CUBE のパフォーマンスが低下することがあります。この記事では、大量商品サイトを高速化するための実践的なテクニックを紹介します。

## 1. N+1問題の解決

### 問題

商品一覧で関連エンティティを取得する際、商品ごとにクエリが発行される N+1 問題が発生します。

```php
// 悪い例：商品ごとにカテゴリを取得（N+1問題）
$products = $productRepository->findAll();
foreach ($products as $product) {
    $categories = $product->getProductCategories(); // 毎回クエリ発行
}
```

### 解決策

QueryBuilder で JOIN を使って一度に取得します。

```php
<?php

namespace Plugin\YourPlugin\Repository;

use Eccube\Repository\ProductRepository as BaseRepository;

class ProductRepository extends BaseRepository
{
    public function findProductsWithCategories(): array
    {
        return $this->createQueryBuilder('p')
            ->select('p', 'pc', 'c')
            ->leftJoin('p.ProductCategories', 'pc')
            ->leftJoin('pc.Category', 'c')
            ->getQuery()
            ->getResult();
    }
}
```

## 2. ページネーションの最適化

### 問題

`COUNT(*)` クエリが大量データで遅くなります。

### 解決策

Doctrine の Paginator ではなく、カスタムページネーションを実装します。

```php
<?php

namespace Plugin\YourPlugin\Repository;

use Doctrine\ORM\Tools\Pagination\Paginator;

class OptimizedProductRepository
{
    /**
     * 総件数を概算で取得（高速）
     */
    public function getEstimatedCount(): int
    {
        $conn = $this->getEntityManager()->getConnection();
        $result = $conn->executeQuery("
            SELECT reltuples::bigint AS estimate
            FROM pg_class
            WHERE relname = 'dtb_product'
        ")->fetchAssociative();

        return (int) ($result['estimate'] ?? 0);
    }

    /**
     * キーセットページネーション（OFFSET を使わない）
     */
    public function findProductsAfter(?int $lastId, int $limit = 20): array
    {
        $qb = $this->createQueryBuilder('p')
            ->orderBy('p.id', 'ASC')
            ->setMaxResults($limit);

        if ($lastId !== null) {
            $qb->where('p.id > :lastId')
               ->setParameter('lastId', $lastId);
        }

        return $qb->getQuery()->getResult();
    }
}
```

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE大量商品サイトの高速化テクニック10選](https://zenn.dev/and_and/articles/eccube-performance-tuning)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
