---
title: "EC-CUBEのデプロイ（Nginx + PHP-FPM + MySQL + Let's Encrypt）"
---

この章では、EC-CUBEのソースコードをサーバーに配置し、ブラウザからアクセスできる状態にするまでの手順を説明します。

## ディレクトリの準備

EC-CUBEを設置するフォルダを作成します。

```bash
sudo mkdir -p /var/www/eccube
sudo chown eccube-admin:www-data /var/www/eccube
sudo chmod 775 /var/www/eccube
```

`chown eccube-admin:www-data` は「このフォルダの所有者を `eccube-admin`、グループを `www-data` にする」という意味です。Webサーバー（Nginx・PHP-FPM）は `www-data` というユーザーで動作するため、グループに含めることでファイルの読み書きが可能になります。

## EC-CUBEのダウンロードと準備

GitHubからEC-CUBEのソースコードを取得し、本番環境用の設定でインストールします。

```bash
cd /var/www/eccube

# GitHubからソースコードを取得
git clone https://github.com/EC-CUBE/ec-cube.git .

# 最新の安定版タグに切り替える
git checkout $(git tag -l "4.3.*" | sort -V | tail -1)

# 本番環境用に依存ライブラリをインストール
composer install --no-dev --optimize-autoloader

# .envを削除してブラウザのインストーラーを有効化する
rm -f .env
```

:::message
`git checkout 4.3` ではなく最新リリースタグを指定します。`4.3` ブランチは開発が継続されているため、予期しない変更が含まれる場合があります。
:::

:::message
`.env` ファイルが存在しないと、EC-CUBEはブラウザでのインストールウィザードを表示します。後の手順でウィザードを使ってデータベース設定を行います。
:::

## パーミッション（アクセス権限）の設定

パーミッションとは「誰がファイルを読み書きできるか」を決める設定です。設定が緩すぎると第三者がファイルを書き換えられる恐れがあり、厳しすぎるとEC-CUBEが動作しません。

### Webサーバーが使うユーザー（www-data）とは

`www-data` はNginxやPHP-FPMが動作する際に使うシステムユーザーです。ブラウザからのリクエストは最終的にこのユーザーとして処理されます。

```
ブラウザ → Nginx（www-dataで動作）→ PHP-FPM（www-dataで動作）→ EC-CUBEのファイル
```

EC-CUBEが商品画像のアップロードやキャッシュを生成するとき、このユーザーがファイルの書き込みを行います。書き込みが必要なフォルダには `www-data` の権限を付与する必要があります。

### 権限を設定する

```bash
# 所有者をeccube-admin、グループをwww-dataに設定
sudo chown -R eccube-admin:www-data /var/www/eccube

# フォルダは755（所有者: 読み書き実行 / グループ・その他: 読み実行のみ）
sudo find /var/www/eccube -type d -exec chmod 755 {} \;

# ファイルは644（所有者: 読み書き / グループ・その他: 読みのみ）
sudo find /var/www/eccube -type f -exec chmod 644 {} \;

# Webサーバーが書き込む必要があるフォルダを775に緩める
sudo chmod -R 775 /var/www/eccube/var        # キャッシュ・ログ
sudo chmod -R 775 /var/www/eccube/html       # 公開ディレクトリ
sudo chmod -R 775 /var/www/eccube/app/Plugin
sudo chmod -R 775 /var/www/eccube/app/PluginData
sudo chmod -R 775 /var/www/eccube/app/proxy
sudo chmod -R 775 /var/www/eccube/app/template
sudo chmod -R 775 /var/www/eccube/vendor     # プラグインインストール時に必要
sudo chmod 664 /var/www/eccube/composer.json
sudo chmod 664 /var/www/eccube/composer.lock
```

## Webサーバー（Nginx）の設定

Nginxに「このドメインへのアクセスをEC-CUBEに渡す」という設定を追加します。

以下のコマンドで設定ファイルを作成します。

```bash
sudo nano /etc/nginx/sites-available/eccube
```

