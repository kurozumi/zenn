# 「Voterは書きすぎ？」Symfony 7.3で変わるアクセス制御の新常識

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論：1箇所だけのアクセス制御にVoterは重すぎた

**「この商品の編集権限チェック、Voterファイル作るほどじゃないんだよな...」**

Symfony開発者なら一度は思ったことがあるはずです。

Symfony 7.3で、この悩みが解消されます。`#[IsGranted]` 属性にクロージャを直接書けるようになりました。

```php
// Before: Voter + Controller で2ファイル必要
// After: Controllerに数行追加するだけ
#[IsGranted(static function (IsGrantedContext $context, mixed $subject): bool {
    return $subject->getCreator() === $context->user;
}, subject: 'product')]
public function edit(Product $product): Response { }
```

「で、いつ使うの？」という方のために、EC-CUBEでの実践例を紹介します。

## 前提条件

- PHP 8.5以上（属性内でClosureが使えるバージョン）
- Symfony 7.3以上
- EC-CUBE 4.3以上（将来的にSymfony 7.x対応時に利用可能）