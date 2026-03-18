---
title: EC-CUBE 4プラグインのパッケージングを自動化する方法
tags:
  - PHP
  - GitHub
  - EC-CUBE
  - GitHubActions
private: false
updated_at: '2026-03-18T22:01:12+09:00'
id: 34b07e91339d93839f3c
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4プラグインのパッケージングを自動化する方法](https://zenn.dev/and_and/articles/eccube-plugin-release-automation)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4プラグインのパッケージングを自動化する方法](https://zenn.dev/and_and/articles/eccube-plugin-release-automation)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
