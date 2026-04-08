# EC-CUBE 4.3のSymfony7/Doctrine ORM3対応で注意すべきLazyGhostObjectsの変更点

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

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

## 原因：LazyGhostObjectsとは

### Doctrine ORM 3の遅延読み込みの変更

Doctrine ORM 3では、エンティティの遅延読み込み（Lazy Loading）の実装方法が変更されました。従来のプロキシ方式に代わり、**LazyGhostObjects**という新しい仕組みが導入されています。

```yaml
doctrine:
    orm:
        enable_lazy_ghost_objects: true  # ORM 3では必須
```

LazyGhostObjectsは、エンティティのプロパティにアクセスされるまで初期化を遅延させる「ゴースト」オブジェクトを生成します。プロパティに初めてアクセスした瞬間に、必要なデータがデータベースから取得されます。

### AbstractMasterEntityの__setメソッド

EC-CUBEの`AbstractMasterEntity`クラスには、マスタデータの不変性を保証するために`__set`マジックメソッドが実装されています。

```php
// src/Eccube/Entity/Master/AbstractMasterEntity.php
public function __set($name, $value)
{
    throw new \InvalidArgumentException();
}
```

この実装は、外部からプロパティを直接変更することを禁止するためのものです。

### なぜエラーが発生するのか

問題は、LazyGhostObjectsの初期化時に`__set`メソッドが呼び出されることにあります。

`LazyGhostTrait::__set()`の動作を見てみましょう。

```php
// vendor/symfony/var-exporter/LazyGhostTrait.php
public function __set($name, $value): void
{
    $propertyScopes = Hydrator::$propertyScopes[$this::class]
        ??= Hydrator::getPropertyScopes($this::class);

    // プロパティがスコープに存在し、未初期化状態の場合
    if ([$class, , $writeScope, $access] = $propertyScopes[$name] ?? null) {
        // ... 初期化処理 ...
        if ($state && /** 条件 **/) {
            goto set_in_scope;  // parent::__set()をスキップ
        }
    }

    // 親クラスに__set()が定義されていれば呼び出す
    if (Registry::$parentMethods[self::class]['set']) {
        parent::__set($name, $value);  // ← ここでエラー発生！
        return;
    }

    set_in_scope:
    // プロパティへの直接設定...
}
```

以下の条件で`parent::__set()`が呼ばれ、`InvalidArgumentException`が発生します。

1. プロパティが`$propertyScopes`に存在しない
2. プロキシの状態（`$state`）がnull
3. プロキシのステータスが`STATUS_INITIALIZED_FULL`（完全初期化済み）

## 解決策

### EC-CUBE本体での対応

EC-CUBEでは、`AbstractMasterEntity::__set()`を以下のように修正することで対応しています。

```php
public function __set($name, $value)
{
    // エンティティの定義済みプロパティへのアクセスは許可
    // Doctrine ORM 3のLazyGhostTraitがプロキシ初期化時に使用する
    if (in_array($name, ['id', 'name', 'sort_no'], true)) {
        $reflection = new \ReflectionClass($this);
        $property = $reflection->getProperty($name);
        $property->setAccessible(true);
        $property->setValue($this, $value);
        return;
    }

    throw new \InvalidArgumentException(sprintf(
        'Cannot set unknown property "%s" on %s',
        $name,
        static::class
    ));
}
```

この修正により、定義済みプロパティ（`id`, `name`, `sort_no`）へのアクセスは許可しつつ、不正なプロパティアクセスはブロックします。

### PHP 8.4以降の対応

PHP 8.4では**Native Lazy Objects**が導入されます。これを使用すると、LazyGhostTraitを経由せずにネイティブな遅延オブジェクトが使用されるため、`__set`の問題は発生しません。

```yaml
doctrine:
    orm:
        enable_native_lazy_objects: true
```

## プラグイン開発者への影響

### AbstractMasterEntityを継承したカスタムエンティティ

プラグインで`AbstractMasterEntity`を継承して独自のマスタデータを作成している場合、注意が必要です。

```php
// 独自のマスタデータエンティティ
class CustomStatus extends AbstractMasterEntity
{
    protected $custom_field;  // 独自プロパティ
}
```

この場合、`custom_field`へのアクセス時に`InvalidArgumentException`が発生する可能性があります。

### 対応方法

独自プロパティを持つ場合は、`__set`メソッドをオーバーライドして許可リストに追加します。

```php
class CustomStatus extends AbstractMasterEntity
{
    protected $custom_field;

    public function __set($name, $value)
    {
        // 独自プロパティを許可
        if ($name === 'custom_field') {
            $this->custom_field = $value;
            return;
        }

        parent::__set($name, $value);
    }
}
```

または、より汎用的にリフレクションで判定する方法もあります。

```php
public function __set($name, $value)
{
    $reflection = new \ReflectionClass($this);
    if ($reflection->hasProperty($name)) {
        $property = $reflection->getProperty($name);
        $property->setAccessible(true);
        $property->setValue($this, $value);
        return;
    }

    throw new \InvalidArgumentException(sprintf(
        'Cannot set unknown property "%s" on %s',
        $name,
        static::class
    ));
}
```

## __setと__getの廃止について

EC-CUBEでは、この機能を廃止する方向で検討が進められています。

もともと`__set()`/`__get()`が実装された経緯は、マスタデータへの定数的なアクセスを可能にするためでした。

```php
// 従来の使い方（マジックメソッド経由）
$orderStatus = $orderStatusRepository->find(OrderStatus::NEW);
```

しかし、PHP 8.2以降ではtraitにクラス定数を追加できるようになったため、マジックメソッドに依存しない実装が可能です。

## まとめ

- Doctrine ORM 3の**LazyGhostObjects**は、プロパティアクセス時に遅延初期化を行う
- この初期化時に`__set`が呼ばれるため、`AbstractMasterEntity`でエラーが発生
- EC-CUBE本体では、定義済みプロパティへのアクセスを許可する形で対応
- プラグイン開発者は、独自プロパティを持つマスタデータエンティティで同様の対応が必要
- PHP 8.4以降では`enable_native_lazy_objects`でこの問題を回避可能

Symfony 7/Doctrine ORM 3への移行を検討している方は、マスタデータエンティティの実装を確認しておくことをお勧めします。

## 参考リンク

- [GitHub Issue: Doctrine ORM3から暗黙的に__setが呼ばれるようになった](https://github.com/EC-CUBE/ec-cube/issues/6469)
- [Symfony VarExporter LazyGhostTrait](https://github.com/symfony/symfony/blob/7.2/src/Symfony/Component/VarExporter/LazyGhostTrait.php)
- [Doctrine ORM Lazy Loading](https://www.doctrine-project.org/projects/doctrine-orm/en/latest/reference/advanced-configuration.html#enabling-lazy-ghost-objects)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---