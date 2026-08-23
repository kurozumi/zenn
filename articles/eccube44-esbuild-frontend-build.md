---
title: "EC-CUBE 4.4 のフロントエンドビルドが webpack + gulp から esbuild になった"
emoji: "⚡"
type: "tech"
topics: ["eccube", "eccube4", "esbuild", "javascript", "frontend"]
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

EC-CUBE 4.4 のフロントエンドビルドが、webpack + gulp から esbuild に載せ替えられました。nanasess さんの [PR #7013](https://github.com/EC-CUBE/ec-cube/pull/7013) で、`4.4` ブランチに 2026年8月5日マージ済みです。4.4 自体はこの記事を書いている時点（2026年8月）で未リリースです。

変更は 830 ファイルありますが、その大半は再生成されたバンドル成果物です。手で書かれたのは `esbuild.config.mjs` の 257 行と、entry の `bundle.js` 3 本だけ。4.3 にあった `gulpfile.js` と `webpack.config.js`、`babel.config.json` は 4.4 のリポジトリルートからすべて消えました。

**TL;DR**

- 依存パッケージが 561 個から 110 個に減り、`npm audit` の指摘 9 件が 0 件になった
- フルビルド 24.1 秒 → 1.0 秒、watch の差分ビルド 13 秒 → 約 50 ms
- 動機は速度ではなくサプライチェーン耐性。Rspack 案（#6745）と実測で突き合わせた結果として esbuild を選んでいる
- テンプレートを触らずに済ませるため、CSS を `<style>` として注入する自前プラグインを書いている
- jQuery UI の AMD 依存が黙って抜け落ちる、ace の mode が 404 になるなど、移行時の罠が entry の差分に残っている
- ace の mode は twig と css と javascript の 3 つだけ静的配置になったので、別モードを使うプラグインは 4.4 で 404 を踏む

## 数字

PR に実測値が載っています。

| 指標 | webpack + gulp | esbuild |
| --- | --- | --- |
| `npm ci` のパッケージ数 | 561 | 110 |
| `npm audit` | 9 件（high 6 / moderate 3） | 0 件 |
| `node_modules` | 183 MB | 149 MB |
| フルビルド | 24.1 秒 | 1.0 秒 |
| JS の差分ビルド（watch） | 13 秒 | 約 50 ms |
| `html/bundle` の生成物 | 783 ファイル / 28 MB | 19 ファイル / 8.8 MB |

`html/bundle` の 783 ファイルというのは誇張ではありません。気になって 4.3 ブランチの `html/bundle` を GitHub API で数えたら、本当に 783 エントリ返ってきました。中身は `003671ee2a876e7614cd94390e2255b3.js` のようなハッシュ名のファイルが 766 個。ace エディタの mode と theme と worker が `file-loader` 経由で全部書き出されたものです。4.4 では 6 ファイルと `ace/` ディレクトリだけになりました。

バンドルサイズはこうなっています。

| ファイル | webpack | esbuild |
| --- | --- | --- |
| `front.bundle.js` | 229,486 B | 235,735 B |
| `admin.bundle.js` | 1,340,149 B | 1,267,915 B |
| `install.bundle.js` | 1,221,919 B | 402,069 B |

`install.bundle.js` だけ 3 分の 1 になっています。最適化が効いたわけではなく、webpack 側のバンドルに CSS の source map（`sourcesContent`）が約 800 KiB 混入していたからです。インストーラーの JS が 1.2 MB もあったのは、中身の 3 分の 2 が SCSS のソース文字列だったからです。誰も気付かないまま配布され続けていたわけです。

## Rspack 案との突き合わせ

この移行の直接の目的は速度ではありません。サプライチェーン耐性です。依存パッケージが 561 個あれば、それだけ侵害されうる経路がある。

同じ動機で先に [PR #6745](https://github.com/EC-CUBE/ec-cube/pull/6745) が Rspack 導入を提案していました。webpack の設定をほぼそのまま移植できるので、移行コストという点では有利です。nanasess さんはそのコメントで「gulp から esbuild への移行を考えております。RSpack と esbuild のメリットデメリットを考え、比較検討をさせていただきます」と書いていて、#7013 はその比較検討の結果です。同じ 4.4 の上に両方の構成を作って測っています。

| 指標 | 現行 | #6745 相当 | #7013 |
| --- | --- | --- | --- |
| インストール数 | 538 | 678 | 93 |
| `npm audit` | 9 件 | 13 件 | 0 件 |
| `node_modules` | 183 MB | 298 MB | 148 MB |
| `html/bundle` | 783 | 469 | 19 |

こちらの表は lock ファイルなしの最新解決で条件を揃えているため、先の表とパッケージ数が少しずれます。

Rspack 構成で依存がむしろ増えているのは、webpack を差し替えても gulp と browser-sync と各種 loader がそのまま残るからです。バンドラだけ速くしても、周りのタスクランナーが依存を持ち込み続ける。gulp ごと捨てにいったのはそこが理由でしょう。

比較の詰め方も丁寧でした。#6745 の `@rspack/cli` は `gulp/task/rspack.js` が `@rspack/core` を直接呼んでいるため実際には参照されておらず、外す余地があります。nanasess さんは外した構成も測っていて、515 パッケージ / 268 MB / audit 9 件。現行に対する脆弱性の増加分 4 件はすべて `@rspack/cli` 由来だと突き止めています。相手の案を一番有利な形に整えてから比べているわけです。

## テンプレートを壊さないという制約

EC-CUBE のようなプロダクトでビルドツールを入れ替えるとき、いちばん怖いのは既存サイトの表示が壊れることです。`default_frame.twig` を上書きしているサイトは珍しくありません。

なので #7013 はテンプレートの変更を伴わないことを最優先に置いています。webpack の `style-loader` は CSS を JavaScript から `<style>` タグとして DOM に注入します。esbuild の標準の挙動は CSS を別ファイルに吐くことなので、素直に移行すると `<link>` タグを足すためにテンプレートを触ることになる。

`esbuild.config.mjs` にはそのための自前プラグインが入っています。

```js
const styleInjectPlugin = {
  name: 'style-inject',
  setup(build) {
    build.onLoad({ filter: /\.css$/ }, async (args) => {
      const bundled = await esbuild.build({
        entryPoints: [args.path],
        bundle: true,
        minify: true,
        write: false,
        logLevel: 'silent',
        loader: assetLoader,
      })
      const css = bundled.outputFiles.map((file) => file.text).join('')

      return {
        contents: `var style = document.createElement('style');`
          + `style.textContent = ${JSON.stringify(css)};`
          + `document.head.appendChild(style);`,
        loader: 'js',
      }
    })
  },
}
```

`onLoad` で CSS を掴まえ、内側でもう一度 esbuild を回して `@import` と `url()` を解決し、その結果を `<style>` を作る JavaScript に書き換えて返しています。`url()` の中身は `assetLoader` で data URI に埋め込まれるので、`url-loader` 相当も同時に効く仕組みです。

ちなみに ec-cube2 の同種の移行（[EC-CUBE/ec-cube2#1391](https://github.com/EC-CUBE/ec-cube2/pull/1391)）では CSS を静的ファイルに分離する方式を採ったそうです。4 系は互換性を優先して見送った、と PR に書かれています。CSS が JS に埋まったままなのは正直あまり嬉しくないのですが、上書きテンプレートが生きているサイトを壊さないという条件下では他に手がなかったのだろうと思います。

## 移行で踏んだ罠

entry の `bundle.js` の差分を 4.3 と 4.4 で見比べると、webpack から esbuild に移るときに何が壊れるかがそのまま出てきます。

### `global` は自分で用意する

4.3 の front 側 entry はこうでした。

```js
const $ = require('jquery');
global.$ = global.jQuery = $;
```

ブラウザに `global` はありません。webpack がバンドル時に埋めてくれていたものです。4.4 では entry 側を `window` に直しています。

```js
window.$ = window.jQuery = require('jquery');
```

`esbuild.config.mjs` 側にも `define: { global: 'window' }` が入っていて、こちらは `node_modules` 内の CommonJS ライブラリが参照する `global` を救うためのものです。自前のコードは `window` を直接書き、依存ライブラリは `define` で吸収する、という切り分けになっています。

webpack の `ProvidePlugin`（`$` を見たら jQuery を注入するやつ）に相当する仕組みは esbuild にありません。EC-CUBE の場合、管理画面の個別 JS は `<script>` タグで別に読まれていて `window.$` を参照するため、`window` への代入さえ残っていれば足ります。

この形になるまでには 2 段階あります。ローカルの `const $` を捨てて `global.$ = global.jQuery = require('jquery')` の 1 行にしたのは、esbuild 移行より前の [PR #6869](https://github.com/EC-CUBE/ec-cube/pull/6869)（ttokoro20240902 さん）でした。Babel を撤去したら `const` が `var` に変換されなくなり、`ProvidePlugin` が注入する `$` と二重宣言になってビルドが落ちた、という別件です。

```
ERROR in [entry] [initial] front.bundle.js
Identifier '$' has already been declared (2:6)
```

IE11 のためだけに残っていた Babel が消えて依存が 139 個減り、その副作用で entry が先に整理されていた。#7013 はそこから `global` を `window` に置き換えただけです。

### jQuery UI は依存を手で並べる

4.3 の admin entry では、jQuery UI の読み込みが 7 行でした。

```js
require('jquery-ui/ui/core');
require('jquery-ui/ui/position');
require('jquery-ui/ui/widget');
require('jquery-ui/ui/widgets/mouse');
require('jquery-ui/ui/widgets/resizable');
require('jquery-ui/ui/widgets/sortable');
require('jquery-ui/ui/widgets/tooltip');
```

4.4 では 13 行に増えました。

```js
// jQuery UI の各モジュールは UMD の AMD 分岐で内部依存を解決しているが、
// esbuild は AMD を解釈しないため依存が読み込まれない。必要なものを依存順に明示する。
require('jquery-ui/ui/version');
require('jquery-ui/ui/position');
require('jquery-ui/ui/widget');
require('jquery-ui/ui/widgets/mouse');
require('jquery-ui/ui/disable-selection');
require('jquery-ui/ui/plugin');
require('jquery-ui/ui/widgets/resizable');
require('jquery-ui/ui/data');
require('jquery-ui/ui/scroll-parent');
require('jquery-ui/ui/widgets/sortable');
require('jquery-ui/ui/keycode');
require('jquery-ui/ui/unique-id');
require('jquery-ui/ui/widgets/tooltip');
```

jQuery UI のモジュールは UMD で書かれていて、AMD の分岐に `define(['./mouse', './widget'], ...)` のような依存宣言が入っています。webpack はこれを解釈して依存を辿りますが、esbuild は AMD を扱いません。結果として `resizable` が必要とする `disable-selection` や `plugin` が黙って抜け落ちます。

厄介なのは、これがビルドエラーにならないことです。ビルドは通り、管理画面を開いてドラッグしようとしたときに初めて壊れる。移行後に手で全部の画面を触っていなければ気付けない類の罠です。

### ace エディタは `webpack-resolver` が使えない

4.3 は `require('ace-builds/webpack-resolver')` を呼んでいました。これは ace の mode と theme と worker を webpack に解決させるためのもので、ハッシュ名で書き出したファイルとモジュール名の対応を実行時に登録します。中身は `file-loader?esModule=false!...` という webpack 固有の inline loader 構文なので、esbuild では解決できません。

4.4 は方針を変えて、実際に使うファイルだけを `html/bundle/ace` に静的配置しています。

```js
const aceFiles = [
  'mode-css.js',
  'mode-javascript.js',
  'mode-twig.js',
  'theme-tomorrow.js',
  'worker-css.js',
  'worker-html.js',
  'worker-javascript.js',
  'ext-searchbox.js',
  'snippets/css.js',
  'snippets/html.js',
  'snippets/javascript.js',
  'snippets/text.js',
  'snippets/twig.js',
]
```

管理画面のテンプレートで実際に指定されているモードを調べて決めた、と設定ファイルのコメントに書かれています。twig はページ管理とブロック編集とレイアウト管理で、css は CSS 管理、javascript は JavaScript 管理で使われている。`worker-html.js` が入っているのは、`mode-twig` が javascript と css と html の 3 つの worker を参照するからです。783 ファイルが 19 ファイルになった主因はここにあります。

そして entry 側でパスを教えます。

```js
const bundleSrc = document.currentScript ? document.currentScript.src : window.location.href;
const acePath = new URL('ace/', bundleSrc).href;
['basePath', 'modePath', 'themePath', 'workerPath'].forEach((key) => window.ace.config.set(key, acePath));
```

4 つ全部設定しているのには理由があります。ace は読み込み時に、自身の置き場を `basePath` だけでなく `modePath` と `themePath` と `workerPath` にも書き込みます。`config.moduleUrl()` は `options[component + 'Path']` を `basePath` より優先して見るため、`basePath` だけ上書きしても mode と theme と worker は `html/bundle` 直下を探しに行って 404 になる。

もうひとつ、コメントには `snippetsPath` は設定しないこと、とわざわざ書かれています。設定すると `moduleUrl()` が component と区切り文字を落として、`ace/snippets/foo` が `ace/foo.js` に解決されてしまうそうです。未設定なら `basePath` にフォールバックするので正しく動く。

設定してはいけない項目がある、というのはコメントがなければ次に触る人が確実に踏みます。

## 成果物をコミットする運用と dependabot

EC-CUBE はビルド成果物をリポジトリにコミットして配布します。`html/bundle/*.bundle.js` も `html/template/**/assets/css` も git 管理下にあります。

これが dependabot と相性が悪い。npm の更新 PR は `package.json` と `package-lock.json` しか触らないので、依存を上げても成果物は古いままです。マージすると、lock ファイルだけ新しくてバンドルは前のバージョンのライブラリを含んだ状態になります。

そこで #7013 は `.github/workflows/dependabot-assets.yml` を新設しました。dependabot のブランチへの push を受けてビルドし、差分があれば同じブランチに追記コミットします。

このワークフローの作りが読みどころでした。build と push が別ジョブに分かれていて、コメントに理由が書かれています。

```yaml
jobs:
  build:
    permissions:
      # 更新された依存パッケージのコードを実行するジョブなので読み取りのみ。
      contents: read
  push:
    needs: build
    permissions:
      # このジョブでは npm を実行しないため、依存パッケージのコードはここに到達しない。
      contents: write
```

`npm ci` は依存パッケージの `postinstall` を走らせ、`npm run build` は更新後の esbuild と sass-embedded のバイナリを実行します。build ジョブは、まだ誰もレビューしていない他人のコードを実行する場だということです。

ここに書き込みトークンを置くと、トークンをステップの `env` に限定してもフックを無効化しても防げません。`$GITHUB_PATH` や `$GITHUB_ENV` へ書き込めば、後続ステップの実行ファイル解決を汚染できるからです。そしてこれらはジョブ単位なので、ジョブを跨ぐと引き継がれない。だから build ジョブは `contents: read` だけを持ち、生成物を artifact に載せて push ジョブへ渡します。push ジョブは npm を一切実行しません。

サプライチェーン耐性のための PR が、そのために足した CI 自体を新しい攻撃面にしていない。ここは素直に感心しました。

細部も同じ発想で作られています。`checkout` に `persist-credentials: false` を指定して認証情報を git config に残さず、push するステップでだけトークンを渡す。`ref` をブランチ名ではなく `github.sha` で固定して、build と push が別コミットを見ないようにする。

## 開発時の変化

`npm start` の中身が変わりました。4.3 は gulp が browser-sync を立ててプロキシしていましたが、4.4 は esbuild の watch だけになります。

browser-sync を捨てたのは、これ単体で 145 パッケージを持ち込み、`npm audit` の high 2 件（`immutable@3.8.3` と `brace-expansion@1.1.17`）の経路にもなっていたからです。差分ビルドが 50 ms で終わるなら手動リロードで支障ない、という判断です。13 秒待たされていた頃なら自動リロードの価値は大きかったはずで、順序としては速くなったから捨てられた、ということになります。自動リロードに慣れていると最初は不便に感じるかもしれません。

SCSS のコンパイルには `sass-embedded` が入りました。ここは #6745 から取り込んだ部分で、JS 実装の `sass` に比べて約 2 倍速いそうです。

`esbuild.config.mjs` を読むと、SCSS だけは esbuild の管理外なので `fs.watch` で個別に見ています。

```js
let timer = null
for (const dir of findScssDirs(templateDir)) {
  fs.watch(dir, (_event, filename) => {
    if (!filename || !filename.endsWith('.scss')) {
      return
    }

    // 保存直後は同じファイルに対して複数回通知されるためまとめて処理する
    clearTimeout(timer)
    timer = setTimeout(() => {
      buildScss()
        .then(() => console.log(`scss rebuilt (${filename})`))
        .catch((e) => console.error(e))
    }, 100)
  })
}
```

`fs.watch` はエディタの保存 1 回で複数イベントを飛ばすので、100 ms のデバウンスが入っています。

source map の扱いにも一手間かかっています。`sass-embedded` は `sources` を `file://` の絶対 URL で返すため、そのまま書き出すとビルドマシンのパスが焼き込まれます。成果物をコミットする運用では、誰が再ビルドしても map ファイルだけが差分になってしまう。なので map ファイルからの相対パスに直し、区切り文字を POSIX に固定してから書き出しています。地味ですが、これを踏むと原因が分かるまでけっこう悩みます。

## プラグイン開発者への影響

コア側のビルド設定は `html/template` 配下しか見ていないので、プラグインが `Resource/assets` に持っている成果物には手が入りません。プラグイン側で webpack を使い続けることもできます。

ただし ace エディタは注意が必要です。4.4 で静的配置されるのは前掲のリストだけ、mode は twig と css と javascript の 3 つしかありません。管理画面に独自のエディタ画面を足していて `ace/mode/json` や `ace/mode/php` を指定しているプラグインは、4.3 では `webpack-resolver` が全モードを登録していたおかげで動いていたものが、4.4 では 404 を踏みます。必要なモードを自分で配置してパスを設定するか、コアに追加を提案するかの選択になります。

あとは、コアのビルド設定を写して使っていた場合。`gulpfile.js` も `webpack.config.js` も `babel.config.json` も 4.4 には存在しません。参照元が消えたので、次に更新するときは自力になります。

## まとめ

数字のインパクトが目立つ PR ですが、読んでいて引っかかったのは速度より制約の置き方でした。テンプレートを触らないと決めたから `style-inject` プラグインを書くことになり、成果物をコミットする運用を維持したから dependabot 用の CI を足すことになり、その CI が他人のコードを実行するから権限を分けることになる。

`esbuild.config.mjs` 257 行のうち、esbuild にビルドを指示している部分はごく一部です。残りは ace の静的配置や source map のパス書き換えといった、既存の運用に合わせるためのコードで埋まっています。ツールの入れ替えそのものより、周りを壊さないための処理のほうが分量も判断も多い。バージョンアップ対応をやっているとよく見る比率なので、他人事ではない気持ちで読みました。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
