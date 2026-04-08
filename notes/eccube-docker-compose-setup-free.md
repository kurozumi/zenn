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

bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d --build
bash
docker compose ps
bash
# Composerの依存関係をコンパイル
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube composer run-script compile

# EC-CUBEインストール（www-dataユーザで非対話モード実行）
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec -u www-data ec-cube bin/console eccube:install -n
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d
bash
docker compose ps
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} down
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} down
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube bin/console cache:clear
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} logs
bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube chown -R www-data:www-data var/
`