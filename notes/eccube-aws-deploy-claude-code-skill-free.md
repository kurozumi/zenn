# 【概念解説】Claude CodeカスタムスキルでEC-CUBEのAWSデプロイを1コマンド化するアイデア

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。


## はじめに

**結論から言います。Claude Codeのカスタムスキルを使えば、EC-CUBEのAWSデプロイが `/deploy-eccube` の1コマンドで完結します。**

ECRへのイメージプッシュ、ECSサービスの更新、デプロイ完了の待機まで、Claude Codeが自動で順番に実行します。手順書を開く必要も、コマンドを1つずつコピペする必要もありません。

「EC-CUBEをAWSに本番デプロイしたいけど、手順が複雑で毎回ドキュメントを見返している」——そういう状況に終止符を打てます。

**この記事で手に入るもの:**

- ローカルで `/deploy-eccube` と打つだけのデプロイ環境
- チームで共有できるデプロイ手順（Git管理）
- EC-CUBE本家を安全に追従するリポジトリ構成

初回セットアップは30〜60分ほど。一度作れば永続的に使えます。

この記事では以下を解説します。

- 必要なツールの準備（GitHub CLI、AWS CLI、Docker）
- EC-CUBEリポジトリのセットアップ（本家を安全に追従する方法）
- AWS インフラの準備（ECR、ECS）
- Claude Codeデプロイスキルの作成
- `/deploy-eccube` コマンドの使い方

## Claude Codeのスキルとは

Claude Codeのスキルは、`SKILL.md` という Markdownファイルに指示を書くだけで作れるカスタムコマンドです。


スキルを作ると `/deploy-eccube` というコマンドが使えるようになります。

| スキルの配置場所 | パス | 適用範囲 |
|---|---|---|
| 個人スキル | `~/.claude/skills/<name>/SKILL.md` | すべてのプロジェクト |
| プロジェクトスキル | `.claude/skills/<name>/SKILL.md` | そのプロジェクトのみ |

`disable-model-invocation: true` を設定すると、Claude が自動的に呼び出さなくなります。デプロイのような副作用のある操作には必ず設定しましょう。