## 原因：LazyGhostObjectsとは

### Doctrine ORM 3の遅延読み込みの変更

Doctrine ORM 3では、エンティティの遅延読み込み（Lazy Loading）の実装方法が変更されました。従来のプロキシ方式に代わり、**LazyGhostObjects**という新しい仕組みが導入されています。


LazyGhostObjectsは、エンティティのプロパティにアクセスされるまで初期化を遅延させる「ゴースト」オブジェクトを生成します。プロパティに初めてアクセスした瞬間に、必要なデータがデータベースから取得されます。

### AbstractMasterEntityの__setメソッド

EC-CUBEの`AbstractMasterEntity`クラスには、マスタデータの不変性を保証するために`__set`マジックメソッドが実装されています。


この実装は、外部からプロパティを直接変更することを禁止するためのものです。

### なぜエラーが発生するのか

問題は、LazyGhostObjectsの初期化時に`__set`メソッドが呼び出されることにあります。

`LazyGhostTrait::__set()`の動作を見てみましょう。


以下の条件で`parent::__set()`が呼ばれ、`InvalidArgumentException`が発生します。

1. プロパティが`$propertyScopes`に存在しない
2. プロキシの状態（`$state`）がnull
3. プロキシのステータスが`STATUS_INITIALIZED_FULL`（完全初期化済み）

## 解決策

### EC-CUBE本体での対応

EC-CUBEでは、`AbstractMasterEntity::__set()`を以下のように修正することで対応しています。


この修正により、定義済みプロパティ（`id`, `name`, `sort_no`）へのアクセスは許可しつつ、不正なプロパティアクセスはブロックします。

### PHP 8.4以降の対応

PHP 8.4では**Native Lazy Objects**が導入されます。これを使用すると、LazyGhostTraitを経由せずにネイティブな遅延オブジェクトが使用されるため、`__set`の問題は発生しません。


## プラグイン開発者への影響

### AbstractMasterEntityを継承したカスタムエンティティ

プラグインで`AbstractMasterEntity`を継承して独自のマスタデータを作成している場合、注意が必要です。


この場合、`custom_field`へのアクセス時に`InvalidArgumentException`が発生する可能性があります。

### 対応方法

独自プロパティを持つ場合は、`__set`メソッドをオーバーライドして許可リストに追加します。


または、より汎用的にリフレクションで判定する方法もあります。


## __setと__getの廃止について

EC-CUBEでは、この機能を廃止する方向で検討が進められています。

もともと`__set()`/`__get()`が実装された経緯は、マスタデータへの定数的なアクセスを可能にするためでした。


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