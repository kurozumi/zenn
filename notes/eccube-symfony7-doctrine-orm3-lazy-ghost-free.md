# EC-CUBE 4.3のSymfony7/Doctrine ORM3対応で注意すべきLazyGhostObjectsの変更点

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## はじめに

EC-CUBE 4.3では、Symfony 7およびDoctrine ORM 3への対応が進められています。この過程で、Doctrine ORM 3から導入された**LazyGhostObjects**（遅延ゴーストオブジェクト）の仕様変更により、`AbstractMasterEntity`を継承したマスタデータのエンティティでエラーが発生する問題が報告されています。

本記事では、この問題の原因と解決策、そしてプラグイン開発者が注意すべき点について解説します。

## 問題の概要

EC-CUBEのSymfony 7対応ブランチで、管理画面の会員一覧画面（`/admin/customer`）にアクセスすると、以下のようなエラーが発生します。

```
Proxies\__CG__\Eccube\Entity\Master\Pref: unknown property "name"

InvalidArgumentException
in src/Eccube/Entity/Master/AbstractMasterEntity.php (line 133)
in vendor/symfony/var-exporter/LazyGhostTrait.php -> __set (line 232)
```

このエラーは、都道府県（`Pref`）などのマスタデータを取得する際に発生します。