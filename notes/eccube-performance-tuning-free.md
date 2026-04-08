# EC-CUBE大量商品サイトの高速化テクニック10選

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

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