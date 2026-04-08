# Twig 3.24の新機能html_attrが便利すぎる - HTML属性の記述が劇的に簡単に

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## はじめに

2026年3月18日にリリースされたTwig 3.24.0で、待望の`html_attr`関数が追加されました。

この機能を使うと、HTML属性の記述が劇的に簡単になります。EC-CUBEのテンプレートカスタマイズでも活用できる、実用的な新機能です。

## Before / After

まずは、どれくらい便利になるか見てみましょう。

### Before（従来の書き方）

```twig
<button
    class="{{ classes|join(' ') }}"
    {% if id %}id="{{ id }}"{% endif %}
    {% if disabled %}disabled{% endif %}
    {% if ariaLabel %}aria-label="{{ ariaLabel }}"{% endif %}
>
    送信
</button>
```

条件分岐だらけで読みにくいですね。

### After（html_attr を使った書き方）

```twig
<button {{ html_attr({
    class: classes,
    id: id,
    disabled: disabled,
    'aria-label': ariaLabel
}) }}>
    送信
</button>
```

スッキリしました。`html_attr`が以下を自動で処理してくれます。

- **配列のclass** → スペース区切りで結合
- **nullやfalse** → 属性を出力しない
- **true** → 属性名だけ出力（`disabled`など）
- **エスケープ** → 自動で適用