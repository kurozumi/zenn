---
title: "EC-CUBE 4プラグインでSymfonyバンドルを登録する方法"
emoji: "📦"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

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

## 環境別のバンドル登録

開発環境のみで使用するバンドルは、環境を指定して登録できます。

```php
<?php

return [
    // 全環境で有効
    Some\Bundle\SomeBundle::class => ['all' => true],

    // 開発環境のみ
    Symfony\Bundle\WebProfilerBundle\WebProfilerBundle::class => ['dev' => true],

    // 本番環境以外
    Doctrine\Bundle\FixturesBundle\DoctrineFixturesBundle::class => ['dev' => true, 'test' => true],
];
```

## バンドルの設定

バンドルの設定は、プラグインの `Resource/config/services.yaml` に記述します。

### 設定ファイルの例（services.yaml）

```yaml
# app/Plugin/SamplePlugin/Resource/config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true

    Plugin\SamplePlugin\:
        resource: '../../*'
        exclude: '../../{Entity,Resource,Tests}'

# バンドルの設定
nelmio_api_doc:
    documentation:
        info:
            title: EC-CUBE API
            description: EC-CUBE Plugin API Documentation
            version: 1.0.0
    areas:
        path_patterns:
            - ^/api(?!/doc)
```

## composer.jsonへの依存関係の追加

プラグインが外部バンドルに依存する場合、`composer.json` に依存関係を記述します。

```json
{
    "name": "ec-cube/sample-plugin",
    "require": {
        "nelmio/api-doc-bundle": "^4.0"
    }
}
```

プラグインインストール時に依存パッケージも自動的にインストールされます。

## 実践例：API Documentationバンドルの導入

NelmioApiDocBundleを使ってSwagger UIを提供する例を紹介します。

### 1. composer.jsonの設定

```json
{
    "name": "ec-cube/sample-plugin",
    "version": "1.0.0",
    "require": {
        "nelmio/api-doc-bundle": "^4.0"
    }
}
```

### 2. bundles.phpの作成

```php
<?php
// app/Plugin/SamplePlugin/Resource/config/bundles.php

return [
    Nelmio\ApiDocBundle\NelmioApiDocBundle::class => ['all' => true],
];
```

### 3. services.yamlでバンドルを設定

```yaml
# app/Plugin/SamplePlugin/Resource/config/services.yaml
services:
    _defaults:
        autowire: true
        autoconfigure: true

    Plugin\SamplePlugin\:
        resource: '../../*'
        exclude: '../../{Entity,Resource,Tests}'

nelmio_api_doc:
    documentation:
        info:
            title: Sample Plugin API
            version: 1.0.0
        servers:
            - url: /
              description: API Server
    areas:
        default:
            path_patterns:
                - ^/plugin/sample/api
```

### 4. ルーティングの設定

```yaml
# app/Plugin/SamplePlugin/Resource/config/routes.yaml
app.swagger_ui:
    path: /plugin/sample/api/doc
    methods: GET
    defaults:
        _controller: nelmio_api_doc.controller.swagger_ui
```

## キャッシュのクリア

バンドルを登録した後は、キャッシュのクリアが必要です。

```bash
bin/console cache:clear --no-warmup
bin/console cache:warmup
```

## 注意点

### 1. バージョン互換性

登録するバンドルがEC-CUBEが使用するSymfonyバージョンと互換性があるか確認してください。

| EC-CUBE | Symfony |
|---------|---------|
| 4.0〜4.1 | 4.4 |
| 4.2 | 5.4 |
| 4.3 | 6.4 |

### 2. プラグインの無効化

プラグインを無効化すると、`bundles.php` に登録されたバンドルも自動的に無効化されます。バンドルが提供する機能に依存するデータがある場合は、適切にハンドリングしてください。

## まとめ

EC-CUBEプラグインでSymfonyバンドルを登録するには：

1. `Resource/config/bundles.php` にバンドルクラスを登録する
2. `Resource/config/services.yaml` にバンドルの設定を記述する
3. `composer.json` に依存関係を記述する

`PluginManager` での複雑な処理は不要で、ファイルを配置するだけでバンドルが利用可能になります。この仕組みにより、Symfonyエコシステムの豊富なバンドルをEC-CUBEプラグインで簡単に活用できます。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
