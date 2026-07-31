---
title: "EC-CUBE 4.4でEntityの if (!class_exists()) が全廃される。あの謎ガードの正体"
emoji: "🧹"
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
この記事は EC-CUBE 4.4 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## 結論: EC-CUBE 4.4で、全Entityを覆っていたあのガードが消えます

EC-CUBE のソースを初めて開いたとき、自分が最初に引っかかったのがこれでした。`src/Eccube/Entity/` 配下の全 Entity が、こう書かれています。

```php
namespace Eccube\Entity;

if (!class_exists(Category::class)) {
    /**
     * Category
     *
     * @ORM\Table(name="dtb_category")
     * @ORM\Entity(repositoryClass="Eccube\Repository\CategoryRepository")
     */
    class Category extends AbstractEntity
    {
        // ...
    }
}
```

クラス定義全体が `if (!class_exists())` でくるまれ、その分だけインデントが1段深い。IDE のクラス補完も効きにくく、`git diff` は無駄に大きくなる。自分もプラグインを作るとき、本体がこう書いてるからという理由だけで同じガードを写経していました。理由は分かっていませんでした。

このガードが、[PR #6895](https://github.com/EC-CUBE/ec-cube/pull/6895)（`4.4` ブランチに 2026年7月15日マージ済み）で **全廃** されました。差分は `+14,030 / -13,968`、76ファイル。コア 71 クラスからガードが消えています。

**TL;DR**

- EC-CUBE 4.4 で `src/Eccube/Entity/` の `if (!class_exists())` ガードが全廃される（[PR #6895](https://github.com/EC-CUBE/ec-cube/pull/6895)）
- ガードの正体は、元ソースと `app/proxy/entity` 配下の proxy という**同一 FQCN の2ファイル**を `require_once` したときの redeclare fatal 回避
- `EntityProxyService::scanTraits()` と `TraitProxyAttributeDriver` を proxy 対応にすることでガードを不要にした。**ただしこれでは足りず、マージ後に回帰バグが出た。2026年7月31日に修正がマージされて解決済み**（後述）
- 副作用として、`app/Customize/Entity` に置いた単独 Entity を trait 拡張しても列がマッピングされない潜在バグも同時に解消された
- プラグイン生成コマンドのスケルトンが吐くガードは、このPRには含まれていない（`4.4` ブランチでも現存）

:::message alert
**追記（2026年7月31日）修正がマージされ、解決しました**

この記事の主題である #6895 は、マージ後に回帰バグが見つかりました。ガードを外した結果、特定の構成で `Cannot declare class` が発生し、全リクエストと `cache:clear` が失敗する状態でした。

自分でも手元で再現させ、最初の修正案では塞ぎきれない経路を見つけて報告しました（[#6979](https://github.com/EC-CUBE/ec-cube/issues/6979)）。方式を変えた [#6982](https://github.com/EC-CUBE/ec-cube/pull/6982) が 2026年7月31日に `4.4` へマージされ、Issue もクローズされています。**現在の `4.4` ブランチにこのバグは残っていません。** 経緯は末尾の「その後、回帰バグが見つかった」に書いています。
:::

## そもそも、なぜあのガードが必要だったのか

EC-CUBE の Entity 拡張の仕組みを思い出してください。プラグインは `#[EntityExtension]` を付けた trait を用意することで、コアの Entity にカラムを追加できます。

```php
namespace Plugin\YourPlugin\Entity;

use Doctrine\ORM\Mapping as ORM;
use Eccube\Attribute\EntityExtension;

#[EntityExtension(\Eccube\Entity\Product::class)]
trait ProductTrait
{
    #[ORM\Column(name: 'your_field', type: 'string', nullable: true)]
    private ?string $yourField = null;
}
```

このとき `eccube:generate:proxies` が走ると、EC-CUBE は **元の Entity ソースに trait の `use` 文を差し込んだコピー** を `app/proxy/entity/src/Eccube/Entity/Product.php` に書き出します。以降 Doctrine が読むのは proxy 側です。

ここに問題があります。**元ソースと proxy は、まったく同じ FQCN（`Eccube\Entity\Product`）を持つ別ファイル**なのです。PHP は同じクラス名を2回宣言できません。両方を `require_once` してしまうと、次の fatal で即死します。

```
PHP Fatal error: Cannot declare class Eccube\Entity\Product, because the name is already in use
```

`require_once` はファイルパス単位での重複排除しかしてくれないので、パスが違えば普通に2回読み込まれてしまいます。そこで **クラス名単位** で二重宣言を止める盾として `if (!class_exists(Product::class))` が全 Entity に貼られていた、というのが正体です。

Issue としては [#5844](https://github.com/EC-CUBE/ec-cube/issues/5844)（プラグイン Entity 拡張時の二重宣言）が根本原因、[#6891](https://github.com/EC-CUBE/ec-cube/issues/6891) が実現計画にあたります。

## `require_once` はどこで起きているのか

PR #6895 のアプローチは、ガードを外す前に `require_once` が起きる箇所をすべて proxy 対応にする、というものです。PR 本文（Draft 作成時点の整理）では、対象は4箇所とされています。

| 箇所 | 対象 | PR本文での整理 |
| --- | --- | --- |
| `Kernel::loadEntityProxies()` | proxy 全体 | 変更不要（booted フラグ＋パス重複排除で対応済み） |
| `ReloadSafeAttributeDriver` | コアの `src/Eccube/Entity` | 変更不要（トークン解析＋新規 proxy のランダム改名で回避済み・ガード非依存） |
| `TraitProxyAttributeDriver` | Plugin | 変更不要（proxy 優先 require・パス重複排除） |
| `EntityProxyService::scanTraits()` | Customize / Plugin の Entity | 本PRで修正 |

ただしこの表は Draft 時点のもので、**実際にマージされた差分では `TraitProxyAttributeDriver` にも修正が入っています**（+86/-12）。調査 Issue の [#6891](https://github.com/EC-CUBE/ec-cube/issues/6891) にも「全廃するには4箇所すべてを個別に安全化する必要があり、1箇所のみの修正では不十分」と書かれており、そちらのほうが結果に即しています。

つまり、ガードに実際に依存していたのは `EntityProxyService::scanTraits()` と `TraitProxyAttributeDriver` の2箇所でした。

:::message alert
そして、この整理には**5箇所目が抜けていました**。doctrine-bundle の `auto_mapping` が生成する素の `AttributeDriver` です。EC-CUBE のコードには現れないので、コアのソースを追うだけでは見つかりません。これが後述の回帰バグの原因になります。
:::

:::message
表の「対象」列も PR 本文の整理をそのまま引いたものです。実際には 4.4 の `Kernel::addEntityExtensionPass()` はコアの `src/Eccube/Entity` にも `TraitProxyAttributeDriver` を使っており、`ReloadSafeAttributeDriver` はその継承クラスです。
:::

## 修正の中身: 宣言済みならスキップする

`EntityProxyService::scanTraits()` は、`app/Plugin/*/Entity` や `app/Customize/Entity` 配下の PHP ファイルを Finder で拾って片っ端から `require_once` し、`get_declared_traits()` で `#[EntityExtension]` 付きの trait を探すメソッドです。ここで元ソースを読み込んだ結果、proxy 側と衝突していました。

4.4 の実装はこうなっています（`src/Eccube/Service/EntityProxyService.php`）。

```php
foreach ($files as $file) {
    $realPath = $file->getRealPath();
    $includedFiles[] = $realPath;
    // 既にProxy等でロード済みのEntityクラスを再度require_onceすると
    // "Cannot redeclare class" になるため、宣言済みならスキップする.
    // 対象は Entity ディレクトリ配下 (app/Plugin/*/Entity, app/Customize/Entity) に限定する.
    // Plugin が同梱するライブラリ (例: phpseclib) 等の非Entityファイルは
    // 偽のFQCNを組み立てないよう対象外とし、従来どおり require_once する.
    $normalized = str_replace('\\', '/', $realPath);
    if (preg_match('#/app/(Customize/Entity/[^.]+|Plugin/[^/]+/Entity/[^.]+)\.php$#', $normalized, $matches)) {
        $fqcn = str_replace('/', '\\', $matches[1]);
        if (class_exists($fqcn, false)) {
            continue;
        }
    }
    require_once $realPath;
}
```

ポイントは2つあります。

**1つめ**は `class_exists($fqcn, false)` の第2引数です。`false` を渡すとオートローダーを起動せず、いま実際にメモリ上で宣言済みかどうかだけを見ます。ここで `true`（デフォルト）にしてしまうと、判定のためにオートローダーが走って結局ファイルを読み込みかねません。二重宣言判定でこの引数を落とすのは典型的なバグなので、自作コードで似た判定を書くときも気をつけたいところです。

**2つめ**は、パス→FQCN の変換を `Entity` ディレクトリ配下に限定している点です。`app/Plugin/YourPlugin/phpseclib/bootstrap.php` のような同梱ライブラリまで機械的に FQCN 化すると、実在しない `Plugin\YourPlugin\phpseclib\bootstrap` を組み立てることになります。ここは限定しておかないと事故ります。

なお PR 本文によると、[#5844](https://github.com/EC-CUBE/ec-cube/issues/5844) のコメントで提案されていた案は `app/Plugin` 限定でしたが、実測で `app/Customize` を取りこぼして fatal が残ったため、`Plugin|Customize` 両対応になっています。

## `TraitProxyAttributeDriver` 側の対応

`TraitProxyAttributeDriver::getAllClassNames()` にも同じ考え方が入りました（+86/-12）。PR 適用前のこのメソッドは `require_once $proxyFile;` / `require_once $sourceFile;` を無条件に実行しているだけで、`class_exists` 判定を持っていませんでした。

```php
// ソースファイルからFQCNを取得し、未宣言のクラスだけをロードする.
// Proxy(app/proxy/entity)と元ソースは同一FQCNを持つため、既にロード済み
// (例: Kernel::loadEntityProxies)の状態で require_once すると
// "Cannot redeclare class" になる. 旧実装では各Entityの if (!class_exists())
// ガードがこれを吸収していた.
$classNames = $this->extractClassNames($sourceFile);
if ($classNames === []) {
    // interface / trait 等 (Entity以外) はそのままロードする
    require_once $sourceFile;
    $includedFiles[] = realpath($sourceFile);
    continue;
}

$undeclared = array_filter($classNames, static fn ($fqcn) => !class_exists($fqcn, false));
if ($undeclared !== []) {
    require_once $sourceFile;
}
```

コメントに「旧実装では各Entityの `if (!class_exists())` ガードがこれを吸収していた」とはっきり書かれていて、何を代替したのかが読み取れます。

## Customize の単独Entityが trait 拡張できなかった件

個人的にこのPRで一番おいしいのはここです。

#6895 では、`Kernel::addEntityExtensionPass()` の Customize 用ドライバが、標準の attribute マッピングドライバから `TraitProxyAttributeDriver` に差し替えられました。PR 適用前の 4.4 はこうでした。

```php
// 4.4（PR #6895 適用前）: src/Eccube/Kernel.php
// Customize
$container->addCompilerPass(DoctrineOrmMappingsPass::createAttributeMappingDriver(
    ['Customize\\Entity'],
    ['%kernel.project_dir%/app/Customize/Entity']
));
```

ちなみに 4.3 は、まだアノテーション時代なので `createAnnotationMappingDriver()` の同等コードです。いずれにせよ Symfony/Doctrine 標準のマッピングドライバをそのまま使っていた、という構図は同じです。

PR 適用後は、コア・Plugin と同じドライバに統一されました。

```php
// 4.4: src/Eccube/Kernel.php
// Customize
$customizePaths = ['%kernel.project_dir%/app/Customize/Entity'];
$customizeNamespaces = ['Customize\\Entity'];
$customizeDriver = new Definition(TraitProxyAttributeDriver::class, [$customizePaths]);
$customizeDriver->addMethodCall('setTraitProxiesDirectory', [$projectDir.'/app/proxy/entity']);
$container->addCompilerPass(new DoctrineOrmMappingsPass($customizeDriver, $customizeNamespaces, []));
```

標準ドライバは proxy を知らないので、`app/Customize/Entity` に置いた独自 Entity のマッピングは常に元ソースから読まれていました。つまり `#[EntityExtension(\Customize\Entity\Foo::class)]` な trait で自分の Entity を拡張しても、**その拡張列が Doctrine のメタデータに乗らない**。proxy には trait が差し込まれているのに、ドライバが proxy を見ていないので気付かない、という噛み合わせの悪さです。

`TraitProxyAttributeDriver` に統一されたことで、proxy が存在すればそちらを読むようになり、この挙動が直りました。PR 本文でも「既存の潜在バグも同時に解消」と明記されています。

ただしこれは裏を返すと、既存の動作が変わるということでもあります。PR 本文の互換性チェックリストでも「既存機能の仕様変更はありません」に意図的にチェックが入っておらず、Discussion で相談事項として挙げられています。`app/Customize/Entity` に単独 Entity を置いていて、かつそれを trait 拡張している構成の方は、4.4 移行時にスキーマ差分が出ないか確認しておくと安全です。

## プラグイン開発者への影響

### 自作プラグインの Entity にガードを書いている場合

まず落ち着いてください。**すぐに壊れるわけではありません。** ガードは二重宣言を防ぐためのもので、あって困るものではありません。4.4 でコア側の `require_once` 経路が proxy 対応になった結果、不要になったというだけです。

しかも 4.4 の `EntityProxyService` には `removeClassExistsBlock()` が残っており、proxy 生成時にガードのブロックを剥がします。つまりプラグイン側にガードが残っていても、proxy には持ち込まれません。

とはいえ、ガードがあると以下が地味に効いてきます。

- クラス定義が1段深くインデントされ、IDE の解析・補完が弱くなる
- PHPStan などの静的解析でクラスが条件付き定義の扱いになる
- コアの書き方と揃わなくなる

4.4 対応のタイミングで外していく方向で問題ありません。外す場合は `eccube:generate:proxies` の連続実行と `cache:clear` を通し、`doctrine:mapping:info` で拡張列がメタデータに乗っていることを確認してください。PR でもこの3コマンドで fatal 0 を確認したと報告されています。

:::message
なお、`eccube:plugin:generate` が生成するスケルトンはこのPRの対象外です（PR 本文に「本PRには未含」と明記。ガードを入れた当のPRは [#4719](https://github.com/EC-CUBE/ec-cube/pull/4719)）。実際、この記事を書いている時点の `4.4` ブランチでも `src/Eccube/Command/PluginGenerateCommand.php` は `if (!class_exists('\Plugin\{code}\Entity\Config', false)) {` を吐き続けています。リリースまでに変わる可能性はあるので、実リリース版でご確認ください。
:::

### コア Entity を `require` している自作コードがある場合

これは要注意です。もし自作コードで `src/Eccube/Entity/Foo.php` を直接 `require` / `require_once` している箇所があるなら、ガードが消えた 4.4 では、そこが**二重宣言 fatal の発火点**になり得ます。

これまでは Entity 側のガードが、誰がどこから読み込んでも安全という保険になっていました。その保険がなくなります。Entity は Composer のオートローダー（と proxy ロード）に任せ、手動 `require` はやめる、が 4.4 での正解です。

なお、この点は PR や Issue に直接の記述があるわけではなく、実装から読み取れる範囲での注意喚起です。

## Entity の attribute 化

4.4 の Entity はアノテーション（`@ORM\Table`）から PHP 8 の attribute（`#[ORM\Table]`）へ移行済みです。これは #6895 単独の変更ではなく、Doctrine ORM 3 対応を含む 4.4 ブランチ全体の流れによるものですが、ガード撤廃と合わせると Entity の見た目はこう変わります。

```php
// 4.3
if (!class_exists(Category::class)) {
    /**
     * @ORM\Table(name="dtb_category")
     * @ORM\Entity(repositoryClass="Eccube\Repository\CategoryRepository")
     */
    class Category extends AbstractEntity
    {
        /**
         * @return string
         */
        public function __toString()
        {
            return (string) $this->getName();
        }
    }
}
```

```php
// 4.4
#[ORM\Table(name: 'dtb_category')]
#[ORM\InheritanceType('SINGLE_TABLE')]
#[ORM\DiscriminatorColumn(name: 'discriminator_type', type: 'string', length: 255)]
#[ORM\HasLifecycleCallbacks]
#[ORM\Entity(repositoryClass: CategoryRepository::class)]
class Category extends AbstractEntity implements \Stringable
{
    #[\Override]
    public function __toString(): string
    {
        return $this->getName();
    }
}
```

`@return string` の PHPDoc が実際の戻り値型宣言になり、`\Stringable` と `#[\Override]` が入り、`repositoryClass` が文字列から `::class` 定数になっています。IDE のジャンプもリファクタリングも効くようになるので、実装を読むのがかなり楽になります。

## その後、回帰バグが見つかった

ここからは公開後の追記です（2026年7月27日に追記、7月31日に決着を反映）。

#6895 のマージから9日後、[PR #6963](https://github.com/EC-CUBE/ec-cube/pull/6963) が出ました。**#6895 の回帰バグ修正**です。ガードを外したことで、こうなる環境が出ました。

```
PHP Fatal error: Cannot declare class Eccube\Entity\Customer,
because the name is already in use in src/Eccube/Entity/Customer.php on line 49
```

Proxy 生成後、全リクエストが 500 になります。`cache:clear` も通りません。

### 原因は5箇所目の `require_once`

上で「`require_once` が起きるのは4箇所」と書きましたが、5箇所目がありました。`doctrine.orm.auto_mapping: true` です。

doctrine-bundle は auto_mapping が有効なとき、登録済みの全バンドルについて「Bundle クラスが置かれたディレクトリに `Entity/` があるか」を見て、あれば自動でマッピング対象にします。`EccubeBundle` のクラスファイルは `src/Eccube/EccubeBundle.php` なので、`src/Eccube/Entity` が引っかかります。

そしてこのドライバは素の `AttributeDriver` で、`ColocatedMappingDriver::getAllClassNames()` が Entity ソースを無条件に `require_once` します。`Kernel::__construct()` が `loadEntityProxies()` を呼んで proxy を先にロードしているので、そこで二重宣言になります。

厄介なのは、このドライバが EC-CUBE のコードに一切現れないことです。doctrine-bundle が設定から生成します。コアのソースを `grep` しても出てきません。ガードは、この見えない経路まで黙って吸収していたわけです。

### 発生条件

条件が2つ揃ったときだけ起きます。

1. コア Entity を trait 拡張するプラグインが入っている（＝ proxy が生成されている）
2. **Entity を持つ第三者バンドルが別に入っている**

2 が要るのは、doctrine-bundle が auto_mapping 対象のパスを1つのドライバインスタンスに集約するからです。チェーンに登録される名前空間は EC-CUBE 側の明示登録で上書きされますが、同じインスタンスが別の名前空間で残っていると、`getAllClassNames()` が自分の持つ全パスを走査してしまいます。

実務的には、条件2は API プラグイン（`ec-cube/api44`）を入れれば成立します。`league/oauth2-server-bundle` が付いてくるからです。決済プラグイン + API プラグインという、ごく普通の構成で踏みます。

### 最初の修正案（#6963）と、その穴

最初に出た [#6963](https://github.com/EC-CUBE/ec-cube/pull/6963) は `doctrine.yaml` の6行でした。

```yaml
    orm:
        auto_mapping: true
        mappings:
            EccubeBundle: false
```

auto_mapping 全体ではなく `EccubeBundle` だけを無効化します。コアの Entity は `Kernel::addEntityExtensionPass()` が `TraitProxyAttributeDriver` で明示登録しているので、auto_mapping による登録は要りません。

これで直るのか確かめたくて、`4.4`（`89dec55c49`）をローカルに立てて実際に踏ませてみました。DB のインストールは不要で、`composer install` して `cache:warmup` を叩くだけで確認できます。

| 構成 | 結果 |
| --- | --- |
| #6963 未適用 + Entity 付き第三者バンドル + コア proxy | `Cannot declare class Eccube\Entity\Category` |
| #6963 適用 | OK |
| **#6963 適用 + ルート直下に Bundle を置いたプラグイン** | **`Cannot declare class Plugin\Foo\Entity\Bar`** |
| **#6963 適用 + `app/Customize` 直下に Bundle** | **`Cannot declare class Customize\Entity\MyThing`** |

3行目と4行目が落ちました。#6963 では塞ぎきれない経路が残っていたわけです。

`Kernel::registerBundles()` は `EccubeBundle` だけでなく、`app/Plugin/<Code>/Resource/config/bundles.php` と `app/Customize/Resource/config/bundles.php` からもバンドルを登録します。判定基準は上と同じなので、`app/Plugin/Foo/FooBundle.php` + `app/Plugin/Foo/Entity/` という配置だと `EccubeBundle` とまったく同じ二重登録になります。

`mappings: EccubeBundle: false` はバンドル名を名指しする方式なので、サードパーティ製プラグインのバンドル名は事前に書けません。この経路は原理的に塞げないことになります。

確認した範囲では、公式プラグインにこの配置のものはありませんでした。API プラグインは `ApiBundle` を `Bundle/` サブディレクトリに置いているため、たまたま該当しません。ただし置き場所を規約で縛っているわけではないので、たまたま助かっているだけです。

これを [Issue #6979](https://github.com/EC-CUBE/ec-cube/issues/6979) として報告しました。

### 決着: コンパイル時にパスを剥がす（#6982）

報告の翌日、方式を変えた [PR #6982](https://github.com/EC-CUBE/ec-cube/pull/6982) が出ました。#6963 はクローズされ、こちらに置き換わっています。

バンドル名を列挙するのをやめ、**`Kernel::addEntityExtensionPass()` が明示登録した Entity ディレクトリを、コンパイル時に auto_mapping 側のドライバの `paths` から取り除く**方式です（`StripAutoMappedEntityPathsPass`）。

```php
$container->addCompilerPass(
    new StripAutoMappedEntityPathsPass($explicitlyMappedPaths),
    PassConfig::TYPE_BEFORE_OPTIMIZATION,
    -1001
);
```

剥がすパスは、明示登録に使った配列をそのままコンパイラパスへ渡しています。登録先が将来増えても剥がす側が自動で追従するので、パスの二重管理が起きません。第三者バンドルのパスは残るため、`league/oauth2-server-bundle` などの Entity は従来どおりマッピングされます。

こちらも手元で確認しました。上の3ケースはすべて解消し、素の構成でもマッピング数に増減はありませんでした。同一プラグイン内に「剥がす対象」と「残す対象」を同居させるケース、プロジェクトをシンボリックリンク経由で参照するケースも通っています。

この PR は **2026年7月31日に `4.4` へマージされました**。報告した #6979 も同時にクローズされています。

差分は10ファイル `+944 / -0` で、削除行がゼロです。新規のコンパイラパスが170行、`Kernel.php` への追加が15行、残り759行はテストとフィクスチャでした。既存の行を1行も書き換えずに塞いだことになります。

`doctrine.yaml` には手が入っていません。#6963 の `EccubeBundle: false` は取り込まれず、バンドル名を名指しする方式は消えました。

### 4.4 リリース時にどうなっているか

一連の経緯は #6895（ガード全廃）→ #6963（コアだけ塞ぐ）→ #6979（穴の報告）→ #6982（一般化して塞ぐ）という流れです。#6982 の方式ならバンドル名に依存しないので、同じ系統の再発は起きにくいはずです。回帰テストも `AutoMappedEntityPathsBootTest` として入ったので、直下バンドル構成で boot まで通ることが CI で守られます。

`4.4` はまだリリース前です。#6895 は76ファイル `+14,030/-13,968` の大規模変更なので、リリースまでに別の踏み方が出てくる可能性は残ります。ガード全廃を前提にした対応を進めるなら、実リリース版で最終確認してください。

### 何が教訓か

自分がこの記事を書いたとき、コアのソースを追って「`require_once` は4箇所」と整理しました。実際には5箇所目があり、それはフレームワークが設定から生成するもので、コアのコードには現れませんでした。

アプリケーションのコードだけを読んで挙動を把握したつもりになるのは危ういです。とくに Symfony のように、設定からサービスが生成されるフレームワークでは。今回は `bin/console debug:container` や実際に動かす手順を踏むまで、この経路に気づけませんでした。

## まとめ

- EC-CUBE 4.4 でコア Entity の `if (!class_exists())` ガードが全廃される（[PR #6895](https://github.com/EC-CUBE/ec-cube/pull/6895)）
- ガードは元ソースと proxy の同一 FQCN 二重宣言を防ぐためのもので、`EntityProxyService::scanTraits()` と `TraitProxyAttributeDriver` を proxy 対応にすることで不要になった
- `class_exists($fqcn, false)` の第2引数 `false` が肝。オートローダーを起動せずに、宣言済みかどうかだけを見る
- 副作用で `app/Customize/Entity` の単独 Entity が trait 拡張できるようになった（挙動が変わるので移行時は確認推奨）
- 自作プラグインのガードは急いで外す必要はないが、コア Entity を手動 `require` しているコードがあれば 4.4 では危険
- `eccube:plugin:generate` のスケルトンには、`4.4` ブランチ時点でまだガードが残っている
- **マージ後に回帰バグが出たが、[#6982](https://github.com/EC-CUBE/ec-cube/pull/6982) が2026年7月31日にマージされて解決済み**（経緯: [#6963](https://github.com/EC-CUBE/ec-cube/pull/6963) → [#6979](https://github.com/EC-CUBE/ec-cube/issues/6979) → #6982）

:::message alert
EC-CUBE 4.4 はこの記事を書いている時点（2026年7月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
