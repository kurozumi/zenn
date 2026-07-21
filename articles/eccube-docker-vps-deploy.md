---
title: "EC-CUBE 4 を Docker で動かす：本体はイメージに焼き、カスタムコードだけを Git 管理する構成"
emoji: "🐳"
type: "tech"
topics: ["eccube", "eccube4", "docker", "php", "symfony"]
published: true
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

EC-CUBE を Docker で動かす記事はすでにいくつもあります。ただ、その多くは「ローカルで開発環境を立てる」ところで話が終わっていて、そのまま VPS や AWS に載せて運用するところまでは面倒を見てくれません。開発と本番で構成がまるで違えば、結局どこかでつまずきます。

そこで、ローカルから本番まで同じ土台で回せることを目標にした Docker 構成を作りました。

https://github.com/kurozumi/eccube-docker

この記事では、その設計方針と使い方を紹介します。

## 何を解決したかったか

EC-CUBE を Docker で運用しようとすると、だいたい次の3点で悩みます。

1. **本体コードをどう管理するか** — `composer create-project` で展開される EC-CUBE 本体は数万ファイルあります。これを丸ごと Git に入れると差分が追えなくなり、バージョンアップのたびに地獄を見ます。
2. **開発と本番の差** — ローカルでは Mailpit や phpMyAdmin を使いたいが、本番には要らない。HTTPS の終端も本番でしか要らない。この差をどう吸収するか。
3. **スケールさせたいとき** — アクセスが増えたときに、セッションやアップロード画像をどう共有し、複数ホストにどう広げるか。

この構成は、この3つに一本の方針で答えを出しています。

## 設計の3本柱

### 1. 本体はイメージにベイクする

いちばんの肝がこれです。EC-CUBE 本体は Git で管理せず、Docker イメージのビルド時に `composer create-project` で焼き込みます。`docker/php/Dockerfile` の該当部分はこうなっています。

```dockerfile
FROM php:8.2-fpm-bookworm

ARG ECCUBE_VERSION=~4.3.0

# ... 拡張やComposerの導入は省略 ...

# DBに触れるスクリプトは起動時に回すので --no-scripts で本体だけ展開する
RUN composer create-project "ec-cube/ec-cube:${ECCUBE_VERSION}" . \
    --no-interaction --no-scripts --prefer-dist
```

ポイントは `--no-scripts` です。`composer create-project` の後処理には DB を必要とするものが含まれるので、ここでは本体のコードを展開するだけに留め、DB が絡む初期化（マイグレーションやキャッシュ生成）はコンテナ起動時のエントリポイントに寄せています。これで「ビルドは DB なしで完結し、DB を使う処理は起動時にやる」という綺麗な分離になります。

デフォルトの `ECCUBE_VERSION` は `~4.3.0` で、ベースは PHP 8.2 の公式イメージ。Redis 拡張は Symfony 6.4 との相性を踏まえて phpredis 6.0.2 にピン留めしてあります。

こうすると、リポジトリに残るのは自分で書いたコードだけになります。本体のバージョンを上げたいときはイメージを作り直すだけ。「本体の差分がノイズになってカスタム差分が埋もれる」問題が根本から消えます。

デメリットは、バージョン変更にイメージの再ビルドが必要なこと。ただ、EC-CUBE 本体を頻繁に書き換えることは通常ありませんから、実運用ではむしろこの制約が「本体を勝手にいじらない」規律として働きます。

### 2. Git で追うのは自分のコードだけ

本体は名前付きボリュームに載せ、その上に自分のディレクトリだけを bind mount で重ねます。Git 管理下に置くのは次のディレクトリです。

```
app/
├── Customize/            # コントローラ・エンティティ・DIサービス
├── template/             # テーマ（Twig上書き）
├── DoctrineMigrations/   # 独自のスキーマ変更
├── Plugin/               # プラグイン
└── config/eccube/packages/  # ロギングやキャッシュなどのフレームワーク設定
frontend/                 # Sass のソース
html/user_data/           # 独自 CSS/JS
```

本体と自分のコードがボリューム構成のレベルできっちり分離されているので、どこを触っていいのか迷いません。

### 3. スキーマの同期は自分のマイグレーションだけ

本体のマイグレーションはイメージビルド時に適用済みです。したがって、環境間で同期を気にするのは `app/DoctrineMigrations/` に置いた自分のマイグレーションだけになります。ここでも「本体のことは考えなくていい」が徹底されています。

## ローカルで動かす

セットアップは初期化スクリプト一本です。

```bash
git clone https://github.com/kurozumi/eccube-docker eccube-docker
cd eccube-docker
bin/init.sh                    # .env 生成 → AUTH_MAGIC 生成 → build → up
docker compose logs -f ec-cube # 初期化ログを追う
```

`bin/init.sh` が `.env` を作り、`AUTH_MAGIC` を自動生成し、イメージのビルドと起動まで済ませます。立ち上がったら次の URL にアクセスできます。

- フロント: http://localhost:8080/
- 管理画面: http://localhost:8080/admin/
- Mailpit（メール確認）: http://localhost:8025/
- phpMyAdmin: http://localhost:8081/

