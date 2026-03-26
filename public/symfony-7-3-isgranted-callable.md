---
title: '「Voterは書きすぎ？」Symfony 7.3で変わるアクセス制御の新常識'
tags:
  - EC-CUBE
  - PHP
  - Symfony
private: false
updated_at: ''
id: null
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [「Voterは書きすぎ？」Symfony 7.3で変わるアクセス制御の新常識](https://zenn.dev/kurozumi/articles/symfony-7-3-isgranted-callable)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[「Voterは書きすぎ？」Symfony 7.3で変わるアクセス制御の新常識](https://zenn.dev/kurozumi/articles/symfony-7-3-isgranted-callable)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
