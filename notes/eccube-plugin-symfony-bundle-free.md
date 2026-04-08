# EC-CUBE 4プラグインでSymfonyバンドルを登録する方法

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

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