Compose ファイルは役割ごとに分かれています。

| ファイル | 役割 |
|---|---|
| `compose.yaml` | ベース。ec-cube / worker / nginx / mariadb / redis |
| `compose.override.yaml` | 開発用。Mailpit・phpMyAdmin・Sass監視・rwマウントを追加 |
| `compose.prod.yaml` | 本番用。公開方式をプロファイルで切り替え |
| `compose.app.yaml` | マルチホスト時のアプリ層のみ（DB/Redisは外部参照） |

`compose.override.yaml` は `docker compose` が自動で読み込むため、ローカルでは何も指定しなくても開発向けサービスが立ち上がります。逆に本番では `compose.prod.yaml` を明示するので、開発用サービスは混ざりません。この「差分を別ファイルに切り出す」やり方で、開発と本番の構成差を素直に表現しています。

## カスタマイズの置き場所

### PHP

`app/Customize/` が `Customize\` 名前空間の置き場です。コントローラ、イベントリスナー、Form、エンティティ拡張、DIサービス、コンソールコマンドをここに書きます。この名前空間はバージョン切り替えをまたいでも生き残るので、本体を作り直しても自分のコードは無傷です。

### テンプレート

`app/template/` に Twig の上書きを置きます。フロント・管理画面どちらのテーマも本体のテーマエンジンに乗ります。

### CSS/JS

`frontend/scss/` の Sass をビルドして `html/user_data/assets/css/` に吐き出します。出力した `customize.css` は本体が `style.css` の後に自動で読み込むため、上書きが素直に効きます。開発中は監視ビルドを回せます。

```bash
bin/assets.sh watch
```

### プラグイン

プラグインは通常どおり生成でき、`app/Plugin/` に rw マウントされるのでそのまま開発できます。

```bash
docker compose exec ec-cube runuser -u www-data -- \
  php bin/console eccube:plugin:generate MyPlugin
```

## 非同期メール（Symfony Messenger）

地味に効くのがこれです。注文完了メールなどを Symfony Messenger で `messenger_messages` テーブルにキューイングし、`worker` サービスが非同期に送信します。

- 注文完了処理がメール送信でブロックされない
- 失敗しても永続リトライ（5秒 → 15秒 → 45秒、その後 failed キューへ）

状態はコンソールで確認できます。

```bash
docker compose exec ec-cube runuser -u www-data -- php bin/console messenger:stats
docker compose exec ec-cube runuser -u www-data -- php bin/console messenger:failed:show
```

同期送信に戻したいときは `app/config/eccube/packages/messenger.yaml` を外して `worker` を止めるだけです。

## 本番への公開方式を選ぶ

本番は `compose.prod.yaml` のプロファイルで公開方式を切り替えます。

- **`tunnel`** — Cloudflare Tunnel。ポートを一切開けずに公開する
- **`caddy`** — Caddy で Let's Encrypt を終端し、80/443 で公開する
- **未指定** — `127.0.0.1:8080` でホスト内のみに待ち受け、前段の外部ロードバランサに任せる

`.env` の `COMPOSE_PROFILES` を切り替えるだけで、同じリポジトリのまま公開方式を選べます。小さな個人サイトなら Cloudflare Tunnel、自前で証明書まで面倒を見たいなら Caddy、ALB の後ろに置くならプロファイル未指定、と使い分けられます。

デプロイ自体は `bin/publish.sh` 一本です。中身はベースと本番用の Compose ファイルを重ねて起動しているだけで、選んだプロファイルに応じたサービスが立ち上がります。

```bash
bin/publish.sh
# 実体はおおむね:
# docker compose -f compose.yaml -f compose.prod.yaml up -d --build
```

## スケールさせる

### 単一ホストの範囲でのチューニング

まずは1台の中でできることが一通り入っています。

- php-fpm のワーカー数チューニング（`.env` の `PHP_FPM_MAX_CHILDREN` ほか）
- 本番向け OPcache（`validate_timestamps=0`）
- Redis によるアプリケーションキャッシュ
- MariaDB のバッファプール・接続数の最適化
- nginx の gzip と静的ファイルのキャッシュヘッダ

php-fpm のワーカー数は搭載メモリから逆算します。EC-CUBE は1プロセスあたりそれなりにメモリを食うので、闇雲に増やすとスワップして逆に遅くなります。`.env` の `PHP_FPM_MAX_CHILDREN` を「使えるメモリ ÷ 1プロセスあたりのメモリ」で見積もり、後述の php-fpm ステータスで `max_children_reached` を見ながら詰めていくのが安全です。

### 1台の中でレプリカを増やす

1台のまま app コンテナだけ横に増やすこともできます。

```bash
docker compose up -d --scale ec-cube=3
```

ただし、起動時のマイグレーションとキャッシュクリアが全レプリカで走ると競合します。`var/cache` は共有されるため、走行中にレプリカを足すとコンパイル済みキャッシュがクリアされ、一瞬 500 になることがあります。増やすときはスキップフラグを付けます。

```bash
ECCUBE_SKIP_DB_INIT=1 ECCUBE_SKIP_CACHE_CLEAR=1 \
  docker compose up -d --scale ec-cube=3
