---
title: "Symfony UX AI Skills - AIがWeb開発の「正しいやり方」を学べる仕組み"
emoji: "🤖"
type: "tech"
topics: ["symfony", "AI", "eccube", "php"]
published: true
---

:::message
この記事は Symfony 7.x / 8.x および EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

最近、AIを使ってプログラミングをする人が増えています。Claude CodeやCursor、GitHub Copilotなど、AIがコードを書いてくれるツールが普及してきました。

しかし、AIは万能ではありません。「動くコード」は書けても、「そのプロジェクトに最適なコード」を書くのは難しいことがあります。

この課題を解決するために、Symfonyの公式から「AI Skills」という仕組みが発表されました。簡単に言うと、**AIに「このプロジェクトではこうやって書くのが正解だよ」と教える仕組み**です。

## AIが間違えやすいこと

例えば、Webサイトに「検索機能」を追加したいとします。

Symfonyには複数の方法があります。

- **Stimulus**: シンプルなJavaScriptの書き方
- **Turbo**: ページの一部だけを更新する方法
- **LiveComponent**: サーバーと連携してリアルタイム更新する方法

どれを使うべきかは、状況によって異なります。しかし、AIはこの「使い分け」を間違えることがあります。

結果として、動くけど「イマイチなコード」ができてしまうことも。

## AI Skillsで解決

AI Skillsは、AIに「正しい使い分け」を教えるファイルです。

具体的には：

- **どんな時にどの方法を使うべきか**（判断基準）
- **やってはいけないこと**（よくある失敗）
- **お手本のコード**（ベストプラクティス）

これらをAIが読み込むことで、最初から正しいアプローチで実装できるようになります。

## 誰が作ったの？

Symfonyの開発に深く関わっているSimon André氏（SensioLabs所属）が作成しました。

Symfonyの「中の人」が作っているので、内容は公式に近いクオリティです。

## 対応しているAIツール

以下のツールで使えます。

- **Claude Code**（Anthropic社のCLIツール）
- **Cursor**（AI搭載エディタ）
- **Gemini CLI**（Google製）
- **Windsurf**

最近のAIコーディングツールであれば、ほとんど対応しています。

## 使い方

Claude Codeの場合、以下のコマンドでインストールできます。

```bash
git clone https://github.com/smnandre/symfony-ux-skills.git
cp -r symfony-ux-skills/skills/* ~/.claude/skills/
```

一度インストールすれば、あとは自動的に機能します。「このスキルを使って」と指示する必要はありません。

## 実際の効果

### Before（スキルなし）

ユーザー：「商品検索をリアルタイムにしたい」

AI：「えーと、JavaScriptで書きますね...」（試行錯誤が発生）

### After（スキルあり）

ユーザー：「商品検索をリアルタイムにしたい」

AI：「リアルタイム検索ですね。LiveComponentを使うのが最適です。こう書きます」（一発で正解）

スキルがあると、AIが「経験豊富なSymfony開発者」のように振る舞えるようになります。

## EC-CUBEでも使える

EC-CUBEはSymfonyベースで作られています。そのため、このAI Skillsはそのまま活用できます。

例えば：

- カートの数量変更をリアルタイム反映
- 商品検索の結果を素早く更新
- お気に入りボタンのアニメーション

こうした機能をAIに実装してもらう際に、より良いコードが生成されるようになります。

## 人間にも役立つ

実は、AI Skillsのファイルは人間が読んでも勉強になります。

「Stimulus、Turbo、LiveComponentの違いがよく分からない」という方は、スキルファイルを読むだけでも理解が深まるはずです。

公式ドキュメントより実践的で、「こういう時はこれを使う」という判断基準が明確に書かれています。

## まとめ

- AI Skillsは、AIに「正しいコードの書き方」を教える仕組み
- Symfonyの専門家が作成した公式に近いクオリティ
- Claude Code、Cursorなど主要ツールに対応
- EC-CUBE開発にも活用可能
- 人間の学習リソースとしても有用

AIと一緒にコードを書く機会が増えている今、こうした仕組みを活用することで、より良いコードを効率的に書けるようになります。

## 参考リンク

- [Introducing AI Skills for Symfony UX (Symfony Blog)](https://symfony.com/blog/introducing-ai-skills-for-symfony-ux)
- [GitHub: symfony-ux-skills](https://github.com/smnandre/symfony-ux-skills)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
