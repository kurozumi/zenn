---
title: "EC-CUBE 4.4で getenv() が死ぬ? symfony/dotenv一本化の罠と高速化"
emoji: "⚡"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
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

## 結論: あなたのプラグインの `getenv()`、EC-CUBE 4.4で値が取れなくなるかもしれません

EC-CUBE 4.4(未リリース)で、`.env` の読み込み方法が `vlucas/phpdotenv` から Symfony 標準の `symfony/dotenv`(`bootEnv()`)に一本化されます。その裏側で `putenv()` を使わない設計に変わったため、自作プラグインやカスタマイズコードの中で `getenv('DATABASE_URL')` のような書き方をしている箇所があれば、4.4環境では**値が取れなくなる可能性**があります。

一方で良い話もあります。`composer symfony:dump-env prod` を実行すれば `.env.local.php` が生成され、本番起動のたびに発生していた `.env` パース処理を丸ごとスキップできる、地味だが効く高速化が手に入ります。

ただしこの高速化には罠があります。**`.env.local.php` を生成した後に `.env` を直接書き換えても、起動時にはその変更が反映されません。** EC-CUBEはこの罠に対して本体側で2箇所の安全策を入れていますが、運用フローとして「`.env` を変えたら dump-env をやり直す」を徹底しないと、本番で「設定を直したのに反映されない」事故につながります。

