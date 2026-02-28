---
title: "Claude CodeのスキルでEC-CUBE 4のDocker環境を簡単構築"
emoji: "🐳"
type: "tech"
topics: ["eccube", "eccube4", "docker", "claudecode"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE 4の開発環境をDocker Composeで構築する際、コマンドを調べながら実行するのは手間がかかります。Claude Codeの`eccube-docker`スキルを使えば、対話形式で簡単にDocker環境を構築・管理できます。

## eccube-dockerスキルとは

`eccube-docker`は、私がEC-CUBE開発用に作成したClaude Codeのスキルです。Docker Compose環境を対話形式で管理できます。

以下の操作をサポートしています。

- **新規セットアップ**: Docker環境の構築とDB初期化
- **起動**: コンテナの起動
- **停止**: コンテナの停止
- **再起動**: コンテナの再起動

:::message
このスキルは自由に使用・カスタマイズできます（MITライセンス）。ご自身の開発スタイルに合わせてカスタマイズしてお使いください。
:::

## SKILL.mdの内容

以下が`eccube-docker`スキルの全内容です。

````markdown
---
name: eccube-docker
description: EC-CUBE 4 を Docker Compose で起動する。ローカル開発環境のセットアップ時に使用する。
---

# EC-CUBE 4 Docker Compose 環境管理

あなたはEC-CUBE 4のDocker環境構築の専門家です。Docker ComposeでEC-CUBEの起動・停止・管理を行います。

引数が渡された場合（`$ARGUMENTS`）はEC-CUBEのディレクトリパスまたは操作内容として解釈してください。

## 前提条件

- Docker と Docker Compose がインストールされていること

## 操作の確認

AskUserQuestion ツールで以下を確認:

- EC-CUBEのディレクトリ（デフォルト: カレントディレクトリ）
- データベース:
  - **MySQL**（推奨）
  - **PostgreSQL**
- 実行する操作:
  - **新規セットアップ**: 初めてDocker環境を構築する（起動 + DB初期化）
  - **起動**: すでにDB初期化済みで、コンテナを起動するだけ
  - **停止**: コンテナを停止する
  - **再起動**: コンテナを再起動する

## データベース別の compose ファイル

| データベース | compose ファイル |
|-------------|------------------|
| MySQL | `docker-compose.mysql.yml` |
| PostgreSQL | `docker-compose.pgsql.yml` |

以降のコマンドでは、選択されたDBに応じて compose ファイルを使い分けてください。

---

## 新規セットアップ

以下のコマンドでは `${DB_COMPOSE}` を選択したDBのcomposeファイルに置き換えてください:
- MySQL: `docker-compose.mysql.yml`
- PostgreSQL: `docker-compose.pgsql.yml`

### 1. Docker Compose で起動

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d --build
```

### 2. コンテナ起動確認

```bash
docker compose ps
```

ec-cube コンテナが起動していることを確認してください。

### 3. データベーススキーマの初期化

```bash
# Composerの依存関係をコンパイル
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube composer run-script compile

# EC-CUBEインストール（www-dataユーザで非対話モード実行）
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec -u www-data ec-cube bin/console eccube:install -n
```

**重要:** `eccube:install` コマンドは必ず `www-data` ユーザで実行し、`-n`（非対話モード）オプションを使用してください。

### 4. 動作確認

- フロント画面: http://localhost:8080/
- 管理画面: http://localhost:8080/admin/
  - ID: `admin`
  - パスワード: `password`

---

## 起動

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d
```

起動確認:
```bash
docker compose ps
```

---

## 停止

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} down
```

---

## 再起動

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} down
docker compose -f docker-compose.yml -f ${DB_COMPOSE} up -d
```

---

## ローカル開発について

Docker Compose のボリュームマウントにより、ローカルのファイル変更が即座にコンテナに反映されます。

- `app/` - アプリケーションコード
- `src/` - EC-CUBEコアコード
- `html/` - 公開ディレクトリ
- `var/` - キャッシュ、ログ等

キャッシュクリアが必要な場合:

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube bin/console cache:clear
```

## よく使うコマンド

| 操作 | コマンド |
|------|----------|
| ログ確認 | `docker compose logs -f ec-cube` |
| コンテナに入る | `docker compose exec ec-cube bash` |
| キャッシュクリア | `docker compose exec ec-cube bin/console cache:clear` |
| マイグレーション実行 | `docker compose exec ec-cube bin/console doctrine:migrations:migrate` |

## トラブルシューティング

### コンテナが起動しない場合

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} logs
```

