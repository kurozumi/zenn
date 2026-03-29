---
title: "【コピペで完成】さくらVPS + EC-CUBE 4.3 本番環境を2時間で構築するセキュリティ設定付き手順書"
emoji: "🛡️"
type: "tech"
topics: ["eccube", "eccube4", "vps", "ubuntu", "linux"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

**この記事の手順を進めれば、2時間でEC-CUBEが本番稼働します。**

セキュリティ設定なしでデプロイしたサーバーは、公開直後から攻撃を受けます。SSH総当たり攻撃、rootへの不正アクセス試行——VPSを立ち上げた瞬間から始まっています。

この記事では「とりあえず動いた」で終わらず、本番で安全に運用できる環境を一度で構築します。**コマンドはすべてコピペ可能です。**

**この記事を読み終えると、以下がすべて完成しています:**

- SSH鍵認証 + rootログイン禁止（パスワード攻撃を無力化）
- ufw + fail2ban（不正アクセスを自動ブロック）
- PHP 8.3 + Nginx + MySQL によるEC-CUBE 4.3動作環境
- Let's Encrypt SSL（無料HTTPS化）
- git pullベースのデプロイスクリプト（次回以降は1コマンドでデプロイ完了）

**動作環境:**

| 項目 | バージョン |
|---|---|
| OS | Ubuntu 24.04 LTS |
| PHP | 8.3 |
| Webサーバー | Nginx |
| データベース | MySQL 8.0 |
| EC-CUBE | 4.3 |

:::message alert
**この記事はVPS初期設定から本番デプロイまでの流れを解説したものです。** 本番運用にはバックアップ設定、監視設定、DBチューニングなど追加の設定が必要になる場合があります。
:::

## 1. さくらVPSの契約と初期設定

### 1-1. VPSの契約

[さくらのVPS](https://vps.sakura.ad.jp/) にアクセスして契約します。EC-CUBEの本番環境には **2GB以上のメモリ** を推奨します。

プランの目安：

| 月額 | メモリ | CPU | 推奨用途 |
|---|---|---|---|
| 643円〜 | 1GB | 1コア | 開発・テスト用 |
| 979円〜 | 2GB | 3コア | 小規模本番 |
| 1,979円〜 | 4GB | 4コア | 中規模本番 |

OSは **Ubuntu 24.04 LTS** を選択してください。

### 1-2. コントロールパネルにログイン

契約後、さくらインターネットの会員メニューからVPSコントロールパネルにアクセスします。サーバーのIPアドレスを確認しておきましょう。

### 1-3. 最初のSSH接続（rootで）

初回のみrootでログインします。

```bash
# ローカルマシンのターミナルで実行
ssh root@<サーバーのIPアドレス>
```

パスワードは契約時に設定したものを入力します。

## 2. セキュリティの初期設定

:::message alert
この章の設定は**必ず順番通りに**行ってください。SSH鍵の設定が完了する前にパスワード認証を無効にすると、サーバーに入れなくなります。万が一ロックアウトした場合はさくらVPSのコントロールパネルからVNCコンソールで復旧できます。
:::

### 2-1. システムを最新に更新する

```bash
apt update && apt upgrade -y
```

### 2-2. 一般ユーザーを作成する

rootで常時作業するのは危険です。一般ユーザーを作成してsudo権限を付与します。

```bash
# ユーザーを作成（例：eccube-admin）
adduser eccube-admin
```

`adduser` を実行すると対話式でパスワードの設定を求められます。

```
Enter new UNIX password:       ← パスワードを入力
Retype new UNIX password:      ← 確認用に再入力
passwd: password updated successfully
Full Name []:                  ← 空欄でEnterでOK
Room Number []:
Work Phone []:
Home Phone []:
Other []:
Is the information correct? [Y/n]: Y
```

```bash
# sudo権限を付与
usermod -aG sudo eccube-admin
```

作成したユーザーでログインできることを確認します（**ターミナルを新しく開いて試す**）。

```bash
# 別のターミナルで確認
ssh eccube-admin@<サーバーのIPアドレス>
sudo whoami  # rootと表示されればOK
```

### 2-3. SSH鍵認証を設定する

パスワード認証より安全なSSH鍵認証に切り替えます。

**ローカルマシンで鍵ペアを生成する:**

```bash
# ローカルのターミナルで実行
ssh-keygen -t ed25519 -C "eccube-vps"
# 保存先: ~/.ssh/id_ed25519（そのままEnter）
# パスフレーズ: 設定することを推奨
```

**公開鍵をサーバーにコピーする:**

```bash
# ローカルのターミナルで実行
ssh-copy-id -i ~/.ssh/id_ed25519.pub eccube-admin@<サーバーのIPアドレス>
```

**鍵でログインできることを確認する:**

```bash
ssh -i ~/.ssh/id_ed25519 eccube-admin@<サーバーのIPアドレス>
```

ログインできたら次のステップに進みます。

### 2-4. SSHの設定を強化する

サーバー上で以下を実行します。

```bash
sudo nano /etc/ssh/sshd_config
```

以下の項目を変更します（`#` がついている行はコメントを外す）。

```
# rootログインを禁止
PermitRootLogin no

# パスワード認証を無効化（鍵認証のみに）
PasswordAuthentication no

# 鍵認証を明示的に有効化
PubkeyAuthentication yes

# PAM経由のパスワード認証も無効化（Ubuntu 22.04以降）
KbdInteractiveAuthentication no

# 接続を許可するユーザーをホワイトリストで指定
AllowUsers eccube-admin
```

設定を反映します。

```bash
sudo systemctl restart sshd
```

**別のターミナルから新しい設定でログインできることを必ず確認してください。**

### 2-5. ファイアウォール（ufw）を設定する

必要なポートだけ開けて、それ以外はすべてブロックします。

```bash
# デフォルトで全拒否
sudo ufw default deny incoming
sudo ufw default allow outgoing

# SSH（22番）を許可
sudo ufw allow 22/tcp

# HTTP・HTTPSを許可
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# ufwを有効化
sudo ufw enable

# 設定確認
sudo ufw status verbose
```

:::message
MySQLのポート（3306番）は `deny incoming` のデフォルト設定により外部からブロックされています。`ufw allow 3306` は絶対に実行しないでください。また、MySQLがlocalhostのみをリッスンしていることを確認しましょう。

```bash
sudo ss -tlnp | grep 3306
# 127.0.0.1:3306 と表示されればOK
# 0.0.0.0:3306 が表示された場合は /etc/mysql/mysql.conf.d/mysqld.cnf の
# bind-address = 127.0.0.1 を確認してください
```
:::

### 2-6. fail2banで不正アクセスを防ぐ

fail2banは、繰り返しログイン失敗したIPアドレスを自動的にブロックするツールです。

```bash
sudo apt install fail2ban python3-systemd -y
```

設定ファイルを作成します（元のファイルは変更しない）。

```bash
sudo nano /etc/fail2ban/jail.local
```

以下を記述します。

```ini
[DEFAULT]
# 10分以内に5回失敗したら1時間ブロック
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
```

fail2banを起動します。

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 動作確認
sudo fail2ban-client status sshd
```

## 3. Webサーバー環境の構築

### 3-1. Nginxのインストール

```bash
sudo apt install nginx -y
sudo systemctl enable nginx
sudo systemctl start nginx
```

ブラウザで `http://<サーバーのIPアドレス>` にアクセスして「Welcome to nginx!」が表示されれば成功です。

### 3-2. PHPのインストール

EC-CUBE 4.3はPHP 8.1〜8.3をサポートしています。Ubuntu 24.04はPHP 8.3をデフォルトリポジトリに含んでいますが、最新のマイナーバージョンを利用するためにPPAを追加します。

```bash
# PPAリポジトリを追加（最新マイナーバージョンを利用する場合）
sudo apt install software-properties-common -y
sudo add-apt-repository ppa:ondrej/php -y
sudo apt update

# PHP 8.3と必要な拡張をインストール
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

### 3-3. MySQLのインストール

```bash
sudo apt install mysql-server -y
sudo systemctl enable mysql
sudo systemctl start mysql
```

セキュリティ設定を行います。

```bash
sudo mysql_secure_installation
```

対話式で以下を設定します。

- VALIDATE PASSWORD component: `Y`（パスワード強度チェックを有効化）
- Password strength: `2`（STRONG）
- Remove anonymous users: `Y`
- Disallow root login remotely: `Y`
- Remove test database: `Y`
- Reload privilege tables: `Y`

EC-CUBE用のデータベースとユーザーを作成します。

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
`GRANT ALL PRIVILEGES` は使わず、必要な権限のみを付与します。SQLインジェクション攻撃が発生した場合の被害を最小限に抑えるためです。
:::

### 3-4. Composerのインストール

セキュリティのためハッシュ検証付きでインストールします。

```bash
php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');"
php -r "if (hash_file('sha384', 'composer-setup.php') === file_get_contents('https://composer.github.io/installer.sig')) { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;"
php composer-setup.php
php -r "unlink('composer-setup.php');"
sudo mv composer.phar /usr/local/bin/composer
composer --version
```

## 4. EC-CUBEのデプロイ

### 4-1. ディレクトリの準備

```bash
sudo mkdir -p /var/www/eccube
sudo chown eccube-admin:www-data /var/www/eccube
sudo chmod 775 /var/www/eccube
```

### 4-2. EC-CUBEのインストール

```bash
cd /var/www/eccube

# GitHubからEC-CUBEを取得
git clone https://github.com/EC-CUBE/ec-cube.git .

# 本番環境では最新リリースタグを指定する（開発継続中のブランチより安定）
git checkout $(git tag -l "4.3.*" | sort -V | tail -1)

# 依存関係のインストール
composer install --no-dev --optimize-autoloader
```

### 4-3. 環境設定ファイルの作成

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
# 管理画面URLを変更してスキャン攻撃を防ぐ（推奨）
ECCUBE_ADMIN_ROUTE=your-secret-admin-path
```

:::message alert
`ECCUBE_AUTH_MAGIC` にはランダムな文字列を設定してください。以下のコマンドで生成できます。
```bash
openssl rand -base64 32
```

`ECCUBE_ADMIN_ROUTE` を変更すると管理画面URLが `/your-secret-admin-path` になります。デフォルトの `/admin` は攻撃ターゲットになりやすいため変更を推奨します。
:::

`.env` をWebから見えないよう保護します。

```bash
chmod 600 .env
chown eccube-admin:eccube-admin .env
```

:::message
本番環境では `.env` に機密情報を書くより `.env.local`（`.gitignore` 対象）に書くパターンも有効です。`.env.local` は `.env` より優先されます。
:::

### 4-4. パーミッションの設定

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

### 4-5. データベースのセットアップ

```bash
cd /var/www/eccube
php bin/console eccube:install --no-interaction
```

## 5. NginxのVhost設定

### 5-1. Nginx設定ファイルの作成

```bash
sudo nano /etc/nginx/sites-available/eccube
```

以下を記述します（`your-domain.com` を実際のドメインに変更）。

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

    # index.php以外のPHPファイルへの直接アクセスを禁止
    location ~ \.php$ {
        return 404;
    }

    error_log /var/log/nginx/eccube_error.log;
    access_log /var/log/nginx/eccube_access.log;
}
```

設定を有効化します。

```bash
sudo ln -s /etc/nginx/sites-available/eccube /etc/nginx/sites-enabled/
sudo nginx -t  # 設定ファイルのチェック
sudo systemctl reload nginx
```

## 6. SSL証明書の設定（Let's Encrypt）

無料のSSL証明書を設定します。ドメインが取得済みで、DNSがサーバーのIPアドレスに向いていることを確認してから実行してください。

```bash
sudo apt install certbot python3-certbot-nginx -y

sudo certbot --nginx -d your-domain.com
```

対話式でメールアドレス等を入力します。成功するとNginxの設定が自動でHTTPS対応に更新されます。

証明書の自動更新を確認します。

```bash
sudo certbot renew --dry-run
```

## 7. チームでの安全なデプロイフロー

### 基本的な流れ

```
ローカル: 開発 → git push → GitHub（PRレビュー）→ mainマージ
                                                        ↓
サーバー:                                          ./deploy.sh
```

### デプロイスクリプトの作成

```bash
nano /var/www/eccube/deploy.sh
```

```bash
#!/bin/bash
set -euo pipefail

echo "=== EC-CUBE デプロイ開始 ==="

APP_DIR="/var/www/eccube"
cd "$APP_DIR"

# 最新のコードを取得（マージコミットを作らない）
echo "コードを更新中..."
git fetch origin
git reset --hard origin/main

# 依存関係を更新
echo "依存関係を更新中..."
composer install --no-dev --optimize-autoloader

# キャッシュをクリア
echo "キャッシュをクリア中..."
php bin/console cache:clear --env=prod --no-debug

# varディレクトリのパーミッションを修正
chmod -R 775 "$APP_DIR/var"

echo "=== デプロイ完了！ ==="
```

実行権限を付与します。

```bash
chmod +x /var/www/eccube/deploy.sh
```

以降のデプロイは以下のコマンドだけで完了します。

```bash
cd /var/www/eccube && ./deploy.sh
```

### デプロイ時の注意点

:::message alert
**スキーマ変更（マイグレーション）がある場合は、別途手動での対応が必要です。**

```bash
# マイグレーション実行（スキーマ変更がある場合のみ）
php bin/console doctrine:migrations:migrate --env=prod
```

マイグレーション実行前にデータベースのバックアップを取ることを強く推奨します。
:::

## 8. 動作確認チェックリスト

デプロイ完了後、以下を確認してください。

- [ ] `https://your-domain.com` でEC-CUBEのトップページが表示される
- [ ] `https://your-domain.com/<ECCUBE_ADMIN_ROUTE>` で管理画面にログインできる
- [ ] `.env` ファイルにブラウザからアクセスできない（403が返る）
- [ ] HTTP（80番）にアクセスするとHTTPS（443番）にリダイレクトされる
- [ ] `APP_DEBUG=0` になっていることを確認（`.env` を確認）
- [ ] `sudo ufw status` でファイアウォールが有効になっている
- [ ] `sudo fail2ban-client status sshd` でfail2banが動作している
- [ ] rootユーザーでSSHログインできないことを確認

## まとめ

この記事で行ったセキュリティ設定をまとめます。

| 設定 | 目的 |
|---|---|
| 一般ユーザー作成 | root権限の常時使用を避ける |
| SSH鍵認証 + `AllowUsers` | パスワード攻撃・不正ユーザーのログインを防ぐ |
| rootログイン禁止 | rootへの直接攻撃を防ぐ |
| パスワード認証・KbdInteractive無効 | 総当たり攻撃を防ぐ |
| ufw | 不要なポートへのアクセスをブロック |
| fail2ban | 繰り返し失敗するIPを自動ブロック |
| MySQLの最小権限 | SQLインジェクション時の被害を最小化 |
| Let's Encrypt | 通信の暗号化 |
| Nginxセキュリティヘッダー | クリックジャッキング・MIMEスニッフィング対策 |
| 管理画面URLの変更 | スキャン攻撃のターゲットになりにくくする |

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
