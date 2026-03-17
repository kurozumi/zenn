---
title: EC-CUBE 4プラグインにCSS/JSなどの静的ファイルを同梱する方法
tags:
  - PHP
  - Symfony
  - EC-CUBE
private: false
updated_at: '2026-03-17T21:49:34+09:00'
id: e4ed230f75d13b9d53a5
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4プラグインにCSS/JSなどの静的ファイルを同梱する方法](https://zenn.dev/and_and/articles/eccube-plugin-static-assets)**

---

EC-CUBEプラグイン開発において、独自のCSSやJavaScriptを同梱したいケースがあります。この記事では、プラグインに静的ファイルを配置し、テンプレートから読み込む方法を解説します。

## 静的ファイルの配置場所

プラグインの静的ファイルは `Resource/assets` ディレクトリに配置します。

### ディレクトリ構成

```
app/Plugin/SamplePlugin/
├── Resource/
│   ├── assets/           # 静的ファイルを配置
│   │   ├── css/
│   │   │   └── style.css
│   │   ├── js/
│   │   │   └── script.js
│   │   └── img/
│   │       └── logo.png
│   ├── config/
│   │   └── services.yaml
│   └── template/
│       └── ...
└── ...
```

## インストール時の動作

プラグインをインストールすると、`PluginService::copyAssets()` メソッドにより `Resource/assets` ディレクトリの内容が公開ディレクトリにコピーされます。

**コピー元**: `app/Plugin/SamplePlugin/Resource/assets/`
**コピー先**: `html/plugin/SamplePlugin/assets/`

```php
// EC-CUBE本体の PluginService.php より
public function copyAssets($pluginCode)
{
    $assetsDir = $this->calcPluginDir($pluginCode).'/Resource/assets';

    if (file_exists($assetsDir)) {
        $file = new Filesystem();
        $file->mirror($assetsDir, $this->eccubeConfig['plugin_html_realdir'].$pluginCode.'/assets');
    }
}
```

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4プラグインにCSS/JSなどの静的ファイルを同梱する方法](https://zenn.dev/and_and/articles/eccube-plugin-static-assets)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
