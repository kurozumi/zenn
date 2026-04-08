## 仕組み：コンパイラーパスによる自動検出

内部実装としては `RegisterCustomTypePass` というコンパイラーパスが追加され、DIコンテナのビルド時に `#[AsDoctrineType]` 属性を持つクラスを自動検出し、`doctrine.dbal.connection_factory.types` に登録します。

Symfonyの `#[AsTaggedItem]` や `#[AutoconfigureTag]` と同じ思想の拡張です。EC-CUBEでも `#[AsEccubeNav]` や `#[AsEccubeAdminNav]` といった属性ベースの自動設定が使われており、同じパターンです。

---

## EC-CUBEプラグイン開発への影響

EC-CUBEのプラグインでカスタムDoctrineタイプを使うケースは意外と多いです。

| ユースケース | カスタムタイプの例 |
|---|---|
| 金額を専用の値オブジェクトで扱う | `MoneyType` |
| 複数の設定値をJSONで1カラムに格納 | `SettingsType` |
| Enumをそのままカラムに保存 | `OrderStatusType` |
| 暗号化が必要なカラム | `EncryptedStringType` ※ |

これらがすべて `doctrine.yaml` の記述なしで動くようになります。


### 現在のEC-CUBEでの対応策

このPRがマージされてもEC-CUBE 4.3（Symfony 6.4ベース）では使えません。現時点では以下の方法でカスタムタイプを登録してください。

```yaml
# app/Plugin/AcmePlugin/Resource/config/services.yaml で登録するか
# app/Plugin/AcmePlugin/Resource/config/doctrine.yaml に記載する

doctrine:
  dbal:
    types:
      money: Plugin\AcmePlugin\Doctrine\Type\MoneyType
      settings: Plugin\AcmePlugin\Doctrine\Type\SettingsType
```

または、プラグインの `ServiceProvider` で動的に登録する方法もあります。

```php
// PluginManager.php
use Doctrine\DBAL\Types\Type;

public function install(array $meta, ContainerInterface $container): void
{
    if (!Type::hasType('money')) {
        Type::addType('money', MoneyType::class);
    }
}
```

---

## EC-CUBEのSymfony 7.4移行が進行中（PR #6686）

実は、EC-CUBE本体でも大規模なアップグレードが進んでいます。

**[EC-CUBE PR #6686: Upgrade to Symfony 7.4 / Doctrine ORM 3.6 / DBAL 4.4](https://github.com/EC-CUBE/ec-cube/pull/6686)**

| 対象 | 現在 | アップグレード後 |
|---|---|---|
| Symfony | 6.4 | **7.4 LTS**（PHP 8.2+必須） |
| Doctrine ORM | 2.x | **3.6** |
| Doctrine DBAL | 3.x | **4.4** |
| Monolog | 2.x | 3.x |

### `getName()` はDBAL 4.4で完全に削除される

前述のコード例で触れた `getName()` メソッドは、DBAL 3.x では非推奨でしたが、**DBAL 4.4では削除されます**。EC-CUBE PR #6686 がマージされると、`getName()` を実装しているカスタムタイプはエラーになります。

既存プラグインのカスタムDoctrineタイプを持っている場合、`getName()` を削除する対応が必要になります。

```php
// DBAL 4.x 対応後は getName() を削除する
// （タイプ名はTypeRegistryで管理されるため不要）
final class MoneyType extends Type
{
    public function getSQLDeclaration(array $column, AbstractPlatform $platform): string
    {
        return 'DECIMAL(10, 2)';
    }

    // getName() は不要（削除する）
}
```

### 既存プラグインの互換性

PR #6686 では**4つの互換レイヤー**が実装されており、`@ORM` アノテーション記法のプラグインも当面は動作するよう設計されています。

| 互換レイヤー | 対応内容 |
|---|---|
| `HybridMappingDriver` | `@ORM` アノテーションと属性の両方に対応 |
| `HybridAnnotationClassLoader` | `@Route` アノテーション互換 |
| `TemplateAnnotationListener` | `@Template` アノテーション互換 |
| `PluginReturnTypeCompatLoader` | プラグインメソッドへの戻り値型を自動補完 |

ただし、長期的にはアノテーション記法から**PHP 8属性**への移行が推奨されます。

ℹ️ PR #6686 は2026年3月時点でオープン中で、`4.3-symfony7` ブランチで開発中です。正式リリース時期は未確定ですが、プラグイン開発者は今から対応を意識しておくと安心です。

---

## まとめ

| 比較軸 | 現在（Symfony 6.4） | PR #63774後（Symfony 8.1〜） |
|---|---|---|
| 登録方法 | `doctrine.yaml` に手動追記 | `#[AsDoctrineType]` 属性1行 |
| 追記漏れリスク | あり（実行時エラー） | なし（自動検出） |
| タイプ追加時の作業 | PHPファイル＋YAMLの2ファイル | PHPファイルのみ |
| EC-CUBE 4.3対応 | 今すぐ使える | 将来のバージョンアップ後 |

属性ベースの自動設定はSymfonyの流れであり、EC-CUBEもこの恩恵を受けるのは時間の問題です。今のうちにカスタムDoctrineタイプのパターンを把握しておくと、将来のバージョンアップ時にスムーズに移行できます。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---