### パーミッションエラーの場合

```bash
docker compose -f docker-compose.yml -f ${DB_COMPOSE} exec ec-cube chown -R www-data:www-data var/
```

### データベース接続エラーの場合

データベースコンテナが完全に起動するまで待ってから、再度 `eccube:install` を実行してください。

## 参考

- [EC-CUBE 4 ドキュメント - Docker Composeを使用したインストール](https://doc4.ec-cube.net/quickstart/docker_compose_install)
````

## スキルの設置方法

### 1. ディレクトリの作成

Claude Codeのスキルは `~/.claude/skills/` ディレクトリに配置します。

```bash
mkdir -p ~/.claude/skills/eccube-docker
```

### 2. SKILL.mdファイルの作成

上記の内容を `SKILL.md` ファイルとして保存します。

```bash
# ファイルを作成
touch ~/.claude/skills/eccube-docker/SKILL.md
```

お好みのエディタで `~/.claude/skills/eccube-docker/SKILL.md` を開き、上記のSKILL.mdの内容をコピー＆ペーストしてください。

### 3. ディレクトリ構成の確認

設置後のディレクトリ構成は以下のようになります。

```
~/.claude/
└── skills/
    └── eccube-docker/
        └── SKILL.md
```

### 4. スキルの確認

Claude Codeを起動して、スキルが認識されているか確認します。

```
/eccube-docker
```

と入力すると、スキルが起動します。

## スキルの使い方

### 1. スキルの実行

EC-CUBEのソースコードがあるディレクトリで、Claude Codeを起動し、以下のコマンドを入力します。

```
/eccube-docker
```

### 2. 対話形式で設定

スキルを実行すると、以下の項目を順番に聞かれます。

1. **EC-CUBEのディレクトリ**: EC-CUBEのソースコードがあるパス（デフォルト: カレントディレクトリ）
2. **データベース**: MySQL（推奨）または PostgreSQL
3. **実行する操作**: 新規セットアップ / 起動 / 停止 / 再起動

### 3. 自動実行

選択した内容に応じて、必要なDockerコマンドが自動的に実行されます。

## 新規セットアップの流れ

「新規セットアップ」を選択すると、以下の処理が順番に実行されます。

### Step 1: Docker Composeで起動

選択したデータベースに応じたcomposeファイルを使用してコンテナを起動します。

```bash
# MySQLの場合
docker compose -f docker-compose.yml -f docker-compose.mysql.yml up -d --build

# PostgreSQLの場合
docker compose -f docker-compose.yml -f docker-compose.pgsql.yml up -d --build
```

### Step 2: コンテナ起動確認

```bash
docker compose ps
```

ec-cubeコンテナが正常に起動していることを確認します。

### Step 3: データベーススキーマの初期化

```bash
# Composerの依存関係をコンパイル
docker compose exec ec-cube composer run-script compile

# EC-CUBEインストール（www-dataユーザで非対話モード実行）
docker compose exec -u www-data ec-cube bin/console eccube:install -n
```

:::message alert
`eccube:install`コマンドは必ず`www-data`ユーザで実行してください。rootユーザで実行すると、ファイルのパーミッションの問題が発生します。
:::

### Step 4: 動作確認

セットアップが完了したら、ブラウザでアクセスできます。

| 画面 | URL |
|------|-----|
| フロント画面 | http://localhost:8080/ |
| 管理画面 | http://localhost:8080/admin/ |

管理画面のログイン情報：
- ID: `admin`
- パスワード: `password`

## まとめ

`eccube-docker`スキルを使えば、EC-CUBE 4のDocker環境構築を対話形式で簡単に行えます。

1. `~/.claude/skills/eccube-docker/SKILL.md` にスキルファイルを配置
2. `/eccube-docker`でスキルを起動
3. データベースと操作を選択
4. 自動的にDockerコマンドが実行される

Docker Composeのコマンドを覚えていなくても、スキルがガイドしてくれるので、初めてEC-CUBEの開発環境を構築する方にもおすすめです。

## 参考

- [EC-CUBE 4 ドキュメント - Docker Composeを使用したインストール](https://doc4.ec-cube.net/quickstart/docker_compose_install)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
