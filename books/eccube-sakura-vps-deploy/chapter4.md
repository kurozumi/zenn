---
title: "EC-CUBEのデプロイ"
---

## ディレクトリの準備

```bash
sudo mkdir -p /var/www/eccube
sudo chown eccube-admin:www-data /var/www/eccube
sudo chmod 775 /var/www/eccube
```

## EC-CUBEのインストール

```bash
cd /var/www/eccube

git clone https://github.com/EC-CUBE/ec-cube.git .

# 本番環境では最新リリースタグを指定する（開発継続中のブランチより安定）
git checkout $(git tag -l "4.3.*" | sort -V | tail -1)

composer install --no-dev --optimize-autoloader

# .envを削除してGUIインストーラーを有効化する
rm -f .env
```

:::message
`git checkout 4.3` ではなく最新リリースタグを指定します。`4.3` ブランチは開発が継続されているため、予期しない変更が含まれる場合があります。
:::

## パーミッションの設定

### www-data とは

`www-data` は Nginx や PHP-FPM が動作する際に使うシステムユーザーです。ブラウザからのリクエストは最終的にこのユーザーとして処理されます。

```
ブラウザ → Nginx（www-dataで動作）→ PHP-FPM（www-dataで動作）→ EC-CUBEのファイル
```

EC-CUBE が画像のアップロードやキャッシュの生成でファイルを書き込む際も、この `www-data` ユーザーが実際に書き込みます。そのため、書き込みが必要なディレクトリには `www-data` の権限を付与する必要があります。

### 権限を設定する

```bash
sudo chown -R eccube-admin:www-data /var/www/eccube

# ディレクトリは755、ファイルは644を基本に設定
sudo find /var/www/eccube -type d -exec chmod 755 {} \;
sudo find /var/www/eccube -type f -exec chmod 644 {} \;

# Webサーバーが書き込む必要があるディレクトリを緩める
sudo chmod -R 775 /var/www/eccube/var
sudo chmod -R 775 /var/www/eccube/html
sudo chmod -R 775 /var/www/eccube/app/Plugin
sudo chmod -R 775 /var/www/eccube/app/PluginData
sudo chmod -R 775 /var/www/eccube/app/proxy
sudo chmod -R 775 /var/www/eccube/app/template
# プラグインインストール時に必要
sudo chmod -R 775 /var/www/eccube/vendor
sudo chmod 664 /var/www/eccube/composer.json
sudo chmod 664 /var/www/eccube/composer.lock
```

## Nginxの設定

```bash
sudo nano /etc/nginx/sites-available/eccube
```

```nginx
server {
    listen 80;
    server_name your-domain.com;
    root /var/www/eccube/html;
    index index.php;

    client_max_body_size 32M;

    # セキュリティヘッダー
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    location / {
        try_files $uri /index.php$is_args$args;
    }

    location ~ ^/index\.php(/|$) {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_split_path_info ^(.+\.php)(/.*)$;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        fastcgi_param DOCUMENT_ROOT $realpath_root;
        internal;
    }

    # ドットファイル全般をブロック（.well-knownはLet's Encrypt用に除外）
    location ~ /\.(?!well-known) {
        deny all;
    }

    location ~ \.php$ {
        return 404;
    }

    error_log /var/log/nginx/eccube_error.log;
    access_log /var/log/nginx/eccube_access.log;
}
```

```bash
sudo ln -s /etc/nginx/sites-available/eccube /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL証明書の設定（Let's Encrypt）

ドメインのDNSがVPSのIPアドレスに向いていることを確認してから実行してください。

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d your-domain.com
```

証明書の自動更新を確認します。

```bash
sudo certbot renew --dry-run
```

## データベースの作成

MySQLにrootでログインしてデータベースとユーザーを作成します。

```bash
sudo mysql -u root
```

MySQLプロンプトで以下を実行してください（パスワードは任意の強力な値を設定してください）。

```sql
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eccube'@'localhost' IDENTIFIED BY '任意のパスワード';
GRANT ALL PRIVILEGES ON eccube.* TO 'eccube'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

ここで作成する情報は次の通りです。

| 項目 | 説明 | 例 |
|---|---|---|
| データベース名 | EC-CUBEのデータを保存する入れ物の名前。任意の名前でよい | `eccube` |
| ユーザー名 | EC-CUBEがMySQLに接続するときに使うアカウント名。OSのログインユーザーとは別物 | `eccube` |
| パスワード | 上記ユーザーの認証用パスワード。推測されにくい強力な値を設定する | - |

作成したDB名・ユーザー名・パスワードはインストールウィザードで入力するので控えておいてください。

## インストールウィザードの実行

ブラウザで `https://your-domain.com/install` を開き、インストールウィザードを完了してください。データベース設定では上記で作成したDB名・ユーザー名・パスワードを入力してください。

インストールが完了すると `.env` が自動生成され、データベースの初期化（テーブル作成・初期データ投入）も自動で行われます。

## インストール後の設定

### .envのアクセス権限を設定する

`.env` にはDBパスワードなどの機密情報が含まれるため、所有者だけが読めるように制限します。

```bash
chmod 600 .env
```

本番環境（`APP_ENV=prod`）では Symfony がキャッシュ生成時に `.env` の値を内部ファイルに展開するため、`600` にしても PHP-FPM は正常に動作します。

:::message
本番環境では `.env` に機密情報を書くより `.env.local`（`.gitignore` 対象）に書くパターンも有効です。`.env.local` は `.env` より優先されます。
:::

## 動作確認

- [ ] `https://your-domain.com` でEC-CUBEのトップページが表示される
- [ ] `https://your-domain.com/<ECCUBE_ADMIN_ROUTE>` で管理画面にログインできる
- [ ] `.env` ファイルにブラウザからアクセスできない（403が返る）
- [ ] HTTP（80番）にアクセスするとHTTPS（443番）にリダイレクトされる
- [ ] `APP_DEBUG=0` になっていることを確認
