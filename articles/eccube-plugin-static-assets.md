---
title: "EC-CUBE 4プラグインにCSS/JSなどの静的ファイルを同梱する方法"
emoji: "🎨"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

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

## Twigテンプレートでの読み込み

### asset関数を使用する

EC-CUBEでは、Symfonyの `asset()` 関数に `plugin` パッケージが設定されています。

```yaml
# app/config/eccube/packages/framework.yaml
framework:
    assets:
        packages:
            plugin:
                base_path: '/html/plugin'
```

これにより、以下のようにプラグインの静的ファイルを読み込めます。

### CSSの読み込み

```twig
<link rel="stylesheet" href="{{ asset('SamplePlugin/assets/css/style.css', 'plugin') }}">
```

### JavaScriptの読み込み

```twig
<script src="{{ asset('SamplePlugin/assets/js/script.js', 'plugin') }}"></script>
```

### 画像の読み込み

```twig
<img src="{{ asset('SamplePlugin/assets/img/logo.png', 'plugin') }}" alt="Logo">
```

## 実践例：管理画面にCSSとJSを追加

プラグインの管理画面テンプレートで独自のスタイルとスクリプトを適用する例を紹介します。

### 1. 静的ファイルの作成

```css
/* app/Plugin/SamplePlugin/Resource/assets/css/admin.css */
.sample-plugin-container {
    padding: 20px;
    background-color: #f8f9fa;
    border-radius: 4px;
}

.sample-plugin-title {
    color: #333;
    font-size: 1.5rem;
    margin-bottom: 1rem;
}
```

```js
// app/Plugin/SamplePlugin/Resource/assets/js/admin.js
document.addEventListener('DOMContentLoaded', function() {
    console.log('SamplePlugin admin.js loaded');

    // プラグイン固有の処理
    const container = document.querySelector('.sample-plugin-container');
    if (container) {
        // 初期化処理
    }
});
```

### 2. テンプレートでの読み込み

```twig
{# app/Plugin/SamplePlugin/Resource/template/admin/index.twig #}
{% extends '@admin/default_frame.twig' %}

{% block stylesheet %}
    <link rel="stylesheet" href="{{ asset('SamplePlugin/assets/css/admin.css', 'plugin') }}">
{% endblock %}

{% block javascript %}
    <script src="{{ asset('SamplePlugin/assets/js/admin.js', 'plugin') }}"></script>
{% endblock %}

{% block main %}
    <div class="sample-plugin-container">
        <h2 class="sample-plugin-title">SamplePlugin 設定</h2>
        {# コンテンツ #}
    </div>
{% endblock %}
```

## フロント画面への適用

フロント画面のテンプレートでも同様に読み込めます。

```twig
{# app/Plugin/SamplePlugin/Resource/template/default/index.twig #}
{% extends 'default_frame.twig' %}

{% block stylesheet %}
    <link rel="stylesheet" href="{{ asset('SamplePlugin/assets/css/front.css', 'plugin') }}">
{% endblock %}

{% block javascript %}
    <script src="{{ asset('SamplePlugin/assets/js/front.js', 'plugin') }}"></script>
{% endblock %}

{% block main %}
    {# コンテンツ #}
{% endblock %}
```

## 注意点

### 1. プラグイン更新時の挙動

プラグインを更新（アップデート）した場合、静的ファイルは自動的に再コピーされます。手動でファイルを編集した場合は上書きされるので注意してください。

### 2. アンインストール時の削除

プラグインをアンインストールすると、`html/plugin/プラグインコード/` ディレクトリは `PluginService::removeAssets()` により削除されます。

### 3. キャッシュバスティング

ブラウザキャッシュの問題を避けるため、バージョン番号をクエリパラメータに付与することを推奨します。

```twig
<link rel="stylesheet" href="{{ asset('SamplePlugin/assets/css/style.css', 'plugin') }}?v={{ constant('Plugin\\SamplePlugin\\SamplePlugin::VERSION') }}">
```

プラグインクラスにバージョン定数を定義しておきます。

```php
// app/Plugin/SamplePlugin/SamplePlugin.php
namespace Plugin\SamplePlugin;

use Eccube\Plugin\AbstractPluginManager;

class SamplePlugin extends AbstractPluginManager
{
    public const VERSION = '1.0.0';
}
```

### 4. 開発時のファイル更新

開発中に静的ファイルを変更した場合、手動で `html/plugin/` にコピーするか、プラグインを一度無効化→有効化することで反映できます。

```bash
# プラグインを再有効化してアセットを再コピー
bin/console eccube:plugin:disable --code=SamplePlugin
bin/console eccube:plugin:enable --code=SamplePlugin
```

## まとめ

EC-CUBEプラグインに静的ファイルを同梱するには：

1. `Resource/assets/` ディレクトリにCSS/JS/画像を配置する
2. インストール時に `html/plugin/プラグインコード/assets/` に自動コピーされる
3. Twigテンプレートで `asset('プラグインコード/assets/ファイルパス', 'plugin')` で読み込む

この仕組みにより、プラグイン固有のスタイルやスクリプトを簡単に配布・適用できます。

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
