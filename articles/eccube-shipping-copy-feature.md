---
title: "EC-CUBE 4の出荷登録画面に「注文者情報をコピー」機能を自作する"
emoji: "📋"
type: "tech"
topics: ["eccube", "eccube4", "php", "javascript", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBEの開発コミュニティで、こんな要望を見つけました。

> **出荷登録画面に「注文者情報をコピー」「他の出荷情報からコピー」機能がほしい**
>
> 出荷情報を追加する際に、現状では名前や住所を手入力する必要がある。
> 自動入力ができないので入力ミスが発生してしまう。
>
> — [EC-CUBE Issue #6595](https://github.com/EC-CUBE/ec-cube/issues/6595)

確かに、受注編集画面には「注文者情報をコピー」ボタンがあるのに、出荷登録画面にはありません。これは不便ですね。

この記事では、この機能を `app/Customize` を使って自分で実装する方法を解説します。

## 現状の問題

出荷登録画面で「出荷情報の追加」をすると、名前や住所を手入力する必要があります。

![現状の出荷登録画面](/images/eccube-shipping-before.png)

出荷情報(2)のように、すべてのフィールドが空欄の状態から入力するのは大変です。受注編集画面には「注文者情報をコピー」ボタンがあるのに、出荷登録画面にはありません。

## 完成イメージ

出荷登録画面の各配送先カードのヘッダー部分（「出荷情報を削除」ボタンの左側）に、以下のボタンを追加します。

- **注文者情報をコピー**: 注文者の名前・住所を配送先にコピー
- **他のお届け先からコピー**: 別の配送先の情報をコピー（複数配送先がある場合）

ボタンをクリックするだけで、注文者情報が自動入力されます。

## 実装方針

EC-CUBEのテンプレートを直接編集せず、以下の方法で拡張します。

1. **Twigテンプレートの拡張**: `TemplateEvent` でボタンを挿入
2. **JavaScriptの追加**: コピー機能を実装

この方法なら、EC-CUBEのアップデート時にカスタマイズが上書きされません。

## ディレクトリ構成

```
app/Customize/
├── Resource/
│   └── template/
│       └── admin/
│           └── Order/
│               └── shipping_copy_button.twig
└── EventSubscriber/
    └── ShippingCopyEventSubscriber.php
```

## 実装手順

### 1. EventSubscriberの作成

`TemplateEvent` を使って、出荷登録画面にボタンを挿入します。

```php
<?php
// app/Customize/EventSubscriber/ShippingCopyEventSubscriber.php

namespace Customize\EventSubscriber;

use Eccube\Event\TemplateEvent;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class ShippingCopyEventSubscriber implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            '@admin/Order/shipping.twig' => 'onAdminOrderShipping',
        ];
    }

    public function onAdminOrderShipping(TemplateEvent $event): void
    {
        // 出荷先カードのヘッダー部分にボタンを挿入
        $event->addSnippet('@admin/Order/shipping_copy_button.twig');
    }
}
```

### 2. ボタン用テンプレートの作成

コピーボタンとJavaScriptを含むテンプレートを作成します。

```twig
{# app/Customize/Resource/template/admin/Order/shipping_copy_button.twig #}

{# コピーボタンのテンプレート #}
<template id="shipping-copy-btn-template">
    <div class="btn-group me-2 shipping-copy-buttons">
        <button type="button" class="btn btn-ec-regular btn-sm copy-order-info">
            <i class="fa fa-clipboard me-1"></i>注文者情報をコピー
        </button>
    </div>
</template>

<script>
$(function() {
    // 注文者情報を取得（受注編集画面から渡されたデータを使用）
    var orderData = {
        name01: '{{ Order.name01|e('js') }}',
        name02: '{{ Order.name02|e('js') }}',
        kana01: '{{ Order.kana01|e('js') }}',
        kana02: '{{ Order.kana02|e('js') }}',
        postal_code: '{{ Order.postal_code|e('js') }}',
        pref: '{{ Order.Pref ? Order.Pref.id : '' }}',
        addr01: '{{ Order.addr01|e('js') }}',
        addr02: '{{ Order.addr02|e('js') }}',
        phone_number: '{{ Order.phone_number|e('js') }}',
        company_name: '{{ Order.company_name|e('js') }}'
    };

    // 出荷先カードのセレクタ
    var shippingCardSelector = '.card.rounded.border-0.mb-4.h-adr';

    // 各出荷先カードにコピーボタンを追加
    $(shippingCardSelector).each(function(index) {
        var $card = $(this);
        var $headerRight = $card.find('.card-header .text-end').first();

        // テンプレートからボタングループをクローン
        var $btnGroup = $('#shipping-copy-btn-template').contents().clone();
        $btnGroup.find('.copy-order-info').attr('data-index', index);

        // 他のお届け先からコピー（2つ以上の配送先がある場合のみ）
        var shippingCount = $(shippingCardSelector).length;
        if (shippingCount > 1) {
            var $copyOtherBtn = $('<button type="button" class="btn btn-ec-regular btn-sm dropdown-toggle dropdown-toggle-split" data-bs-toggle="dropdown" aria-expanded="false">' +
                '<span class="visually-hidden">他のお届け先</span></button>');
            var $dropdownMenu = $('<ul class="dropdown-menu"></ul>');

            for (var i = 0; i < shippingCount; i++) {
                if (i !== index) {
                    $dropdownMenu.append('<li><a class="dropdown-item copy-other-shipping" href="#" data-from="' + i + '" data-to="' + index + '">お届け先' + (i + 1) + 'からコピー</a></li>');
                }
            }

            $btnGroup.append($copyOtherBtn);
            $btnGroup.append($dropdownMenu);
        }

        // ヘッダーの先頭に挿入
        $headerRight.prepend($btnGroup);
    });

    // 注文者情報をコピー
    $(document).on('click', '.copy-order-info', function(e) {
        e.preventDefault();
        var index = $(this).data('index');
        var prefix = '#form_shippings_' + index + '_';

        $(prefix + 'name_name01').val(orderData.name01);
        $(prefix + 'name_name02').val(orderData.name02);
        $(prefix + 'kana_kana01').val(orderData.kana01);
        $(prefix + 'kana_kana02').val(orderData.kana02);
        $(prefix + 'postal_code').val(orderData.postal_code);
        $(prefix + 'address_pref').val(orderData.pref);
        $(prefix + 'address_addr01').val(orderData.addr01);
        $(prefix + 'address_addr02').val(orderData.addr02);
        $(prefix + 'phone_number').val(orderData.phone_number);
        $(prefix + 'company_name').val(orderData.company_name);
    });

    // 他のお届け先からコピー
    $(document).on('click', '.copy-other-shipping', function(e) {
        e.preventDefault();
        var fromIndex = $(this).data('from');
        var toIndex = $(this).data('to');

        var fromPrefix = '#form_shippings_' + fromIndex + '_';
        var toPrefix = '#form_shippings_' + toIndex + '_';

        var fields = [
            'name_name01', 'name_name02',
            'kana_kana01', 'kana_kana02',
            'postal_code',
            'address_pref', 'address_addr01', 'address_addr02',
            'phone_number', 'company_name'
        ];

        fields.forEach(function(field) {
            $(toPrefix + field).val($(fromPrefix + field).val());
        });
    });
});
</script>
```

### 3. キャッシュクリア

カスタマイズを反映するため、キャッシュをクリアします。

```bash
bin/console cache:clear --no-warmup
bin/console cache:warmup
```

## コードの解説

### TemplateEventによるテンプレート拡張

EC-CUBEでは、各テンプレートに対応するイベントが発火されます。

```php
'@admin/Order/shipping.twig' => 'onAdminOrderShipping',
```

このイベントをフックして、`addSnippet()` でテンプレートの末尾にHTMLを挿入できます。

### フォームフィールドのID規則

出荷登録画面のフォームフィールドは、以下の命名規則になっています。

```
form_shippings_{インデックス}_{フィールド名}
```

例えば、1番目の配送先（インデックス0）の姓は `form_shippings_0_name_name01` です。

### XSS対策

注文者情報をJavaScriptに渡す際は、必ず `|e('js')` でエスケープします。

```twig
name01: '{{ Order.name01|e('js') }}'
```

これにより、名前に `'` や `</script>` が含まれていても安全に処理できます。

## 動作確認

1. 管理画面 > 受注管理 > 受注一覧から任意の受注を選択
2. 「出荷登録」をクリック
3. 各配送先カードに「注文者情報をコピー」ボタンが表示されることを確認
4. ボタンをクリックして、注文者情報がコピーされることを確認

## 発展：プラグイン化

このカスタマイズをプラグインとして配布したい場合は、以下の構成にします。

```
app/Plugin/ShippingCopyButton/
├── Controller/
├── EventSubscriber/
│   └── ShippingCopyEventSubscriber.php
├── Resource/
│   └── template/
│       └── admin/
│           └── Order/
│               └── shipping_copy_button.twig
├── composer.json
└── PluginManager.php
```

`composer.json` の例：

```json
{
    "name": "ec-cube/shipping-copy-button",
    "version": "1.0.0",
    "description": "出荷登録画面に注文者情報コピー機能を追加",
    "type": "eccube-plugin",
    "require": {
        "ec-cube/plugin-installer": "^2.0"
    },
    "extra": {
        "code": "ShippingCopyButton"
    }
}
```

## 別解：JavaScriptのみで実装

EventSubscriberを使わず、管理画面のJavaScriptカスタマイズだけで実装することも可能です。

`html/template/admin/assets/js/custom.js` を作成し、管理画面のレイアウトで読み込む方法です。ただし、この方法は注文者情報をDOMから取得する必要があり、出荷登録画面では注文者情報が表示されていないため、別途Ajax通信が必要になります。

今回紹介した `TemplateEvent` を使う方法のほうが、Twigの変数にアクセスできるためシンプルに実装できます。

## まとめ

| ポイント | 内容 |
|---------|------|
| 実装方法 | `TemplateEvent` + `addSnippet()` |
| カスタマイズ場所 | `app/Customize/` |
| 主な機能 | 注文者情報コピー、他配送先からコピー |
| XSS対策 | `\|e('js')` でエスケープ |

EC-CUBEの管理画面は、`TemplateEvent` を使うことでコアファイルを編集せずにカスタマイズできます。issueで要望されている機能も、自分で実装してみると意外と簡単に作れることがあります。

ぜひ試してみてください。

## 参考リンク

- [EC-CUBE Issue #6595](https://github.com/EC-CUBE/ec-cube/issues/6595)
- [EC-CUBE 4 テンプレートのカスタマイズ](https://doc4.ec-cube.net/customize_template)
- [TemplateEvent リファレンス](https://doc4.ec-cube.net/plugin_template)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
