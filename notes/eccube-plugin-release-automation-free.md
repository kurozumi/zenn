# EC-CUBE 4プラグインのパッケージングを自動化する方法

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

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