---
title: "Webサーバー環境の構築"
---

## この章で構築するもの

EC-CUBEを動かすために以下をインストールします。

```
クライアント
    ↓ HTTPS
Nginx（Webサーバー）
    ↓ FastCGI
PHP 8.3-FPM（PHPアプリケーション）
    ↓ PDO
MySQL 8.0（データベース）
```

## Nginxのインストール

```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

ブラウザで `http://<サーバーのIPアドレス>` にアクセスして「Welcome to nginx!」が表示されれば成功です。

## PHP 8.3のインストール

EC-CUBE 4.3はPHP 8.1〜8.3をサポートしています。Ubuntu 24.04はPHP 8.3をデフォルトリポジトリに含んでいますが、最新のマイナーバージョンを利用するためにPPAを追加します。

```bash
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update

sudo apt install php8.3 php8.3-fpm php8.3-cli \
    php8.3-mysql php8.3-mbstring \
    php8.3-xml php8.3-zip php8.3-curl php8.3-gd \
    php8.3-intl php8.3-sodium php8.3-bcmath -y
```

インストール確認します。

```bash
php -v
# PHP 8.3.x と表示されればOK
```

### PHP-FPMの設定チューニング

本番環境向けに PHP-FPM のプロセス数を調整します。

```bash
sudo nano /etc/php/8.3/fpm/pool.d/www.conf
```

以下の項目を環境に合わせて変更します（2GBメモリの場合の目安）。

```ini
pm = dynamic
pm.max_children = 10
pm.start_servers = 3
pm.min_spare_servers = 2
pm.max_spare_servers = 5
```

```bash
sudo systemctl restart php8.3-fpm
```

## MySQLのインストール

```bash
sudo apt install mysql-server -y
sudo systemctl enable mysql
sudo systemctl start mysql
```

### セキュリティ設定

```bash
sudo mysql_secure_installation
```

対話式で以下を設定します。

- VALIDATE PASSWORD component: `Y`
- Password strength: `2`（STRONG）
- Remove anonymous users: `Y`
- Disallow root login remotely: `Y`
- Remove test database: `Y`
- Reload privilege tables: `Y`

### EC-CUBE用データベースとユーザーの作成

:::message
Ubuntu 24.04のMySQL 8.0はデフォルトで `auth_socket` 認証を使用します。そのため `root` はパスワードなしでログインできます。
:::

```bash
sudo mysql
```

```sql
-- データベースを作成
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- 専用ユーザーを作成（パスワードは必ず変更すること）
CREATE USER 'eccube_user'@'localhost' IDENTIFIED BY 'your-strong-password';

-- 必要最小限の権限のみ付与
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER,
      CREATE TEMPORARY TABLES, LOCK TABLES
      ON eccube.* TO 'eccube_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

:::message alert
`GRANT ALL PRIVILEGES` は使わず必要な権限のみを付与します。SQLインジェクション攻撃が発生した場合の被害を最小限に抑えるためです。
:::

## Composerのインストール

セキュリティのためハッシュ検証付きでインストールします。

```bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php -r "if (hash_file('sha384', 'composer-setup.php') === file_get_contents('https://composer.github.io/installer.sig')) { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;"
php composer-setup.php
php -r "unlink('composer-setup.php');"
sudo mv composer.phar /usr/local/bin/composer
composer --version
```

## 環境確認

この章が完了したら以下を確認してください。

```bash
php -v          # PHP 8.3.x
nginx -v        # nginx/1.x.x
mysql --version # mysql  Ver 8.x.x
composer -V     # Composer version 2.x.x
```
