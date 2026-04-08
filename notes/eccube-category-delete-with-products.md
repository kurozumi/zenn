# EC-CUBE 4で商品が紐づいていてもカテゴリを削除できるようにする

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

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

## プラグインで解決する

### アプローチ

EC-CUBEのイベントシステムを使って、カテゴリ削除前に関連データを処理します。

1. `admin.product.category.index.complete`イベントをフック
2. 削除リクエストを検知したら、先に関連データを削除
3. その後、通常の削除処理を実行

### 実装コード

#### Event Subscriber

```php
<?php

namespace Plugin\CategoryDeleteImprove\EventSubscriber;

use Doctrine\ORM\EntityManagerInterface;
use Eccube\Entity\Category;
use Eccube\Event\EccubeEvents;
use Eccube\Event\EventArgs;
use Eccube\Repository\CategoryRepository;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;
use Symfony\Component\HttpFoundation\RequestStack;

class CategoryEventSubscriber implements EventSubscriberInterface
{
    public function __construct(
        private EntityManagerInterface $entityManager,
        private CategoryRepository $categoryRepository,
        private RequestStack $requestStack,
    ) {
    }

    public static function getSubscribedEvents(): array
    {
        return [
            EccubeEvents::ADMIN_PRODUCT_CATEGORY_INDEX_COMPLETE => ['onCategoryDeletePre', 10],
        ];
    }

    public function onCategoryDeletePre(EventArgs $event): void
    {
        $request = $this->requestStack->getCurrentRequest();

        // 削除リクエストかどうかを判定
        $id = $request->get('id');
        $isDelete = $request->get('_method') === 'DELETE'
            || $request->getMethod() === 'DELETE';

        if (!$id || !$isDelete) {
            return;
        }

        /** @var Category|null $category */
        $category = $this->categoryRepository->find($id);

        if (!$category) {
            return;
        }

        // 関連データを削除
        $this->deleteRelatedData($category);
    }

    private function deleteRelatedData(Category $category): void
    {
        // 子カテゴリを再帰的に処理
        foreach ($category->getChildren() as $child) {
            $this->deleteRelatedData($child);
        }

        // 商品との紐づけを削除
        $this->deleteProductCategories($category);

        // 子カテゴリを削除
        $this->deleteChildren($category);
    }

    private function deleteProductCategories(Category $category): void
    {
        $this->entityManager->createQueryBuilder()
            ->delete('Eccube\Entity\ProductCategory', 'pc')
            ->where('pc.Category = :category')
            ->setParameter('category', $category)
            ->getQuery()
            ->execute();
    }

    private function deleteChildren(Category $category): void
    {
        foreach ($category->getChildren() as $child) {
            // ソート番号を調整
            $this->entityManager->createQueryBuilder()
                ->update('Eccube\Entity\Category', 'c')
                ->set('c.sort_no', 'c.sort_no - 1')
                ->where('c.sort_no > :sort_no')
                ->setParameter('sort_no', $child->getSortNo())
                ->getQuery()
                ->execute();

            $this->entityManager->remove($child);
        }

        $this->entityManager->flush();
    }
}
```

#### services.yaml

```yaml
services:
    Plugin\CategoryDeleteImprove\EventSubscriber\CategoryEventSubscriber:
        tags: ['kernel.event_subscriber']
```

## 削除前に確認ダイアログを表示する

カスケード削除は便利ですが、うっかり大量のデータを消してしまうリスクもあります。削除前に確認ダイアログを改善しましょう。

### Twigテンプレートの拡張

```twig
{# app/template/admin/Product/category_card.twig #}
{% extends '@admin/Product/category_card.twig' %}

{% block javascript %}
{{ parent() }}
<script>
$(function() {
    $('.btn-ec-delete').on('click', function(e) {
        var categoryName = $(this).closest('li').find('.category-name').text().trim();
        var hasChildren = $(this).closest('li').find('ul.list-group').length > 0;

        var message = 'カテゴリ「' + categoryName + '」を削除しますか？';

        if (hasChildren) {
            message += '\n\n※ 子カテゴリも同時に削除されます。';
        }

        message += '\n※ 商品との紐づけも解除されます。';

        if (!confirm(message)) {
            e.preventDefault();
            e.stopPropagation();
            return false;
        }
    });
});
</script>
{% endblock %}
```

## 注意点

### 1. 商品のカテゴリが空になる可能性

カテゴリを削除すると、そのカテゴリのみに紐づいていた商品はカテゴリなしの状態になります。必要に応じて、削除前にチェックする処理を追加しましょう。

```php
private function hasOrphanProducts(Category $category): bool
{
    // このカテゴリのみに紐づいている商品を検索
    $qb = $this->entityManager->createQueryBuilder();

    return $qb->select('COUNT(p.id)')
        ->from('Eccube\Entity\Product', 'p')
        ->innerJoin('p.ProductCategories', 'pc')
        ->groupBy('p.id')
        ->having('COUNT(pc.id) = 1')
        ->andWhere('pc.Category = :category')
        ->setParameter('category', $category)
        ->getQuery()
        ->getSingleScalarResult() > 0;
}
```

### 2. 大量データの削除時はバッチ処理を検討

子カテゴリや商品紐づけが大量にある場合、一度に削除するとタイムアウトする可能性があります。バッチ処理やキュー処理の導入を検討してください。

### 3. 削除履歴の保持

監査目的で削除履歴を残したい場合は、物理削除ではなく論理削除（ソフトデリート）の実装を検討しましょう。

## まとめ

- EC-CUBEのカテゴリ削除は外部キー制約で保護されている
- イベントシステムを使って、削除前に関連データを処理できる
- 実装時は確認ダイアログの改善や、孤立商品のチェックも忘れずに

この機能が本体に取り込まれるかは[Issue #6587](https://github.com/EC-CUBE/ec-cube/issues/6587)の議論次第ですが、プラグインで先行実装しておくと便利です。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---