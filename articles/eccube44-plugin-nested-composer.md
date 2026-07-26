---
title: "8年間眠っていたEC-CUBEの地雷。プラグイン同梱ライブラリでcache:clearが落ちる"
emoji: "💥"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "di"]
published: false
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

## 結論: このエラーを見たことがある人、あなたは悪くありません

```
Expected to find class "Plugin\AmazonPayV2_42_Bundle\phpseclib\bootstrap"
in file ".../app/Plugin/AmazonPayV2_42_Bundle/phpseclib/bootstrap.php"
while importing services from resource "../../../app/Plugin/*", but it was not found!
```

プラグインを入れた瞬間、`cache:clear` も `cache:warmup` も `doctrine:schema:update` も通らなくなる。管理画面すら開けない。エラーメッセージはこのファイルにこのクラスが無いと言っているが、そんなクラスは最初から存在しない。自分のプラグインが悪いのかと疑いたくなりますが、悪いのはコアです。

このバグ、**2017年12月18日のコミット（`8633b4679b`）から存在していた潜在バグ**です。EC-CUBE 4 系がリリースされるより前から、ずっとそこにありました。[PR #6917](https://github.com/EC-CUBE/ec-cube/pull/6917)（`4.4` ブランチに 2026年7月15日マージ済み）でようやく修正されています。

**TL;DR**

- 原因は `services.yaml` の `Plugin\` ブロックが `app/Plugin/*` を PSR-4 で総なめすること
- プラグインが同梱する **非 PSR-4 のライブラリファイル**（phpseclib の `bootstrap.php` など）まで拾ってしまう
- Symfony DI の `FileLoader::registerClasses` がクラスを見つけられず例外を投げ、コンテナビルドが死ぬ
- Symfony **4.4 / 5.4 / 6.4 / 7.4 の全世代で同一に再現**（Symfony のバージョンアップによる回帰ではない）
- 4.4 では `Plugin\` の登録を `services.php` へ移し、**ネストした `composer.json` を検出して動的に exclude** する
- 副産物として `services.yaml` の `_defaults` の `bind` が届かなくなるため、**名前付きオートワイヤリング別名** が追加された

## なぜ落ちるのか

EC-CUBE 4.3 の `app/config/eccube/services.yaml` には、プラグインを DI コンテナに自動登録するこのブロックがあります。

```yaml
    Plugin\:
        resource: '../../../app/Plugin/*'
        exclude: '../../../app/Plugin/*/{Entity,Resource,ServiceProvider,Tests,Codeception,DoctrineMigrations}'
```

Symfony の PSR-4 自動登録は、`resource` にマッチした `.php` ファイルについて、このパスなら FQCN はこうなるはずだと機械的に組み立て、そのクラスが実際に定義されているかを確認します。

つまり `app/Plugin/AmazonPayV2_42_Bundle/phpseclib/bootstrap.php` というファイルがあれば、Symfony は `Plugin\AmazonPayV2_42_Bundle\phpseclib\bootstrap` というクラスが定義されているはずだと考えます。当然そんなクラスはありません。`bootstrap.php` はライブラリの初期化スクリプトであって、PSR-4 のクラスファイルではないからです。

:::message
厳密には、`FileLoader::findClasses()` は組み立てた FQCN が PHP の識別子として妥当かも見ています。`phpseclib-1.0/bootstrap.php` のようにハイフンを含むディレクトリ配下なら、識別子として不正なので黙ってスキップされ、例外は出ません。今回 `phpseclib/bootstrap.php` が刺さったのは、名前がたまたま有効な識別子だったからです。
:::

そして `FileLoader::registerClasses` は、これを黙って無視せず **例外を投げます**。

コンテナビルドが失敗するということは、`cache:clear` も `cache:warmup` も `doctrine:schema:update` も、要するに Symfony アプリケーションを起動するあらゆる操作が失敗するということです。プラグインを入れた瞬間にサイトが死ぬ、というのはこの経路です。

`exclude` に書かれている `Entity` や `Resource` は EC-CUBE のディレクトリ規約なので、そこにない `phpseclib` のようなディレクトリは素通りします。

### Symfony バージョンとの関係

PR の作成者は、この挙動が Symfony 4.4 / 5.4 / 6.4 / 7.4 のすべてで同一に再現することを、`symfony/dependency-injection` 単体で隔離検証しています。

4.4 に上げる前から、ずっと壊れていました。Symfony メジャーバージョンアップの回帰ではないと切り分けた上で修正されています。

## 修正: ネストした composer.json を検出して除外する

Issue [#6915](https://github.com/EC-CUBE/ec-cube/issues/6915) では複数の対応案が挙がっていましたが、採用されたのは **「ライブラリ名に依存させず動的に除外する」** 方針です。

`phpseclib` を `exclude` に直書きすれば AmazonPay プラグインは直りますが、次に別のライブラリを同梱したプラグインが出れば同じことが起きます。コアの設定ファイルに個別ライブラリ名を焼き込むのは筋が悪い。

そこで着目したのが **「同梱パッケージのルートには `composer.json` がある」** という規則性です。

`Plugin\` の登録は YAML では表現できないため、`app/config/eccube/services.php` という新規ファイルに移されました。

```php
return function (ContainerConfigurator $configurator): void {
    // このファイルは app/config/eccube/ 配下にあるため, 3 階層上がプロジェクトルート。
    $projectDir = \dirname(__DIR__, 3);
    $pluginDir = $projectDir.'/app/Plugin';

    // 従来 services.yaml が持っていた静的 exclude (+ 同梱ライブラリ集約用に vendor を追加)。
    $excludes = [
        $pluginDir.'/*/{Entity,Resource,ServiceProvider,Tests,Codeception,DoctrineMigrations,vendor}',
    ];

    // プラグイン配下のネストした composer.json (= 同梱パッケージ) を検出して除外する。
    foreach (glob($pluginDir.'/*', GLOB_ONLYDIR) ?: [] as $plugin) {
        $scan = static function (string $dir) use (&$scan, &$excludes): void {
            foreach (scandir($dir) ?: [] as $entry) {
                // vendor は上の静的 exclude 済み。走査コスト削減のため潜らない。
                if ('.' === $entry || '..' === $entry || 'vendor' === $entry) {
                    continue;
                }
                $path = $dir.'/'.$entry;
                if (!is_dir($path)) {
                    continue;
                }
                // 同梱パッケージのルートを見つけたらサブツリーごと除外し, これ以上潜らない。
                if (is_file($path.'/composer.json')) {
                    $excludes[] = $path;

                    continue;
                }
                $scan($path);
            }
        };
        // プラグインルート直下の composer.json (プラグイン自身の定義) は対象外。サブディレクトリのみ走査する。
        $scan($plugin);
    }

    $services = $configurator->services();

    $services->defaults()
        ->autowire()
        ->autoconfigure()
        ->private();

    $services->load('Plugin\\', $pluginDir.'/*')
        ->exclude($excludes);
};
```

読みどころがいくつかあります。

**プラグインルート直下の `composer.json` は対象外**にしている点。プラグイン自身の `composer.json`（`app/Plugin/YourPlugin/composer.json`）まで検出してしまうと、プラグイン全体が除外されて何も登録されなくなります。`$scan($plugin)` が走査するのは `$plugin` 直下のエントリからなので、ルート自体はチェックされません。

**同梱パッケージを見つけたらそれ以上潜らない**点（`continue`）。パッケージの中にさらにネストしたパッケージがあっても、親をサブツリーごと除外済みなので走査する意味がありません。無駄な再帰を避けています。

**`vendor` は静的 exclude に追加した上で走査もスキップ**している点。`vendor/` 配下は数千ファイルになり得るので、`scandir` の再帰で潜ると無視できないコストになります。

これで、直接バンドル（`app/Plugin/Foo/phpseclib/`）でも `vendor/` 同梱（`app/Plugin/Foo/vendor/phpseclib/`）でも、ライブラリ名を知らずに除外できます。

### 実行コストは？

コンテナビルドのたびにディレクトリを再帰走査するのか、という点は気になります。PR に説明があります。

> 走査ロジック（`scandir` 再帰）は **コンテナのコンパイル時のみ**実行され, ダンプ済みコンテナ（`var/cache/<env>/*Container.php`）には含まれません。通常リクエストでは実行されないためランタイム性能への影響はありません

Symfony の DI は、設定ファイルを評価した結果を `var/cache/` に PHP コードとしてダンプします。通常のリクエストが読むのはそのダンプ済みファイルであって、`services.php` ではありません。走査が走るのは `cache:clear` / `cache:warmup` のときだけです。

追跡リソースの `app/Plugin` Glob も従来の `Plugin\` glob と同一で、リクエストごとのコストは増えていないことを `meta.json` で確認したとも書かれています。

## 副作用: `bind` が届かなくなる問題

ここからが Symfony の DI を触る人にとって本題かもしれません。

4.3 の `services.yaml` には、こんな `_defaults` があります。

```yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true
        public: false

        bind:
          $cartPurchaseFlow: '@eccube.purchase.flow.cart'
          $shoppingPurchaseFlow: '@eccube.purchase.flow.shopping'
          $orderPurchaseFlow: '@eccube.purchase.flow.order'
          $_orderStateMachine: '@state_machine.order'
```

決済プラグインの Payment Method などが、コアの `Cash` クラスと同じように `PurchaseFlow $shoppingPurchaseFlow` を型 + 引数名で注入する。これが成立していたのは、この `bind` のおかげです。

問題は、**Symfony の `_defaults` がその定義ファイルの中のサービスにしか適用されない**ことです。スコープは定義ファイル単位（正確には同一 `services` ブロック単位）です。公式ドキュメントにも "for any service that's defined in this file" と明記されています。

つまり `Plugin\` の登録を `services.php` に移した瞬間、プラグインのサービスは `services.yaml` の `_defaults` の対象外になり、`$shoppingPurchaseFlow` が解決できなくなります。決済プラグインが軒並み壊れる、というかなり危ない副作用です。

これを避けるため、`services.yaml` に **名前付きオートワイヤリング別名（named autowiring alias）** が追加されました。

```yaml
    # PurchaseFlow / OrderStateMachine の名前付き引数をコンテナ全体で解決するための別名。
    # 上記 _defaults の bind はこのファイル内のサービスにのみ適用されるため, services.php で
    # 登録するプラグインのサービス (例: 決済プラグインの Payment Method) からも解決できるよう,
    # 名前付きオートワイヤリング別名として明示的に定義する。
    Eccube\Service\PurchaseFlow\PurchaseFlow $cartPurchaseFlow: '@eccube.purchase.flow.cart'
    Eccube\Service\PurchaseFlow\PurchaseFlow $shoppingPurchaseFlow: '@eccube.purchase.flow.shopping'
    Eccube\Service\PurchaseFlow\PurchaseFlow $orderPurchaseFlow: '@eccube.purchase.flow.order'
    Symfony\Component\Workflow\WorkflowInterface $_orderStateMachine: '@state_machine.order'
```

`型 $引数名: '@サービスID'` という書き方で、コンテナ全体に効くエイリアスを定義できます。Symfony ではこれを **named autowiring alias** と呼びます。同じインターフェースの実装が複数あるときに引数名で選ばせる、標準的な手法です。

`bind` とは効く範囲が違うことを覚えておくと、いつか役に立ちます。

| 書き方 | 効く範囲 | マッチ条件 |
| --- | --- | --- |
| `_defaults` の `bind` | その定義ファイル（同一 `services` ブロック）内のみ | 引数名 / 型 / 型 + 引数名 のいずれか |
| named autowiring alias | コンテナ全体 | 型 + 引数名 |

一方 `services.php` 側の `defaults()` には `bind` を書いていません。追加された `services.php` のソースコメントが理由を説明しています。

> この scope のどのサービスからも使われない bind は "unused binding" エラーになるため

プラグインは入っているが、どのプラグインのサービスも `$cartPurchaseFlow` を引数に取っていない、という状況は普通にあります。その scope のどのサービスからも使われない `bind` があると、Symfony は `ResolveBindingsPass` でコンパイル時に例外を投げます（警告ではなくエラーです）。だから `services.php` 側では定義せず、コンテナ全体に効く別名に寄せた、という判断です。

## プラグイン開発者としてどうすべきか

### 4.3 以下でいま踏んでいる場合

4.4 を待たずに回避したいなら、`app/config/eccube/services.yaml` の `Plugin\` ブロックの `exclude` に該当ディレクトリを追記するのが最短です。

```yaml
    Plugin\:
        resource: '../../../app/Plugin/*'
        exclude: '../../../app/Plugin/*/{Entity,Resource,ServiceProvider,Tests,Codeception,DoctrineMigrations,vendor,phpseclib}'
```

ただしこの `exclude` パターンは `app/Plugin/*/` の**直下1階層**にしかマッチしません。`app/Plugin/AmazonPayV2_42_Bundle/phpseclib/` のようにプラグイン直下なら効きますが、`app/Plugin/Foo/lib/phpseclib/` のように1階層深いところにあると効きません。その場合はパターンを実際の配置に合わせてください。

:::message alert
`app/config/eccube/services.yaml` はコアの設定ファイルです。ここを直接編集すると、EC-CUBE 本体のバージョンアップ時に上書き・コンフリクトの対象になります。編集した内容は必ず記録に残し、アップデート手順に含めてください。
:::

### 自作プラグインでライブラリを同梱する場合

そもそも、可能ならライブラリは同梱せず、プラグインの `composer.json` の `require` に書いてください。同梱してしまうと composer 経由の更新が届かず、そのライブラリに脆弱性が出てもプラグインを作り直すまで古いままです。今回の例に出ている phpseclib は暗号ライブラリなので、なおさら危険です。

どうしても同梱が必要な場合に限り、DI の観点では `app/Plugin/YourPlugin/vendor/` 配下に置くのが安全です。4.4 では `vendor` が静的 exclude に入っているので確実に除外されますし、4.3 以下でも `exclude` への追記が1行で済みます。

さらに、同梱パッケージのルートに `composer.json` を置いておけば、4.4 の動的検出にそのまま乗ります。Composer の `--path` リポジトリなどでライブラリをそのまま持ってきた形であれば、通常 `composer.json` は含まれているはずです。

逆にやってはいけないのは、プラグイン直下に `bootstrap.php` のような非 PSR-4 の `.php` ファイルを、`composer.json` なしのディレクトリに置くことです。4.4 の動的検出は `composer.json` の存在を手がかりにしているので、それがないと除外されません。

### 4.4 で `services.php` に何かを追記したくなったら

`app/config/eccube/services.php` はコアのファイルです。プラグイン側から DI 設定を足したい場合は、従来どおりプラグインの `Resource/config/services.yaml` を使ってください。コアの `services.php` を書き換える必要はありませんし、するべきでもありません。

## まとめ

- プラグイン同梱の非 PSR-4 ファイルでコンテナビルドが落ちるバグは、2017年から存在していた（[PR #6917](https://github.com/EC-CUBE/ec-cube/pull/6917) で修正）
- Symfony のバージョンとは無関係（4.4 / 5.4 / 6.4 / 7.4 すべてで再現）
- 4.4 では `Plugin\` の登録が `services.php` に移り、ネストした `composer.json` を検出して動的に exclude する
- 走査はコンパイル時のみ。ランタイム性能への影響はない
- `_defaults` の `bind` は定義ファイル単位でしか効かない。コンテナ全体に効かせたいなら named autowiring alias（`型 $引数名: '@サービスID'`）
- ライブラリの同梱は最後の手段。やるなら `vendor/` 配下 + `composer.json` 同梱

`exclude` にライブラリ名を1つ足せば直ったことにはなります。そうせずに、`composer.json` の存在という規則性を見つけて一般解にした。8年越しのバグ修正としては、ずいぶんきれいな決着でした。

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
