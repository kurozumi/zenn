---
title: "EC-CUBE 4.4で動かなくなるプラグイン｜Symfony 7移行で壊れる7つのポイント"
emoji: "⚠️"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "doctrine"]
published: true
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## TL;DR

> **「うちのプラグイン、4.4 でもそのまま動くだろう」と思っていませんか？**
> 結論から言うと、**Entity を拡張・金額計算・テストコードを書いているプラグインは、ほぼ確実に修正が必要**です。理由は、4.4 が「機能追加」ではなく **Symfony 7・Doctrine 3・PHP 8.5 への土台総入れ替え**だから。以下の7項目に1つでも心当たりがあれば、この記事はあなた向けです。

- **EC-CUBE 4.4 は 2026年8月下旬の正式版リリースを目標**に開発中です（[GitHub Issue #6762](https://github.com/EC-CUBE/ec-cube/issues/6762)）。
- 中身はほぼ**フレームワークのメジャーアップグレード**です。Symfony 6.4 → **7.4**、Doctrine ORM 2.x → **3.x**、PHP は **8.2〜8.5** が対象になります。
- この変更により、**Entity 拡張・イベント購読・金額計算・テストコードを書いているプラグインは修正がほぼ必須**になります。
- 加えて **AI（Agentic Commerce / AEO）対応**として、商品フィードやリードオンリーの MCP サーバ機能が新規追加される予定です。
- リポジトリには移行支援用の `rector.php` が同梱されています。**今のうちから手元のプラグインを 4.4 ブランチで動かしてみることが最善の準備**です。

---

## はじめに：なぜ「今」読むべきなのか

EC-CUBE のバージョンアップでは、これまでも互換性のない変更が繰り返されてきました。2系・3系・4系の間には互換性がなく、4 系の中でも 4.1 → 4.2 では Symfony のバージョンアップに伴いプラグインの大幅な改修が必要でした。**そして 4.4 も例外ではありません。** Symfony 6.4 → 7.4、Doctrine ORM 2 → 3、PHP 8.5 対応という、**土台（フレームワーク）の世代交代**を伴うからです。

これが意味するのは、こういうことです。

> **アノテーションで Entity を書いているプラグインは、4.4 ではそのままでは動かない可能性があります。**

2026年6月現在、GitHub には [4.4 のロードマップ Issue（#6762 [WIP] EC-CUBE 4.4 Roadmap）](https://github.com/EC-CUBE/ec-cube/issues/6762) が公開され、**`4.4` ブランチは既に動いています**。つまり「壊れるかどうか」は、今この瞬間に手元で検証できます。

この記事では、ロードマップの内容を一次ソース（実際の `composer.json` や各ライブラリの `UPGRADE.md`）と照らし合わせながら、**プラグイン開発者・カスタマイズ担当者が「今から」直せる破壊的変更**を中心に整理します。

:::message
本記事はロードマップ Issue（WIP）と、執筆時点（2026年6月）の `4.4` 開発ブランチの状態をもとにしています。**正式リリースまでに仕様が変わる可能性**があります。最新情報は必ず公式の Issue・アップグレードガイドをご確認ください。
:::

---

## EC-CUBE 4.4 の全体像

ロードマップによると、4.4 の基本方針は大きく 2 つです。

1. **Symfony 6.4 の EOSL（2027年11月）対策**として、Symfony 7.4 へバージョンアップする
2. **AI フレンドリーな機能構築**として、Agentic Commerce / AEO に対応する機能（情報フィード、MCP サーバ、skills など）を実装する

リリース目標は **2026年8月下旬**。4.4 で取り込む改修一覧は [マイルストーン 54（4.4.0）](https://github.com/EC-CUBE/ec-cube/milestone/54) で管理されています（執筆時点で 350 件超の Issue/PR が紐づいています）。

そして重要なのが、**`4.4` ブランチは既に存在している**という点です。実際にブランチの `composer.json` を見ると、依存バージョンが新世代に切り替わっていることが確認できます。

| 依存パッケージ | 4.3（`composer.json`） | 4.4 ブランチ（現時点） |
|---|---|---|
| PHP | `^8.1` | `^8.2` |
| symfony/framework-bundle | `^6.4` | `^7.4` |
| doctrine/orm | `^2.11` | `^3.0` |
| doctrine/dbal | `^3.3` | `^3.8` |
| phpunit/phpunit | （bridge 経由） | `^11.0` |

:::message
ロードマップ本文では Doctrine DBAL を「4.x」と記載していますが、執筆時点の `4.4` ブランチの `composer.json` は `^3.8` でした。開発途中のため最終的な制約は変わる可能性があります。本記事では「DBAL 4.x で何が変わるか」も後述しますが、現状はまだ DBAL 3 系である点にご注意ください。
:::

---

## システム要件の変化

まずは動作環境の変化です。プラグインのコードそのものではありませんが、サーバ要件として把握しておく必要があります。

| ミドルウェア | 4.3 | 4.4（予定） | 補足 |
|---|---|---|---|
| PHP | 8.1〜8.3 | **8.2〜8.5** | PHP 8.1 は 2025年12月に EOL のためサポート対象外 |
| PostgreSQL | 12〜16 | **13〜18** | PostgreSQL 12 は 2024年11月 EOL のため対象外 |
| MySQL | 8.0〜8.4 LTS | **8.4 LTS** | MySQL は最新対応済みのため新バージョン対応なし |
| Apache | 2.4 | 2.4 | 変更なし |

PHP に関しては公式サポート状況も確認しておきましょう（[php.net](https://www.php.net/supported-versions.php)）。

- **PHP 8.1**: セキュリティサポートは 2025年12月31日まで（執筆時点で既に終了）
- **PHP 8.4**: 2024年11月リリース。セキュリティサポートは 2028年12月31日まで
- **PHP 8.5**: 2025年11月リリース。セキュリティサポートは 2029年12月31日まで

つまり 4.4 は、**EOL を迎えた PHP 8.1 を切り捨て、最新の 8.4 / 8.5 まで対応する**という整理になっています。

---

## フレームワーク・ライブラリのメジャーアップ

ここからが本題です。プラグインに影響するのは、主に以下のメジャーバージョンアップです。

| ライブラリ | 4.3 | 4.4（予定） | EOL（セキュリティ修正終了） |
|---|---|---|---|
| Symfony | 6.4 | **7.4** | 6.4: 2027年11月 / 7.4: 2029年11月 |
| Doctrine ORM | 2.x | **3.x** | 2.x: 2027年2月以降 |
| Doctrine DBAL | 3.x | **4.x（予定）** | 未定 |
| PHPUnit | 9 | **11** | 9: 2025年2月 |
| jQuery | 3.7.x | **4.x** | 3.x: 致命的なバグ修正のみ |

Symfony 6.4 と 7.4 はどちらも LTS で、EOL は **6.4 が 2027年11月**、**7.4 が 2029年11月**です（[Symfony リリースカレンダー](https://symfony.com/releases)で確認できます）。EC-CUBE が 7.4 へ移行するのは、6.4 の EOL より前にセキュリティサポートを確保するためです。

では、それぞれのメジャーアップで「プラグインの何が壊れるのか」を見ていきます。

---

## プラグイン開発者が影響を受ける Breaking Changes

### 1. Symfony 7：アノテーション廃止、PHP Attribute へ

Symfony 7.0 では、**Doctrine annotations ライブラリの統合が削除**されました（[UPGRADE-7.0.md](https://github.com/symfony/symfony/blob/7.4/UPGRADE-7.0.md) で確認）。Routing・Validator・Serializer などで、アノテーションローダーが軒並み削除され、**PHP 8 の Attribute（属性）が必須**になります。

たとえばルーティングを書く場合、アノテーション形式はもう使えません。

```php
// ❌ 旧: アノテーション形式（Symfony 7 で動かない）
/**
 * @Route("/example", name="example")
 */
public function index()
{
}

// ✅ 新: PHP 8 Attribute
#[Route('/example', name: 'example')]
public function index()
{
}
```

バリデーションも同様です。

```php
// ❌ 旧
/**
 * @Assert\NotBlank()
 */
private $name;

// ✅ 新
#[Assert\NotBlank]
private $name;
```

加えて、`HttpKernel` / `Form` / `Validator` など多数のコンポーネントで**型宣言が厳格化**されています。たとえば `ParameterBag::getInt()` / `getBool()` は不正な値でデフォルトにフォールバックせず `UnexpectedValueException` を投げるようになりました。フォームやリクエスト処理をカスタマイズしているプラグインは、戻り値・引数の型を見直す必要があります。

### 2. Doctrine ORM 3：アノテーションマッピング廃止

Doctrine ORM 3 では、**アノテーション形式の Mapping が完全に廃止**されました（[ORM UPGRADE.md](https://github.com/doctrine/orm/blob/3.x/UPGRADE.md)）。`AnnotationDriver` が削除されており、Attribute ドライバ（または XML）への移行が必須です。

EC-CUBE のプラグインで Entity を定義・拡張している場合、マッピングは Attribute で書く必要があります。

```php
// ❌ 旧: アノテーション形式
/**
 * @ORM\Entity
 * @ORM\Table(name="plg_example")
 */
class Example
{
    /**
     * @ORM\Id
     * @ORM\Column(type="integer")
     * @ORM\GeneratedValue
     */
    private $id;
}

// ✅ 新: PHP 8 Attribute
#[ORM\Entity]
#[ORM\Table(name: 'plg_example')]
class Example
{
    #[ORM\Id]
    #[ORM\Column(type: 'integer')]
    #[ORM\GeneratedValue]
    private $id;
}
```

また、ORM 3 ではライフサイクルイベントの引数クラスが変わっています。ORM 固有の `Doctrine\ORM\Event\LifecycleEventArgs` が削除され、`PrePersistEventArgs` / `PostLoadEventArgs` のような**専用イベントクラス**へ移行が必要になります。

### 3. Doctrine の EventSubscriber → AsDoctrineListener

ロードマップには「`EventSubscriber` 形式の Doctrine リスナは廃止し、`#[AsDoctrineListener]` を用いる形に変更」とあります。これは正確には、**Symfony 7 の DoctrineBridge が subscriber タグのサポートを削除した**ことに起因します。

EC-CUBE 本体も、現状この形式を使っています。実際に `src/Eccube/Doctrine/EventSubscriber/` には以下の 3 ファイルがあり、いずれも Doctrine の `EventSubscriber` インターフェースを実装しています。

- `InitSubscriber.php`
- `SaveEventSubscriber.php`
- `TaxRuleEventSubscriber.php`

たとえば `TaxRuleEventSubscriber` は次のような構造です（4.3）。

```php
use Doctrine\Common\EventSubscriber;
use Doctrine\ORM\Events;

class TaxRuleEventSubscriber implements EventSubscriber
{
    public function getSubscribedEvents()
    {
        return [
            Events::prePersist,
            Events::postLoad,
            Events::postPersist,
            Events::postUpdate,
        ];
    }
    // ...
}
```

4.4 では、これらが `#[AsDoctrineListener]` 属性を使った Listener 形式に書き換えられる見込みです。**プラグイン側で同様に Doctrine の `EventSubscriber` を使っている場合は、Listener 形式への移行が必要**になります。

```php
// ✅ 新: AsDoctrineListener 属性
use Doctrine\Bundle\DoctrineBundle\Attribute\AsDoctrineListener;
use Doctrine\ORM\Event\PrePersistEventArgs;
use Doctrine\ORM\Events;

#[AsDoctrineListener(event: Events::prePersist)]
class ExampleListener
{
    public function prePersist(PrePersistEventArgs $args): void
    {
        // ...
    }
}
```

なお、Symfony のリクエスト/レスポンス系のイベント購読（`EventSubscriberInterface` を実装した通常の EventSubscriber）は引き続き利用できます。**廃止されるのは Doctrine の `EventSubscriber` の方**である点に注意してください。

### 4. Doctrine DBAL 4：旧 fetch API の削除

DBAL 4 では、**旧来の Result fetching API が削除**されます（[DBAL UPGRADE.md](https://github.com/doctrine/dbal/blob/4.0.x/UPGRADE.md)）。`Connection` 経由で SQL を直接実行しているプラグインは要注意です。

削除される主な API と代替は次の通りです。

```php
// ❌ 削除された API
$result->fetch();
$result->fetchAll();
$conn->query($sql);
$conn->exec($sql);
$conn->executeUpdate($sql);

// ✅ 代替メソッド
$conn->executeQuery($sql)->fetchAssociative();   // 1行を連想配列で
$conn->executeQuery($sql)->fetchAllAssociative(); // 全行を連想配列で
$conn->executeQuery($sql)->fetchFirstColumn();    // 最初のカラムのみ
$conn->executeStatement($sql);                    // INSERT/UPDATE/DELETE
```

:::message alert
ユーザー入力を含む SQL を実行する場合は、必ずプレースホルダ（バインドパラメータ）を使ってください。文字列連結は SQL インジェクションの原因になります。

```php
// ❌ 危険: 文字列を連結している
$conn->executeQuery('SELECT * FROM dtb_customer WHERE id = ' . $id);

// ✅ 安全: プレースホルダでバインドする
$conn->executeQuery(
    'SELECT * FROM dtb_customer WHERE id = :id',
    ['id' => $id]
)->fetchAssociative();
```
:::

また、`AbstractPlatform::getName()` が削除されます。データベースの種類を文字列で判定していた箇所は、**`instanceof` での判定**に書き換える必要があります。

```php
// ❌ 旧
if ($platform->getName() === 'mysql') {
    // ...
}

// ✅ 新
use Doctrine\DBAL\Platforms\AbstractMySQLPlatform;

if ($platform instanceof AbstractMySQLPlatform) {
    // ...
}
```

さらに、DBAL 4 では **decimal カラムの precision/scale のデフォルト値が廃止**され、明示指定が必要になりました。これが次の「金額計算」の話につながります。

### 5. 金額計算：実は 4.3 から string ＆ BCMath

ロードマップには「`Order` / `OrderItem` などの DECIMAL 型プロパティを `?string` に統一」「金額計算は `bcmath` 関数に置き換え」とあります。ここは誤解しやすいので、実際のソースを確認しておきましょう。

**実は EC-CUBE 4.3 の時点で、金額系プロパティは既に `string` を返します。** `src/Eccube/Entity/Order.php` を見ると、`getTotal()` / `getPaymentTotal()` / `getSubtotal()` などはすべて `@ORM\Column(type="decimal", precision=12, scale=2)` で定義され、戻り値は文字列です。

さらに、`OrderItem` の計算ロジックも既に BCMath を使っています。

```php
// src/Eccube/Entity/OrderItem.php（4.3）より抜粋
public function getPriceIncTax()
{
    // 税表示区分が税込の場合は, price に税込金額が入っている.
    if ($this->TaxDisplayType && $this->TaxDisplayType->getId() == TaxDisplayType::INCLUDED) {
        return $this->price;
    }

    return bcadd($this->price, $this->tax, 2);
}

public function getTotalPrice()
{
    return bcmul($this->getPriceIncTax(), $this->getQuantity(), 2);
}
```

`bcadd()` / `bcmul()` の第3引数 `2` がスケール（小数点以下の桁数）です。金額計算は文字列入力・文字列出力で完結しています。

つまり、**EC-CUBE はもともと「金額は文字列で扱い、計算は BCMath で行う」設計**です。4.4 で型宣言がより厳格になるため、この方針が一層徹底されると考えればよいでしょう。

**やってはいけないのは、プラグイン側で金額を `int` / `float` として受け取って計算してしまうこと**です。

```php
// ❌ 危険: float にキャストすると誤差が出る／型エラーの原因に
$total = (float) $order->getTotal();
$newTotal = $total * 1.1;

// ✅ 安全: 文字列のまま BCMath で計算
$newTotal = bcmul($order->getTotal(), '1.1', 2);
```

金額計算を行っているプラグインは、**float を経由していないか**を今のうちに確認しておきましょう。

### 6. PHPUnit 11：DataProvider は static 必須

プラグインにテストコードを書いている場合、PHPUnit 9 → 11 の変更も影響します（[PHPUnit 公式ドキュメント](https://docs.phpunit.de/en/11.5/)）。

- **DataProvider メソッドは `public` かつ `static` が必須**になりました。
- アノテーション（`@dataProvider` など）は非推奨となり、**Attribute（`#[DataProvider]`）への移行**が推奨されます。アノテーションは **PHPUnit 12 で削除予定**です。

```php
// ❌ 旧
/**
 * @dataProvider additionProvider
 */
public function testAddition($a, $b, $expected)
{
    // ...
}

public function additionProvider()  // 非 static
{
    return [[1, 2, 3], [0, 0, 0]];
}

// ✅ 新
use PHPUnit\Framework\Attributes\DataProvider;

#[DataProvider('additionProvider')]
public function testAddition($a, $b, $expected)
{
    // ...
}

public static function additionProvider()  // static 必須
{
    return [[1, 2, 3], [0, 0, 0]];
}
```

### 7. jQuery 4：実際に削除される API を正しく把握する

ロードマップには jQuery 3.7 → 4.x の廃止 API として `.bind()` / `.unbind()` / `.delegate()` / `.undelegate()` / `.size()` / `.parseJSON()` などが挙げられています。

ただし、[jQuery 4.0 公式アップグレードガイド](https://jquery.com/upgrade-guide/4.0/) を確認すると、ここは正確に区別しておく必要があります。

- **`.size()`** は jQuery **3.0 で既に削除済み**です（4.0 の新規削除ではありません）。代わりに `.length` を使います。
- **`.bind()` / `.unbind()` / `.delegate()` / `.undelegate()`** は jQuery 3.0 で**非推奨（deprecated）**になっていますが、4.0 でも完全には削除されていません。いずれにせよ将来削除されるため、`.on()` / `.off()` への移行が推奨です。
- **`$.parseJSON()`** は jQuery **4.0 で削除**されます。`JSON.parse()` を使います。

そのほか、4.0 では以下のユーティリティが削除されます（移行先も記載）。

```js
// ❌ → ✅ jQuery 4.0 で削除されるユーティリティの例
$.isArray(x)     → Array.isArray(x)
$.isFunction(x)  → typeof x === 'function'
$.now()          → Date.now()
$.trim(str)      → str.trim()
$.parseJSON(str) → JSON.parse(str)
$.unique(arr)    → $.uniqueSort(arr)
```

また `$.ajax` の挙動も変わり、JSONP を使う場合は `dataType: "jsonp"` の明示が必要になるなど、いくつか仕様変更があります。**独自テンプレートやプラグインで古い jQuery API を使っている場合は、`.on()` 系・ネイティブ JS への置き換え**を進めておきましょう。

---

## 移行支援：同梱の rector.php を使う

ここまで読むと「修正箇所が多すぎる」と感じるかもしれませんが、**機械的な書き換えの大部分は自動化できます**。

EC-CUBE のリポジトリには **`rector.php` が同梱**されています（`4.3` ブランチ・`4.4` ブランチの両方で確認できます）。[Rector](https://github.com/rectorphp/rector) は PHP のコードを自動でリファクタリング・アップグレードするツールで、Symfony / Doctrine / PHP のメジャー更新に伴う書き換え（アノテーション → Attribute など）をかなりの部分まで自動化できます。

4.3 同梱の `rector.php` では、対象 PHP バージョンや適用ルールセット（`DEAD_CODE`、`UP_TO_PHP_80`、`PHPUNIT_90` など）が設定されています。4.4 移行にあたっては、Symfony・Doctrine・PHP それぞれのルールセットを有効化して実行することで、手作業を大きく減らせます。

```bash
# Rector で差分を確認（dry-run）
vendor/bin/rector process --dry-run

# 実際に適用
vendor/bin/rector process
```

:::message alert
`vendor/bin/rector process`（`--dry-run` なし）は**ソースファイルを直接上書き**します。実行前に必ず変更を Git にコミットするか、バックアップを取ってください。また、Rector の実行は**ローカル／開発環境で行い、本番環境では実行しない**でください。
:::

:::message
Rector は万能ではありません。マッピングや型宣言など機械的な変換はカバーできますが、**ロジックの修正（float 計算の見直しや、Doctrine リスナの再設計など）は手作業が必要**です。Rector で大枠を変換 → 残りを手作業、という二段構えが現実的です。
:::

詳しい移行手順は、別途公開予定の **「EC-CUBE 4.3 → 4.4 アップグレードガイド」** に記載されるとのことなので、こちらも要チェックです。

---

## AI 機能（4.4 新規）

4.4 のもう一つの柱が **AI（Agentic Commerce / AEO）対応**です。ロードマップでは以下が予定されています。

- **ACP / UCP 対応のサイト・商品フィード**：AI エージェントが商品情報を取得・提示するためのフィード出力機能
- **リードオンリーの MCP（Model Context Protocol）サーバ機能**：外部 AI から商品・在庫などを参照するためのインターフェース（**書き込み系の操作は対象外**）
- 各種インデックス・定義ファイルの配置

「AEO（Answer Engine Optimization）」は、AI による検索・回答エンジンに対して自社の商品情報を正しく提示するための最適化を指します。AI エージェント経由で商品が発見・購入される時代を見据えた機能、という位置づけです。

マイルストーンには、UCP checkout のコア実装や MCP サーバ実装の PR が既に登録されています。ただし、**参照する仕様のバージョンや認証・認可モデルの詳細は、要件定義が固まり次第追記される**とのことなので、現時点では「そういう方向で動いている」と捉えておくのがよいでしょう。

:::message
MCP（Model Context Protocol）は、AI モデルが外部のデータやツールへアクセスするための標準プロトコルです。EC-CUBE 4.4 では、まず**読み取り専用**で商品・在庫情報を AI に提供する形で提供される予定です。
:::

---

## 今から準備できること（チェックリスト）

正式リリースは 2026年8月下旬予定ですが、**4.4 ブランチは既に動いています**。今からできる準備をまとめます。

- [ ] 手元のプラグインを **`4.4` ブランチの EC-CUBE で動かしてみる**（一番効果的）
- [ ] Entity マッピングを **アノテーション → PHP 8 Attribute** に書き換える
- [ ] ルーティング・バリデーションの **アノテーションを Attribute 化**する
- [ ] Doctrine の **`EventSubscriber` を `#[AsDoctrineListener]` 形式**に移行する
- [ ] `Connection::query()` / `fetch()` / `fetchAll()` など **DBAL の旧 API を新 API に置き換え**る
- [ ] `Platform::getName()` での DB 判定を **`instanceof` 判定**に変更する
- [ ] 金額計算で **`float` を経由していないか**確認し、BCMath ＋文字列に統一する
- [ ] PHPUnit の **DataProvider を `static` 化＋`#[DataProvider]` 属性**に移行する
- [ ] テンプレートの **古い jQuery API（`$.parseJSON` 等）を置き換え**る
- [ ] **`rector.php` を実行**して、自動変換できる箇所をまとめて処理する

特に最初の「4.4 ブランチで動かしてみる」が最も確実です。エラーが出た箇所こそが、あなたのプラグインで修正が必要な箇所だからです。

---

## まとめ

EC-CUBE 4.4 は、**Symfony 7.4 / Doctrine ORM 3 / PHP 8.4・8.5 という新世代フレームワークへの土台移行**が主軸のメジャーバージョンです。プラグイン開発者にとっては、

- アノテーション → **PHP Attribute** への全面移行
- Doctrine の **リスナ方式の変更**
- DBAL の **旧 API 削除**
- 金額計算の **型・BCMath の徹底**
- テスト・jQuery の **API 変更**

といった対応が必要になります。一見大変ですが、**多くは `rector.php` で自動化でき、金額計算など一部のロジックだけ手作業**という構造です。

正式リリースは 2026年8月下旬予定。**今のうちから 4.4 ブランチで自分のプラグインを動かし、修正ポイントを洗い出しておく**ことが、スムーズな移行への一番の近道です。

---

## あなたはどう動きますか？

- すでに 4.4 ブランチで動作確認した方、**どこが一番ハマりましたか？**
- 「Rector でここまで自動化できた／できなかった」という知見があれば、ぜひコメントで共有してください。
- そもそも 4.4 の **AI（MCP）対応**、現場で使うと思いますか？ 期待・不要、意見が割れそうなところです。

コメント欄やシェア時のひとことで、ぜひ教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
