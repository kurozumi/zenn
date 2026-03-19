---
title: 'EC-CUBE 4プラグインでSymfonyバンドルを登録する方法'
tags:
  - EC-CUBE
  - PHP
  - Symfony
private: false
updated_at: '2026-03-17T22:47:06+09:00'
id: 969cea8648375cb14ca8
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4プラグインでSymfonyバンドルを登録する方法](https://zenn.dev/kurozumi/articles/eccube-plugin-symfony-bundle)**

---

EC-CUBEプラグイン開発において、外部のSymfonyバンドルを利用したいケースがあります。この記事では、プラグインからSymfonyバンドルを登録する方法を解説します。

## ユースケース

以下のような場面で、Symfonyバンドルの登録が必要になります。

- **API開発**: `nelmio/api-doc-bundle` でSwagger UIを提供
- **管理画面拡張**: `knplabs/knp-menu-bundle` でメニューを拡張
- **非同期処理**: `symfony/messenger` でキュー処理を追加
- **PDF生成**: `knplabs/knp-snappy-bundle` でPDF出力機能を追加

## 実装方法

EC-CUBE 4では、プラグインディレクトリ内に `Resource/config/bundles.php` を配置することで、Symfonyバンドルを登録できます。

### ディレクトリ構成

```
app/Plugin/SamplePlugin/
├── Resource/
│   └── config/
│       ├── bundles.php     # バンドル登録ファイル
│       └── services.yaml   # バンドルの設定ファイル
├── PluginManager.php
├── composer.json
└── ...
```

### Resource/config/bundles.php

```php
<?php

return [
    Nelmio\ApiDocBundle\NelmioApiDocBundle::class => ['all' => true],
];
```

これだけでプラグイン有効化時にバンドルが自動的に登録されます。

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4プラグインでSymfonyバンドルを登録する方法](https://zenn.dev/kurozumi/articles/eccube-plugin-symfony-bundle)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
