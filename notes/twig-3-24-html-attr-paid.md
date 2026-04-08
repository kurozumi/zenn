## 基本的な使い方

### シンプルな例

<div {{ html_attr({class: 'container', id: 'main'}) }}>
    コンテンツ
</div>

出力：
<div class="container" id="main">コンテンツ</div>

### 配列でクラスを指定

<div {{ html_attr({class: ['btn', 'btn-primary', 'btn-lg']}) }}>
    ボタン
</div>

出力：
<div class="btn btn-primary btn-lg">ボタン</div>

### 条件付き属性

{% set isDisabled = true %}
{% set customId = null %}

<button {{ html_attr({
    disabled: isDisabled,
    id: customId
}) }}>
    送信
</button>

出力：
<button disabled>送信</button>

`id`は`null`なので出力されません。

## 複数の属性をマージ

`html_attr`は複数の属性マップを受け取れます。後から指定した値が優先されます。

{% set baseAttrs = {class: ['btn'], type: 'button'} %}
{% set variantAttrs = {class: ['btn-primary']} %}
{% set stateAttrs = {disabled: true} %}

<button {{ html_attr(baseAttrs, variantAttrs, stateAttrs) }}>
    送信
</button>

出力：
<button class="btn btn-primary" type="button" disabled>送信</button>

クラスは自動でマージされます。

## Vue.jsなどのフレームワークと併用

Twig 3.24では`html_attr_relaxed`というエスケープ戦略も追加されました。

Vue.jsやAlpine.jsで使う特殊な属性（`:`, `@`で始まるもの）をそのまま出力できます。

<input {{ html_attr({
    ':disabled': 'isLoading',
    '@input': 'validate($event)',
    'v-model': 'formData.email'
})|e('html_attr_relaxed') }}>

出力：
<input :disabled="isLoading" @input="validate($event)" v-model="formData.email">

## EC-CUBEでの活用例

### 商品一覧のボタン

{% for Product in Products %}
    <button {{ html_attr({
        class: ['btn', 'btn-primary', Product.stock_find ? '' : 'btn-disabled'],
        disabled: not Product.stock_find,
        'data-product-id': Product.id
    }) }}>
        {% if Product.stock_find %}
            カートに入れる
        {% else %}
            在庫切れ
        {% endif %}
    </button>
{% endfor %}

### フォーム要素

{% set inputAttrs = {
    class: ['form-control', errors ? 'is-invalid' : ''],
    id: 'email',
    name: 'email',
    type: 'email',
    required: true,
    'aria-describedby': errors ? 'email-error' : null
} %}

<input {{ html_attr(inputAttrs) }}>

## Null-Safe演算子の改善

Twig 3.24では、Null-Safe演算子（`?.`）の動作も改善されました。

{{ user?.address?.city }}

以前は`user`が`null`の場合でも`address`にアクセスしようとしてエラーになることがありましたが、今後はPHPと同じように、`null`が返された時点でチェーンが中断されます。

## EC-CUBEで使うには

現時点（2026年3月）のEC-CUBE 4.3系は、Symfony 6.4ベースでTwig 3.x系を使用しています。

Twig 3.24を使うには、`composer.json`でTwigのバージョンを更新します。

composer require twig/twig:^3.24

ただし、EC-CUBEの動作確認は各自で行ってください。

## まとめ

Twig 3.24の`html_attr`関数は、テンプレートの記述を大幅に簡潔にしてくれます。

- 条件分岐の削減でコードがスッキリ
- クラスの自動マージで再利用性アップ
- Vue.jsなどとの連携も簡単

EC-CUBEのテンプレートカスタマイズでも、ぜひ活用してみてください。

## 参考リンク

- [Twig 3.24.0 Released (Symfony Blog)](https://symfony.com/blog/twig-3-24-0-released)
- [Twig Documentation](https://twig.symfony.com/doc/3.x/)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---