```

### 複数ホストへ広げる

1台で足りなくなったら、状態を外部に逃がして横に広げます。

- **セッション共有** — `Customize\Session\RawRedisSessionHandler` で Redis にセッションを載せる
- **アップロード画像の共有** — ローカルボリュームを NFS/EFS に置き換える
- **アプリ層だけを増やす** — 各ホストで `compose.app.yaml`（app + nginx のみ）を動かし、DB・Redis は外部の共有インスタンスを参照する

このとき、マイグレーションは1台だけで実行し、残りは `ECCUBE_SKIP_DB_INIT=1` で起動時のマイグレーションとキャッシュクリアをスキップします。全ホストが同時にスキーマをいじって競合する、という事故を避けられます。

前段にロードバランサを置く場合は、各ホストの `.env` に `TRUSTED_PROXIES` を設定します。これがないと EC-CUBE が転送ヘッダ（`X-Forwarded-For` など）を信頼せず、クライアント IP や HTTPS 判定がおかしくなります。

そしてマルチホストで見落としやすいのが DB の接続数です。全ホストの php-fpm ワーカーが一斉に DB を掴むと、あっという間に `max_connections` に達します。ざっくり次の式で見積もります。

```
Σ(各ホストの PHP_FPM_MAX_CHILDREN) + worker 数 + 余裕分 ≤ max_connections
```

たとえば「4ホスト × 50 children = 200」で MariaDB のデフォルト上限に張り付きます。ホストを増やす計画があるなら、`docker/mariadb/conf.d/eccube.cnf` で `max_connections` を先に引き上げておきます。

## バージョンアップ・バックアップ・テスト

運用に必要なスクリプトも `bin/` に揃っています。

```bash
# バージョン切り替え（.env更新 → down -v → 再ビルド → 再インストール）
bin/switch-version.sh ~4.2.0

# バックアップ（db.sql.gz と upload.tar.gz を世代管理）
bin/backup.sh
BACKUP_KEEP=14 bin/backup.sh

# リストア
bin/restore.sh backups/20260721-040000

# カスタムコードのテストだけ実行
bin/test.sh
bin/test.sh --testdox
```

バックアップは `mysqldump --single-transaction` を使うので、止めずに一貫性のあるダンプが取れます。テストは `app/Customize/Tests/` に置いた自分のテストだけを対象にするので、本体を作り直しても壊れません。

## 動いているかを確認する

運用では「落ちていないか」「詰まっていないか」を見られることが大事です。全サービスにヘルスチェックが仕込んであるので、まずはこれで状態が見えます。

```bash
docker compose ps   # healthy / unhealthy が一覧で出る
```

php-fpm のプール状況はステータスページで確認できます。特に `max_children_reached`（ワーカー枯渇の回数）は、増設やチューニングの判断材料になります。

```bash
docker compose exec ec-cube sh -c \
  'SCRIPT_NAME=/fpm-status SCRIPT_FILENAME=/fpm-status REQUEST_METHOD=GET \
   cgi-fcgi -bind -connect 127.0.0.1:9000'
```

非同期メールを使っているなら、`worker` のログとキューの詰まりも見ておきます。

```bash
docker compose logs -f worker
docker compose exec worker runuser -u www-data -- \
  php bin/console messenger:stats
```

外形監視は UptimeRobot や Cloudflare Health Checks でトップページ `/` を叩いておけば十分です。

## ハマりどころ

実際に使ううえで気をつける点も書いておきます。

- `app/Customize/` と `app/template/` は空にしてはいけません。本体がこのディレクトリ構造に依存しているため、`.gitkeep` を置いてあります。
- Linux ホストでは `make:migration` の実行に、`app/*` の所有権を www-data（uid 33）に合わせる必要があります。
- Redis セッションはロックしない（last-write-wins）方式です。通常のブラウジングには十分ですが、この前提は理解しておきます。
- フルページキャッシュ（nginx の `fastcgi_cache`）はデフォルトで無効です。ページに CSRF トークンやセッション状態が埋め込まれるため、安易に有効化すると事故ります。
- `var/cache` は横並びのレプリカ間で共有されます。走行中にレプリカを足すとコンパイル済みキャッシュがクリアされ、一瞬 500 が出ることがあります。増設時は前述のスキップフラグを使います。

動作要件は Docker Engine と Compose v2.24 以上、CPU は amd64 / arm64 どちらも対応です。

## まとめ

この構成の芯は「本体はイメージに焼き、Git で追うのは自分のコードだけ」という一点に尽きます。ここが決まると、バージョンアップの差分、開発と本番の構成差、スケール時の状態共有といった悩みが、すべて同じ方針の延長で片付きます。

EC-CUBE を Docker できちんと運用したい方の叩き台になれば幸いです。詳しい設定はリポジトリの README を参照してください。

https://github.com/kurozumi/eccube-docker

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
