# もう$request->headers->get()は書かない。Symfony 8.1 #[MapRequestHeader]

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論：`$request->headers->get()` を書く時代は終わった

> **TL;DR:** HTTPヘッダーを取得するコードが6行→0行になります。

**「Accept-Languageヘッダーを取得して...えーと、どう書くんだっけ」**

Symfony開発者なら、こんなコードを何度も書いてきたはずです：

```php
public function index(Request $request): Response
{
    $acceptLanguage = $request->headers->get('Accept-Language');
    $userAgent = $request->headers->get('User-Agent');
    $authorization = $request->headers->get('Authorization');

    // 以下、処理...
}
```

Symfony 8.1で、これが劇的にシンプルになります。

```php
public function index(
    #[MapRequestHeader] string $acceptLanguage,
    #[MapRequestHeader('User-Agent')] string $userAgent,
    #[MapRequestHeader] ?string $authorization,
): Response {
    // もう$requestを触る必要がない
}
```

`#[MapQueryParameter]`や`#[MapRequestPayload]`の兄弟が、ついにHTTPヘッダーにも登場しました。

## 前提条件

- PHP 8.4以上
- Symfony 8.1以上
- EC-CUBE 4.3以上（将来的にSymfony 8.x対応時に利用可能）