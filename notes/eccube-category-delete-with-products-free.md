# EC-CUBE 4で商品が紐づいていてもカテゴリを削除できるようにする

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## はじめに

EC-CUBEでカテゴリを整理・再編しようとしたとき、こんな経験はありませんか？

- 商品が紐づいているカテゴリが削除できない
- 子カテゴリがあると親カテゴリを削除できない
- 結果、商品からカテゴリを一つずつ外す作業が発生...

この問題は[EC-CUBEのIssue #6587](https://github.com/EC-CUBE/ec-cube/issues/6587)でも要望として挙がっています。

本記事では、プラグインを使ってこの制限を解除する方法を解説します。

## なぜ削除できないのか

### 外部キー制約による保護

EC-CUBEのカテゴリ削除処理を見てみましょう。

```php
// src/Eccube/Repository/CategoryRepository.php
public function delete($Category)
{
    // ソート番号の調整
    $this->createQueryBuilder('c')
        ->update()
        ->set('c.sort_no', 'c.sort_no - 1')
        ->where('c.sort_no > :sort_no')
        ->setParameter('sort_no', $Category->getSortNo())
        ->getQuery()
        ->execute();

    // カテゴリの削除
    $em = $this->getEntityManager();
    $em->remove($Category);
    $em->flush();
}
```

単純に`remove()`で削除しているだけですが、データベースの外部キー制約により以下の場合は削除に失敗します：

1. **商品が紐づいている場合**: `dtb_product_category`テーブルに参照レコードが存在
2. **子カテゴリがある場合**: `dtb_category`テーブルの`parent_id`に参照が存在

### Entityの関連定義

`Category`エンティティの定義を確認すると、`cascade`や`orphanRemoval`が設定されていないことがわかります。

```php
// src/Eccube/Entity/Category.php

#[ORM\OneToMany(targetEntity: ProductCategory::class, mappedBy: 'Category', fetch: 'EXTRA_LAZY')]
protected $ProductCategories;

#[ORM\OneToMany(targetEntity: Category::class, mappedBy: 'Parent')]
#[ORM\OrderBy(['sort_no' => 'DESC'])]
protected $Children;
```

これは**意図的な設計**で、関連データの誤削除を防いでいます。しかし、運用上は柔軟に削除したいケースも多いでしょう。