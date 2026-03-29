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
```

:::message
`git checkout 4.3` ではなく最新リリースタグを指定します。`4.3` ブランチは開発が継続されているため、予期しない変更が含まれる場合があります。
:::

## 環境設定ファイルの作成

```bash
cp .env.dist .env
nano .env
```

以下の項目を設定します。

```bash
APP_ENV=prod
APP_DEBUG=0
DATABASE_URL=mysql://eccube_user:your-strong-password@127.0.0.1:3306/eccube
DATABASE_SERVER_VERSION=8.0
ECCUBE_AUTH_MAGIC=your-random-32-char-string
# 管理画面URLを変更してスキャン攻撃を防ぐ
ECCUBE_ADMIN_ROUTE=your-secret-admin-path
```

:::message alert
**`ECCUBE_AUTH_MAGIC`** にはランダムな文字列を設定してください。

```bash
openssl rand -base64 32
```

**`ECCUBE_ADMIN_ROUTE`** を変更すると管理画面URLが `/your-secret-admin-path` になります。デフォルトの `/admin` は攻撃ターゲットになりやすいため変更を推奨します。
:::

### .envのアクセス権限を設定する

```bash
chmod 600 .env
chown eccube-admin:eccube-admin .env
```

:::message
本番環境では `.env` に機密情報を書くより `.env.local`（`.gitignore` 対象）に書くパターンも有効です。`.env.local` は `.env` より優先されます。
:::

## パーミッションの設定

EC-CUBEはWebサーバー（`www-data`）がいくつかのディレクトリに書き込む必要があります。

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

## データベースのセットアップ

```bash
cd /var/www/eccube
php bin/console eccube:install --no-interaction
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
    add_header X-XSS-Protection "1; mode=block" always;
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

## 動作確認

- [ ] `https://your-domain.com` でEC-CUBEのトップページが表示される
- [ ] `https://your-domain.com/<ECCUBE_ADMIN_ROUTE>` で管理画面にログインできる
- [ ] `.env` ファイルにブラウザからアクセスできない（403が返る）
- [ ] HTTP（80番）にアクセスするとHTTPS（443番）にリダイレクトされる
- [ ] `APP_DEBUG=0` になっていることを確認