**TL;DR**
- `getenv()` に依存したプラグインコードは動作確認が必須(`putenv()` を使わない設計になったため)
- `.env.local.php` を生成すると、以後 `.env` を直接書き換えても起動時に反映されない罠がある
- その代わり `composer symfony:dump-env prod` で本番起動時の `.env` パースを丸ごとスキップでき、起動が速くなる
- EC-CUBE本体の `.env` ロードが `symfony/dotenv` の `bootEnv()` に一本化される([PR #6932](https://github.com/EC-CUBE/ec-cube/pull/6932)、`4.4` ブランチにマージ済み)
- `.env` → `.env.local` → `.env.$APP_ENV` → `.env.$APP_ENV.local` のカスケード読み込みに対応する
- **現時点(2026年7月)で EC-CUBE 4.4 は未リリース**。4.3系は今まで通り `vlucas/phpdotenv` ベース

## この記事の位置づけ(重要)

この変更は EC-CUBE 本体リポジトリの [PR #6932](https://github.com/EC-CUBE/ec-cube/pull/6932) として実装され、**`4.4` ブランチに2026年7月15日マージ済み**です。4.3ブランチの `composer.json` を確認すると、`symfony/dotenv`(`^6.4`)は既に依存関係に含まれているものの、実際の `.env` ロード(`index.php` 内)は今も `vlucas/phpdotenv` が使われています。つまり4.3では `symfony/dotenv` はPHPUnitのテスト実行(`tests/bootstrap.php`)用途で入っているだけで、本体の起動には使われていません。この構図が4.4で「本体もsymfony/dotenvに統一」という形に変わります。

実際のリリース時には細部が変わる可能性がある点にご注意ください。

## 何が変わるのか: 依存パッケージの整理

これまでのEC-CUBEは、`.env` の読み込みに `vlucas/phpdotenv` というサードパーティ製ライブラリを使っていました。一方でSymfonyエコシステム自体は `symfony/dotenv` という標準コンポーネントを持っており、4.3の時点でもPHPUnitのテスト実行ではこちらが使われていました(Codeceptionの受け入れテストは引き続きvlucas側)。つまり「本番起動時はvlucas、PHPUnit実行時はsymfony」という2つのdotenv実装が併存していたことになります。

このPRで `vlucas/phpdotenv` が `composer.json` から削除され、その推移的依存だった `phpoption`・`graham-campbell/result-type` も `composer.lock` から消え、`.env` ロードは `symfony/dotenv` の1本に統一されました。CLIと本体の実装が揃うことで、両者で微妙に異なる `.env` の解釈をされる可能性がなくなります。なお `symfony/dotenv` 自体のバージョンが `^6.4` から `^7.4` に上がっていますが、これはこのPR固有の変更ではなく、4.4ブランチ全体でのSymfony 7系アップグレードに伴うものです。

## 実装を読む: boot_env() ヘルパー

変更の中心は `src/Eccube/Resource/functions/env.php` に追加された、次のヘルパー関数です。

```php
function boot_env(string $path, bool $overrideExistingVars = false): void
{
    $unusedDebugKey = '__ECCUBE_UNUSED_APP_DEBUG';
    (new Dotenv('APP_ENV', $unusedDebugKey))->bootEnv($path, 'dev', ['test'], $overrideExistingVars);
    unset($_SERVER[$unusedDebugKey], $_ENV[$unusedDebugKey]);
}
```

これだけを見ると素通しの薄いラッパーに見えますが、2点の工夫が見えます。

**1. `APP_DEBUG` の自動導出を握りつぶしている**

Symfonyの `bootEnv()` は、`APP_ENV` の値に応じて `APP_DEBUG` を自動的に設定する仕様を持っています(公式ソースのPHPDocに「このメソッドは現在の `APP_ENV` に応じて `APP_DEBUG` 環境変数も設定する」と明記されています)。しかしEC-CUBEはこれまで「`APP_DEBUG` が未定義であること」自体を意味のある状態として扱ってきました。このヘルパーは `Dotenv` のコンストラクタ第2引数(debugキー名)にわざと使わないダミーキー `__ECCUBE_UNUSED_APP_DEBUG` を渡し、Symfonyが自動設定した値をそちらに書き込ませたうえで、直後に `unset` して消し去っています。標準機能の便利さを享受しつつ、既存の挙動を壊さないための工夫です。

**2. `$overrideExistingVars` を呼び出し元で使い分ける**

`index.php` では、`APP_ENV` がOS環境変数として未設定の環境(共有ホスティングなど)では `boot_env($path, true)`、Docker等で `APP_ENV` が既にOS環境変数として設定されている環境では `boot_env($path, false)` という具合に、呼び出し側で挙動を切り替えています。

Symfonyの `bootEnv()` 内部では、`overrideExistingVars=false` の場合、「既に実環境変数として存在する値は、dotenv側の値では上書きしない」という判定が行われます(`populate()` 内の実装で確認)。この判定は、dotenv経由でロード済みの変数名一覧を保持する `SYMFONY_DOTENV_VARS` という特殊な変数を使って行われており、`putenv()` を使わなくても「どの変数がdotenv由来か」を追跡できる仕組みになっています。EC-CUBEの実装がこの挙動を活かし、「OS環境変数がある場合はそちらを優先(保護)する」という従来の運用を、`overrideExistingVars=false` の指定だけで再現しています。

## `.env` のカスケード読み込みに対応する

`symfony/dotenv` の `bootEnv()` は、Symfonyのアプリケーションで標準的な、次の4段階のカスケード読み込みに対応しています(優先度は下にいくほど高い)。

1. `.env`
2. `.env.local`(ただし `APP_ENV=test` のときはスキップされる)
3. `.env.$APP_ENV`(例: `.env.prod`)
4. `.env.$APP_ENV.local`

環境ごとの値を `.env.prod` に、ローカルマシン固有の値(コミットしたくない値)を `.env.local` に、という分離ができるようになります。今回追加された `.gitignore` のエントリ(`.env.local` / `.env.local.php` / `.env.*.local`)も、この運用を前提としたものです。

## 本番起動を速くする: `.env.local.php`

このPRの一番の実利は、`composer symfony:dump-env prod` によって `.env.local.php` を生成できるようになったことです。`symfony/flex` がインストールされていれば、`composer.json` の `scripts` セクションに明示的な定義がなくても、Composerプラグイン経由でこのコマンドが使えます。

`bootEnv()` は起動のたびに `.env.local.php` の存在を最初にチェックし、**存在すればそちらを読み込み、`.env` 系ファイル一式のパース処理自体を丸ごとスキップします**。Symfony公式ドキュメントにも「`.env.local.php` があれば、`.env` ファイル群のパースに時間をかけずに済む」と明記されています。本番環境ではデプロイの一手順として `composer symfony:dump-env prod` を組み込むことで、リクエストのたびに発生していた `.env` パースのオーバーヘッドを削れます。

`.env.local.php` は `DATABASE_URL` などの解決済みの値を平文でそのまま含むキャッシュファイルです。`.env` 同様、Webルート外に置き、Gitにコミットしない(前述の `.gitignore` で除外済み)扱いを徹底してください。

## 落とし穴: `.env.local.php` を生成した後に `.env` を書き換えても反映されない

便利な仕組みですが、罠もあります。`.env.local.php` はいわば `.env` 系ファイルのスナップショットなので、生成後に `.env` を直接書き換えても、`bootEnv()` は最初に `.env.local.php` を見つけてそちらを優先してしまい、**変更が反映されません**。

EC-CUBEはこの罠に対して、2箇所で安全策を入れています。

**インストーラー(`InstallerCommand`)**: インストール実行時、既存の `.env.local.php` を検知したら削除し、再度最適化(dump-env)するようユーザーに促す通知を出します。

```php
$fs = new Filesystem();
if ($fs->exists($envDir.'/.env.local.php')) {
    $fs->remove($envDir.'/.env.local.php');
    $this->io->note('.env.local.php を削除しました。最適化を再適用するには `composer symfony:dump-env prod` を実行してください。');
}
```

(なお実装当初は `@unlink()` によるエラー抑制付きの削除でしたが、PRのレビュー段階で「エラーを握りつぶしている」という指摘が入り、Symfonyの `Filesystem::remove()` を使う形に修正されています。)

**テンプレート切り替え画面(`TemplateController`)**: 管理画面からテンプレートを切り替える機能は `.env` を書き換えることで動作しますが、`.env.local.php` が存在する状態でこの操作をしても、起動時には古いテンプレート設定が読まれ続けてしまいます。そこでこの画面には、`.env.local.php` が存在する場合に警告を表示する分岐が追加されています。

```php
$envLocalPhp = $this->getParameter('kernel.project_dir').'/.env.local.php';
if (false !== getenv('ECCUBE_TEMPLATE_CODE') || file_exists($envLocalPhp)) {
    $this->addWarning('admin.store.template.env_override_warning', 'admin');
}
```

運用者としては、「`.env.local.php` を作って高速化したら、それ以降 `.env` の直接編集では設定が反映されなくなる」という前提を覚えておく必要があります。`.env` を編集したら `composer symfony:dump-env prod` をやり直す、というオペレーションをデプロイ手順に組み込むのが安全です。

## プラグイン開発者・カスタマイズ担当者への影響

### `getenv()` への依存は避ける

このPRの方針として、`putenv()` は明確に使わない設計になっています。Symfonyの `Dotenv` クラスの `usePutenv()` メソッドのドキュメントコメントには「`putenv()` はスレッドセーフでないため、デフォルトでは有効にしていない」と明記されており、EC-CUBE側もこれに合わせています。

この結果、`index.php` や `InstallerCommand.php` 内の `getenv('DATABASE_URL')` のような呼び出しは、今回のPRで軒並み `$_SERVER['DATABASE_URL'] ?? ''` のような書き方に置き換えられています。もし自作プラグインやカスタマイズコードの中で `getenv()` を使って `.env` の値を読み取っている箇所があれば、4.4環境では値が取れない可能性があります。EC-CUBE本体が提供している `env()` ヘルパー関数、または `$_ENV` / `$_SERVER` を参照する形に置き換えておくのが安全です。

### 子プロセスへの環境変数伝播

`InstallerCommand` は内部で `doctrine:*` などのコンソールコマンドを子プロセスとして起動しますが、`putenv()` を使わなくても、Symfonyの `Process` コンポーネントは `Process::getDefaultEnv()` というメソッドで `$_ENV` とOSの `getenv()` を組み合わせた環境変数セットを子プロセスに渡すため、`DATABASE_URL` や `APP_ENV` は問題なく引き継がれます。プラグイン側で `Process` コンポーネントを使って外部コマンドを実行するようなカスタマイズをしている場合も、基本的にはこの仕組みに乗る形で環境変数が伝播するため、追加の対応は不要なはずです。

みなさんのプラグイン・カスタマイズコードで `getenv()` を使っている箇所、今すぐ思い出せますか。4.4がリリースされる前に、`grep -r "getenv("` で一度洗い出しておくことをおすすめします。

## まとめ

- EC-CUBE 4.4(未リリース)で、`.env` ロードが `symfony/dotenv` の `bootEnv()` に一本化されます。
- `composer symfony:dump-env prod` で `.env.local.php` を生成すれば、本番起動時の `.env` パースを省略でき、起動を高速化できます。
- ただし `.env.local.php` 生成後は `.env` の直接編集が反映されなくなるため、インストーラーやテンプレート切替画面には安全策が入っています。運用フローとしても「`.env` を変えたら dump-env をやり直す」を徹底する必要があります。
- `putenv()` を使わない設計になったため、`getenv()` に依存するプラグインコードは動作確認をおすすめします。

正式リリース時には実装が変わっている可能性があるため、最終的な仕様は公式のリリースノートや doc4.ec-cube.net でご確認ください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
