---
title: EC-CUBE 4.3のSymfony7/Doctrine ORM3対応で注意すべきLazyGhostObjectsの変更点
tags:
  - PHP
  - Symfony
  - doctrine
  - EC-CUBE
private: false
updated_at: '2026-03-19T15:13:05+09:00'
id: 32bca50ada1057023ba4
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4.3のSymfony7/Doctrine ORM3対応で注意すべきLazyGhostObjectsの変更点](https://zenn.dev/kurozumi/articles/eccube-symfony7-doctrine-orm3-lazy-ghost)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4.3のSymfony7/Doctrine ORM3対応で注意すべきLazyGhostObjectsの変更点](https://zenn.dev/kurozumi/articles/eccube-symfony7-doctrine-orm3-lazy-ghost)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
