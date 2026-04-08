# EC-CUBE 4プラグインにCSS/JSなどの静的ファイルを同梱する方法

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

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