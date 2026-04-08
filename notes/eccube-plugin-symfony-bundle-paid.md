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

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---