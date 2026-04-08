# Claude CodeのスキルでEC-CUBE 4のDocker環境を簡単構築

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBE 4の開発環境をDocker Composeで構築する際、コマンドを調べながら実行するのは手間がかかります。Claude Codeの`eccube-docker`スキルを使えば、対話形式で簡単にDocker環境を構築・管理できます。

## eccube-dockerスキルとは

`eccube-docker`は、私がEC-CUBE開発用に作成したClaude Codeのスキルです。Docker Compose環境を対話形式で管理できます。

以下の操作をサポートしています。

- **新規セットアップ**: Docker環境の構築とDB初期化
- **起動**: コンテナの起動
- **停止**: コンテナの停止
- **再起動**: コンテナの再起動

ℹ️ このスキルは自由に使用・カスタマイズできます（MITライセンス）。ご自身の開発スタイルに合わせてカスタマイズしてお使いください。

## SKILL.mdの内容

以下が`eccube-docker`スキルの全内容です。

---
name: eccube-docker
description: EC-CUBE 4 を Docker Compose で起動する。ローカル開発環境のセットアップ時に使用する。
---

# EC-CUBE 4 Docker Compose 環境管理

あなたはEC-CUBE 4のDocker環境構築の専門家です。Docker ComposeでEC-CUBEの起動・停止・管理を行います。

引数が渡された場合（`$ARGUMENTS`）はEC-CUBEのディレクトリパスまたは操作内容として解釈してください。