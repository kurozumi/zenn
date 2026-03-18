---
title: "Symfony UX AI Skills - AIエージェントがSymfony UXを正しく使えるようになる仕組み"
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

Symfonyの公式ブログで「AI Skills for Symfony UX」が発表されました。これは、Claude CodeやGemini CLIなどのAIコーディングエージェントが、Symfony UXコンポーネント（Stimulus、Turbo、TwigComponent、LiveComponent）を正しく使えるようにするための仕組みです。

EC-CUBEはSymfonyベースのため、この仕組みはEC-CUBEのフロントエンド開発にも活用できます。

## AI Skillsとは

AI Skillsは、AIコーディングエージェント向けの「構造化された知識パッケージ」です。`SKILL.md`というMarkdownファイルと参考ドキュメントで構成されています。

通常、AIエージェントは汎用的な知識を持っていますが、特定のフレームワークの「ベストプラクティス」や「よくある落とし穴」までは把握していないことがあります。AI Skillsは、この知識ギャップを埋めるためのものです。

### 仕組み

1. エージェント起動時に各スキルの`description`フィールドを読み込む
2. ユーザーのタスクとマッチするスキルを自動的に検出
3. 該当するスキルの知識を使って実装を支援

明示的にスキルを呼び出す必要はありません。タスクに応じて自動的にアクティベートされます。

## 対応AIツール

AI Skillsは[Agent Skills標準](https://agentskills.io/specification)に準拠しているため、以下のツールで利用できます。

- **Claude Code**（公式推奨）
- Gemini CLI
- OpenAI Codex
- Cursor
- Windsurf
- その他SKILL.md対応プラットフォーム

## 提供されるスキル

SensioLabsのリード開発者であるSimon André氏が、以下の5つのスキルを公開しています。

| スキル | 内容 |
|--------|------|
| **symfony-ux** | Stimulus / Turbo / TwigComponent / LiveComponent の選択判断ツリー |
| **stimulus** | コントローラー、ターゲット、値、アクション、クラス、アウトレット |
| **turbo** | Turbo Drive、Frames、Streams、Mercure統合 |
| **twig-component** | props、ブロック、計算プロパティ、匿名コンポーネント |
| **live-component** | props、アクション、データモデルバインディング、フォーム、emit |

### ファイル構成

各スキルは以下のような構成になっています。

```
skills/stimulus/
├── SKILL.md              # メインスキル定義
├── references/
│   ├── api.md           # APIリファレンス
│   ├── patterns.md      # 推奨パターン
│   └── gotchas.md       # よくある落とし穴
```

## インストール方法

### Claude Codeの場合

リポジトリをクローンして、スキルをコピーします。

```bash
git clone https://github.com/smnandre/symfony-ux-skills.git
cp -r symfony-ux-skills/skills/* ~/.claude/skills/
```

プロジェクト単位でインストールする場合は、プロジェクトの`.claude/skills/`ディレクトリにコピーします。

```bash
cd your-project/
mkdir -p .claude/skills
cp -r symfony-ux-skills/skills/* .claude/skills/
```

### その他のツール

```bash
# Gemini CLI
cp -r skills/* ~/.gemini/skills/

# OpenAI Codex
cp -r skills/* ~/.codex/skills/
```

## 使用例

### 例1: ライブ検索の実装

ユーザーが「商品一覧にライブ検索フィルターを追加して」と指示した場合：

1. エージェントが「ライブ検索」→ LiveComponentタスクと判断
2. `live-component`スキルを自動ロード
3. `data-model`、`emit`等の正しいAPIを使った実装を生成

スキルがない場合は試行錯誤が必要になりますが、スキルがあれば最初から正しいアプローチで実装できます。

### 例2: Stimulus vs LiveComponent の選択

「フォーム送信時にページ遷移なしで結果を表示したい」という要件の場合：

1. `symfony-ux`スキル（オーケストレーター）がロードされる
2. 決定木に基づいて、Turbo StreamsかLiveComponentを推奨
3. ユースケースに応じた最適なコンポーネントを選択

この「どのコンポーネントを使うべきか」という判断は、経験がないと難しいポイントです。スキルがこの判断を支援してくれます。

## EC-CUBEでの活用

EC-CUBEはSymfonyベースのため、Symfony UX AI Skillsをそのまま活用できます。

### 活用シーン

- **カート機能**: LiveComponentで数量変更をリアルタイム反映
- **商品検索**: Turbo Framesで検索結果を部分更新
- **お気に入り登録**: Stimulusコントローラーでアニメーション付きトグル
- **管理画面**: TwigComponentで再利用可能なUIパーツを作成

EC-CUBE固有のコードベースについては、別途EC-CUBE用のスキルを作成することで、さらに精度を上げることも可能です。

## 人間にも有用

AI Skills は、AIエージェントだけでなく人間の開発者にとっても価値があります。

- Symfony UXの各コンポーネントの使い分けが分かる
- 経験豊富なコントリビューターによる推奨パターンが学べる
- よくある落とし穴とその対処法が分かる

特に「Turbo vs LiveComponent vs Stimulus」の選択基準は、公式ドキュメントだけでは判断しづらい部分なので、決定木があるのは非常に助かります。

## まとめ

Symfony UX AI Skillsは、AIコーディングエージェントがSymfony UXを正しく使えるようにするための知識パッケージです。

- 自動アクティベーションで明示的な呼び出し不要
- 決定木により試行錯誤なしで正しい実装へ導く
- Claude Code、Gemini CLI、Cursorなど主要ツールに対応

EC-CUBE開発においても、フロントエンドの実装支援として活用できます。Claude Codeを使っている方は、ぜひインストールしてみてください。

## 参考リンク

- [Introducing AI Skills for Symfony UX (Symfony Blog)](https://symfony.com/blog/introducing-ai-skills-for-symfony-ux)
- [GitHub: symfony-ux-skills](https://github.com/smnandre/symfony-ux-skills)
- [Agent Skills 仕様](https://agentskills.io/specification)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
