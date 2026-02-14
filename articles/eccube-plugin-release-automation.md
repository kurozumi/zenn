---
title: "EC-CUBE 4プラグインのパッケージングを自動化する方法"
emoji: "🚀"
type: "tech"
topics: ["eccube", "eccube4", "php", "github", "githubactions"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBEプラグインの配布には、ソースコードをtar.gz形式でパッケージングする必要があります。この記事では、GitHubのリリース機能とGitHub Actionsを使って、パッケージングを自動化する方法を解説します。

## 概要

`bin/console eccube:plugin:generate` コマンドでプラグインを生成すると、以下のファイルが自動的に作成されます。

- `.github/workflows/release.yml` - リリース自動化ワークフロー
- `.gitattributes` - パッケージング除外設定

これらを使うことで、GitHubでリリースを公開するだけでtar.gzファイルが自動生成されます。

## ディレクトリ構成

```
app/Plugin/Sample/
├── .github/
│   └── workflows/
│       └── release.yml     # GitHub Actions ワークフロー
├── .gitattributes          # パッケージング除外設定
├── .gitignore
├── composer.json
├── Controller/
├── Entity/
├── Event.php
├── Form/
├── Nav.php
├── PluginManager.php
├── Repository/
├── Resource/
└── TwigBlock.php
```

## release.yml の解説

GitHubでリリースを公開したときに自動実行されるワークフローです。

```yaml
name: Packaging for EC-CUBE Plugin
on:
  release:
    types: [ published ]
jobs:
  deploy:
    name: Build
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v2

      - name: Packaging
        run: |
          git archive HEAD --format=tar.gz > ../${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz

      - name: Upload binaries to release of TGZ
        uses: svenstaro/upload-release-action@v1-release
        with:
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          file: ${{ runner.workspace }}/${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz
          asset_name: ${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz
          tag: ${{ github.ref }}
          overwrite: true
```

### ワークフローの流れ

1. **トリガー**: リリースが公開（`published`）されたとき
2. **Checkout**: ソースコードをチェックアウト
3. **Packaging**: `git archive` でtar.gzを作成
4. **Upload**: 作成したtar.gzをリリースにアップロード

### git archive コマンド

```bash
git archive HEAD --format=tar.gz > プラグイン名-バージョン.tar.gz
```

このコマンドは、Gitで管理されているファイルのみをアーカイブします。`.gitignore` で無視されているファイルや、`.gitattributes` で `export-ignore` 指定されたファイルは含まれません。

## .gitattributes の解説

`.gitattributes` はGitの属性を設定するファイルです。`export-ignore` 属性を指定すると、`git archive` でパッケージングする際にそのファイルを除外できます。

```
/.gitattributes             export-ignore
/.github                    export-ignore
/.gitignore                 export-ignore
/dummy                      export-ignore
```

### デフォルトで除外されるファイル

| ファイル/ディレクトリ | 理由 |
|----------------------|------|
| `.gitattributes` | パッケージング設定自体は不要 |
| `.github` | GitHub Actions設定は不要 |
| `.gitignore` | Git設定は不要 |
| `/dummy` | ダミーファイル置き場 |

### 除外したいファイルを追加する

開発用のファイルやテストファイルなど、配布パッケージに含めたくないものがあれば追加できます。

```
# デフォルトの除外設定
/.gitattributes             export-ignore
/.github                    export-ignore
/.gitignore                 export-ignore

# 追加の除外設定
/tests                      export-ignore
/phpunit.xml                export-ignore
/phpstan.neon               export-ignore
/.php-cs-fixer.php          export-ignore
/Makefile                   export-ignore
/docker-compose.yml         export-ignore
/README.md                  export-ignore
/CHANGELOG.md               export-ignore
/docs                       export-ignore
```

### よくある除外パターン

```
# テスト関連
/tests                      export-ignore
/phpunit.xml                export-ignore
/phpunit.xml.dist           export-ignore

# 静的解析・コード整形
/phpstan.neon               export-ignore
/.php-cs-fixer.php          export-ignore
/.php-cs-fixer.dist.php     export-ignore

# CI/CD
/.github                    export-ignore
/.gitlab-ci.yml             export-ignore

# 開発環境
/docker-compose.yml         export-ignore
/Makefile                   export-ignore
/.env.example               export-ignore

# ドキュメント（必要に応じて）
/README.md                  export-ignore
/CHANGELOG.md               export-ignore
/docs                       export-ignore
/LICENSE                    export-ignore
```

## リリースの手順

### 1. バージョンを更新

`composer.json` のバージョンを更新します。

```json
{
  "name": "ec-cube/sample",
  "version": "1.0.1",
  "description": "EC-CUBE Sample Plugin",
  "type": "eccube-plugin",
  "require": {
    "ec-cube/plugin-installer": "~0.0.7 || ^2.0"
  },
  "extra": {
    "code": "Sample"
  }
}
```

### 2. 変更をコミット・プッシュ

```bash
git add composer.json
git commit -m "Bump version to 1.0.1"
git push origin main
```

### 3. GitHubでリリースを作成

1. GitHubリポジトリの「Releases」ページへ移動
2. 「Draft a new release」をクリック
3. 「Choose a tag」で新しいタグを作成（例: `1.0.1`）
4. リリースタイトルを入力（例: `v1.0.1`）
5. リリースノートを記入
6. 「Publish release」をクリック

### 4. 自動パッケージング

リリースを公開すると、GitHub Actionsが自動実行されます。

1. ワークフローが `git archive` でtar.gzを作成
2. 作成されたtar.gzがリリースのAssetsに追加される

### 5. ダウンロード確認

リリースページに `Sample-1.0.1.tar.gz` が追加されていることを確認します。

## ワークフローのカスタマイズ

### zip形式も同時に作成

tar.gzとzipの両方を作成する例です。

```yaml
- name: Packaging
  run: |
    git archive HEAD --format=tar.gz > ../${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz
    git archive HEAD --format=zip > ../${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.zip

- name: Upload TGZ
  uses: svenstaro/upload-release-action@v2
  with:
    repo_token: ${{ secrets.GITHUB_TOKEN }}
    file: ${{ runner.workspace }}/${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz
    asset_name: ${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.tar.gz
    tag: ${{ github.ref }}
    overwrite: true

- name: Upload ZIP
  uses: svenstaro/upload-release-action@v2
  with:
    repo_token: ${{ secrets.GITHUB_TOKEN }}
    file: ${{ runner.workspace }}/${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.zip
    asset_name: ${{ github.event.repository.name }}-${{ github.event.release.tag_name }}.zip
    tag: ${{ github.ref }}
    overwrite: true
```

## トラブルシューティング

### パッケージにファイルが含まれない

`.gitignore` に記載されているファイルは `git archive` に含まれません。配布に必要なファイルが `.gitignore` に含まれていないか確認してください。

### パッケージに不要なファイルが含まれる

`.gitattributes` に `export-ignore` を追加してください。

```
/不要なファイル    export-ignore
```

### ワークフローが実行されない

- リリースが「Draft」ではなく「Publish」されているか確認
- `.github/workflows/release.yml` がmainブランチにプッシュされているか確認

### 除外設定が反映されない

`.gitattributes` の変更後はコミットが必要です。

```bash
git add .gitattributes
git commit -m "Update .gitattributes"
git push
```

## まとめ

EC-CUBEプラグインのリリース自動化には以下の仕組みを使います。

1. **release.yml** - GitHubリリース時に自動でtar.gzを作成
2. **.gitattributes** - `export-ignore` で不要ファイルを除外
3. **git archive** - Gitで管理されているファイルのみをパッケージング

`bin/console eccube:plugin:generate` で生成されるテンプレートをベースに、プロジェクトに合わせてカスタマイズしてください。