以下の内容を貼り付けてください（`your-domain.com` は自分のドメインに書き換えてください）。

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/eccube/html;
    index index.php;

    # アップロードできるファイルの最大サイズ（32MB）
    client_max_body_size 32M;

    # セキュリティヘッダー（ブラウザへの指示）
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # すべてのリクエストをEC-CUBEのindex.phpに渡す
    location / {
        try_files $uri /index.php$is_args$args;
    }

    # PHPの処理をPHP-FPMに渡す
    location ~ ^/index\.php(/|$) {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_split_path_info ^(.+\.php)(/.*)$;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        fastcgi_param DOCUMENT_ROOT $realpath_root;
        internal;
    }

    # .envなどのドットファイルへの直接アクセスを禁止
    location ~ /\.(?!well-known) {
        deny all;
    }

    # index.php以外のPHPファイルへの直接アクセスを禁止
    location ~ \.php$ {
        return 404;
    }

    error_log /var/log/nginx/eccube_error.log;
    access_log /var/log/nginx/eccube_access.log;
}
```

設定を有効化してNginxを再起動します。

```bash
# 設定を有効化する
sudo ln -s /etc/nginx/sites-available/eccube /etc/nginx/sites-enabled/

# 設定ファイルに問題がないか確認する
sudo nginx -t

# Nginxに設定を読み込ませる
sudo systemctl reload nginx
```

## SSL証明書の設定（HTTPS化）

Let's Encryptを使って無料のSSL証明書を取得し、HTTPS（暗号化通信）を有効にします。

:::message
実行前に、ドメインのDNS設定でこのVPSのIPアドレスが設定されていることを確認してください。DNS設定が反映されていないとSSL証明書の取得に失敗します。
:::

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

SSL証明書は90日で期限切れになりますが、自動更新の設定が正しく動くか確認しておきます。

```bash
sudo certbot renew --dry-run
```

エラーが出なければ自動更新は正常に動作しています。

## データベースの作成

EC-CUBEが使うデータベース（商品・注文などのデータを保存する場所）とMySQLのユーザーを作成します。

```bash
sudo mysql -u root
```

MySQLのプロンプトが表示されたら、以下のコマンドを順番に実行してください。

```sql
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eccube'@'localhost' IDENTIFIED BY '任意のパスワード';
GRANT ALL PRIVILEGES ON eccube.* TO 'eccube'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

作成する情報の意味は以下の通りです。

| 項目 | 意味 | 例 |
|---|---|---|
| データベース名 | データを保存する入れ物の名前。任意の名前でよい | `eccube` |
| ユーザー名 | EC-CUBEがMySQLに接続するためのアカウント名。OSのログインユーザーとは無関係 | `eccube` |
| パスワード | 上記ユーザーの接続用パスワード。推測されにくい強力な値を設定する | — |

:::message alert
作成したデータベース名・ユーザー名・パスワードは次のインストールウィザードで使います。必ず控えておいてください。
:::

## インストールウィザードの実行

ここまでの準備が整ったら、ブラウザからEC-CUBEをインストールします。

ブラウザで以下のURLを開いてください。

```
https://your-domain.com/install
```

画面の案内に従って設定を入力し、ウィザードを完了してください。データベース設定の画面では、上記で作成したデータベース名・ユーザー名・パスワードを入力します。

インストールが完了すると、データベースへの初期データ投入と `.env` ファイルの自動生成が行われます。

## インストール後の設定

### .env ファイルのアクセス権限を設定する

`.env` にはデータベースのパスワードなど機密情報が含まれています。他のユーザーに読まれないよう、所有者だけが読める権限に変更します。

```bash
chmod 600 /var/www/eccube/.env
```

本番環境（`APP_ENV=prod`）ではSymfonyが起動時に `.env` の内容を内部ファイルに展開するため、`600` に設定してもEC-CUBEは正常に動作します。

## 動作確認

以下のチェックリストをすべて確認してください。

- [ ] `https://your-domain.com` でEC-CUBEのトップページが表示される
- [ ] インストール時に設定した管理画面URLで管理画面にログインできる
- [ ] `.env` ファイルにブラウザから直接アクセスすると403エラーになる
- [ ] `http://` でアクセスすると `https://` に自動でリダイレクトされる
- [ ] 管理画面の「設定」→「システム設定」で `APP_DEBUG` が `0` になっている
