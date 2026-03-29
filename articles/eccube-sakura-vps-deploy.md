---
title: "【コピペで完成】さくらVPS + EC-CUBE 4.3 本番環境を2時間で構築するセキュリティ設定付き手順書"
emoji: "🛡️"
type: "tech"
topics: ["eccube", "eccube4", "vps", "ubuntu", "claudecode"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

**この記事の手順を進めれば、2時間でEC-CUBEが本番稼働します。**

セキュリティ設定なしでデプロイしたサーバーは、公開直後から攻撃を受けます。SSH総当たり攻撃、rootへの不正アクセス試行——VPSを立ち上げた瞬間から始まっています。

この記事では Claude Code の**カスタムスキル**を使い、複雑なVPS初期設定からEC-CUBEのデプロイまでを `/setup-eccube-vps` の**1コマンドで自動化**します。

**このスキルが自動化すること:**

- SSH鍵認証 + rootログイン禁止（パスワード攻撃を無力化）
- ufw + fail2ban（不正アクセスを自動ブロック）
- PHP 8.3 + Nginx + MySQL によるEC-CUBE 4.3動作環境
- Let's Encrypt SSL（無料HTTPS化）
- git resetベースのデプロイスクリプト設置

**動作環境:**

| 項目 | バージョン |
|---|---|
| OS | Ubuntu 24.04 LTS |
| PHP | 8.3 |
| Webサーバー | Nginx |
| データベース | MySQL 8.0 |
| EC-CUBE | 4.3 |

## 事前準備（ローカルマシンで実施）

スキルを実行する前に、ローカルマシンで以下を完了させてください。

### 1. さくらVPSの契約

[さくらのVPS](https://vps.sakura.ad.jp/) で **Ubuntu 24.04 LTS** を選択して契約します。EC-CUBEの本番環境には **2GB以上のメモリ** を推奨します。

| 月額 | メモリ | CPU | 推奨用途 |
|---|---|---|---|
| 643円〜 | 1GB | 1コア | 開発・テスト用 |
| 979円〜 | 2GB | 3コア | 小規模本番 |
| 1,979円〜 | 4GB | 4コア | 中規模本番 |

### 2. SSH鍵ペアの生成

```bash
# ローカルのターミナルで実行
ssh-keygen -t ed25519 -C "eccube-vps"
# 保存先: ~/.ssh/id_ed25519（そのままEnter）
# パスフレーズ: 設定することを推奨
```

### 3. rootでVPSに接続

```bash
ssh root@<サーバーのIPアドレス>
```

接続できたらスキルを実行する準備完了です。

## Claude Codeデプロイスキルの作成

### スキルファイルの作成

ローカルマシンで以下のディレクトリとファイルを作成します。

```bash
mkdir -p ~/.claude/skills/setup-eccube-vps
```

`~/.claude/skills/setup-eccube-vps/SKILL.md` を以下の内容で作成します。

````markdown
---
name: setup-eccube-vps
description: さくらVPS（Ubuntu 24.04）にEC-CUBE 4.3をセキュアにセットアップする
disable-model-invocation: true
allowed-tools: Bash(ssh *), Bash(ssh-copy-id *)
---

# EC-CUBE VPS セットアップスキル

さくらVPS（Ubuntu 24.04）にEC-CUBE 4.3をセットアップします。
実行前に root で VPS に SSH 接続済みであることを確認してください。

## Step 0: セットアップ情報の確認

ユーザーに以下の情報を確認してください。

- **VPSのIPアドレス** (例: 192.0.2.1)
- **作成するユーザー名** (例: eccube-admin)
- **ドメイン名** (例: shop.example.com)
- **DBパスワード** (強力なパスワードを設定すること)
- **管理画面パス** (例: my-secret-admin ← デフォルトの /admin から変更)

すべての情報が揃ったら以下を実行してください。

---

## Step 1: システムの更新

```bash
ssh root@${VPS_IP} "apt update && apt upgrade -y"
```

## Step 2: 一般ユーザーの作成

```bash
ssh root@${VPS_IP} "
  # ユーザー作成（パスワードなし・鍵認証専用）
  adduser --disabled-password --gecos '' ${USERNAME}
  usermod -aG sudo ${USERNAME}
  echo '${USERNAME} ALL=(ALL) NOPASSWD: /usr/bin/composer, /var/www/eccube/deploy.sh' >> /etc/sudoers.d/eccube
"
```

## Step 3: SSH公開鍵をサーバーにコピー

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub ${USERNAME}@${VPS_IP}
```

コピー後、鍵でログインできることを確認します。

```bash
ssh -i ~/.ssh/id_ed25519 ${USERNAME}@${VPS_IP} "echo 'SSH key login OK'"
```

## Step 4: SSHの設定強化

```bash
ssh root@${VPS_IP} "
  sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
  sed -i 's/#PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
  sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
  echo 'PubkeyAuthentication yes' >> /etc/ssh/sshd_config
  echo 'KbdInteractiveAuthentication no' >> /etc/ssh/sshd_config
  echo 'AllowUsers ${USERNAME}' >> /etc/ssh/sshd_config
  systemctl restart sshd
"
```

## Step 5: ファイアウォール設定

```bash
ssh root@${VPS_IP} "
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 22/tcp
  ufw allow 80/tcp
  ufw allow 443/tcp
  ufw --force enable
"
```

## Step 6: fail2banのインストール

```bash
ssh root@${VPS_IP} "
  apt install fail2ban python3-systemd -y
  cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
backend  = systemd

[sshd]
enabled = true
port    = ssh
EOF
  systemctl enable fail2ban
  systemctl start fail2ban
"
```

## Step 7: PHP 8.3 + Nginx + MySQLのインストール

```bash
ssh root@${VPS_IP} "
  # Nginx
  apt install nginx -y
  systemctl enable nginx

  # PHP 8.3
  apt install software-properties-common -y
  add-apt-repository ppa:ondrej/php -y
  apt update
  apt install php8.3 php8.3-fpm php8.3-cli \
    php8.3-mysql php8.3-mbstring \
    php8.3-xml php8.3-zip php8.3-curl php8.3-gd \
    php8.3-intl php8.3-sodium php8.3-bcmath -y

  # MySQL
  apt install mysql-server -y
  systemctl enable mysql
"
```

## Step 8: MySQLのセットアップ

```bash
ssh root@${VPS_IP} "
  mysql -u root << 'EOF'
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eccube_user'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER,
      CREATE TEMPORARY TABLES, LOCK TABLES
      ON eccube.* TO 'eccube_user'@'localhost';
FLUSH PRIVILEGES;
EOF
"
```

## Step 9: Composerのインストール

```bash
ssh root@${VPS_IP} "
  php -r \"copy('https://getcomposer.org/installer', 'composer-setup.php');\"
  php -r \"if (hash_file('sha384', 'composer-setup.php') === file_get_contents('https://composer.github.io/installer.sig')) { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;\"
  php composer-setup.php
  php -r \"unlink('composer-setup.php');\"
  mv composer.phar /usr/local/bin/composer
"
```

## Step 10: EC-CUBEのデプロイ

```bash
ssh root@${VPS_IP} "
  mkdir -p /var/www/eccube
  chown ${USERNAME}:www-data /var/www/eccube
  chmod 775 /var/www/eccube
"

ssh ${USERNAME}@${VPS_IP} "
  cd /var/www/eccube
  git clone https://github.com/EC-CUBE/ec-cube.git .
  git checkout \$(git tag -l '4.3.*' | sort -V | tail -1)
  composer install --no-dev --optimize-autoloader

  # .envの設定
  cp .env.dist .env
  sed -i 's/APP_ENV=.*/APP_ENV=prod/' .env
  sed -i 's/APP_DEBUG=.*/APP_DEBUG=0/' .env
  sed -i 's|DATABASE_URL=.*|DATABASE_URL=mysql://eccube_user:${DB_PASSWORD}@127.0.0.1:3306/eccube|' .env
  sed -i 's/DATABASE_SERVER_VERSION=.*/DATABASE_SERVER_VERSION=8.0/' .env
  AUTH_MAGIC=\$(openssl rand -base64 32)
  echo \"ECCUBE_AUTH_MAGIC=\${AUTH_MAGIC}\" >> .env
  echo 'ECCUBE_ADMIN_ROUTE=${ADMIN_ROUTE}' >> .env
  chmod 600 .env
  chown \${USER}:\${USER} .env
"
```

## Step 11: パーミッションの設定とEC-CUBEインストール

```bash
ssh root@${VPS_IP} "
  chown -R ${USERNAME}:www-data /var/www/eccube
  find /var/www/eccube -type d -exec chmod 755 {} \;
  find /var/www/eccube -type f -exec chmod 644 {} \;
  chmod -R 775 /var/www/eccube/var
  chmod -R 775 /var/www/eccube/html
  chmod -R 775 /var/www/eccube/app/Plugin
  chmod -R 775 /var/www/eccube/app/PluginData
  chmod -R 775 /var/www/eccube/app/proxy
  chmod -R 775 /var/www/eccube/app/template
  chmod -R 775 /var/www/eccube/vendor
  chmod 664 /var/www/eccube/composer.json
  chmod 664 /var/www/eccube/composer.lock
"

ssh ${USERNAME}@${VPS_IP} "
  cd /var/www/eccube
  php bin/console eccube:install --no-interaction
"
```

## Step 12: Nginxの設定

```bash
ssh root@${VPS_IP} "
cat > /etc/nginx/sites-available/eccube << 'NGINX'
server {
    listen 80;
    server_name ${DOMAIN};
    root /var/www/eccube/html;
    index index.php;

    client_max_body_size 32M;

    add_header X-Frame-Options 'SAMEORIGIN' always;
    add_header X-Content-Type-Options 'nosniff' always;
    add_header X-XSS-Protection '1; mode=block' always;
    add_header Referrer-Policy 'strict-origin-when-cross-origin' always;

    location / {
        try_files \$uri /index.php\$is_args\$args;
    }

    location ~ ^/index\.php(/|$) {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_split_path_info ^(.+\.php)(/.*)$;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME \$realpath_root\$fastcgi_script_name;
        fastcgi_param DOCUMENT_ROOT \$realpath_root;
        internal;
    }

    location ~ /\.(?!well-known) {
        deny all;
    }

    location ~ \.php$ {
        return 404;
    }

    error_log /var/log/nginx/eccube_error.log;
    access_log /var/log/nginx/eccube_access.log;
}
NGINX
  ln -sf /etc/nginx/sites-available/eccube /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
"
```

## Step 13: SSL証明書の取得

ドメインのDNSがVPSのIPアドレスに向いていることを確認してから実行してください。

```bash
ssh root@${VPS_IP} "
  apt install certbot python3-certbot-nginx -y
  certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@${DOMAIN}
"
```

## Step 14: デプロイスクリプトの設置

```bash
ssh root@${VPS_IP} "
cat > /var/www/eccube/deploy.sh << 'DEPLOY'
#!/bin/bash
set -euo pipefail
APP_DIR='/var/www/eccube'
cd \"\$APP_DIR\"
echo '=== デプロイ開始 ==='
git fetch origin
git reset --hard origin/main
composer install --no-dev --optimize-autoloader
php bin/console cache:clear --env=prod --no-debug
chmod -R 775 \"\$APP_DIR/var\"
echo '=== デプロイ完了！ ==='
DEPLOY
  chmod +x /var/www/eccube/deploy.sh
  chown ${USERNAME}:www-data /var/www/eccube/deploy.sh
"
```

## Step 15: 完了確認

```bash
ssh ${USERNAME}@${VPS_IP} "
  echo '=== セットアップ完了確認 ==='
  sudo ufw status
  sudo fail2ban-client status sshd
  php -v
  nginx -v
  mysql --version
  echo ''
  echo '=== EC-CUBE動作確認 ==='
  curl -s -o /dev/null -w '%{http_code}' http://${DOMAIN}/
"
```

すべて完了したら以下のURLにアクセスして動作を確認してください。

- ショップ: https://${DOMAIN}/
- 管理画面: https://${DOMAIN}/${ADMIN_ROUTE}/
````

## スキルの使い方

スキルを作成したら、VPSにrootでSSH接続した状態でClaude Codeを開き、以下を実行します。

```
/setup-eccube-vps
```

Claude Codeが以下を確認してから自動で実行します。

1. VPSのIPアドレス・ユーザー名・ドメイン・DBパスワード・管理画面パスを確認
2. システム更新
3. ユーザー作成 + SSH鍵認証設定
4. ufw + fail2ban設定
5. PHP 8.3 + Nginx + MySQL インストール
6. EC-CUBE 4.3 デプロイ
7. Nginx + SSL設定
8. デプロイスクリプト設置
9. 動作確認

## 次回以降のデプロイ

初回セットアップ後は、サーバー上でデプロイスクリプトを実行するだけです。

```bash
ssh eccube-admin@<サーバーのIPアドレス>
cd /var/www/eccube && ./deploy.sh
```

:::message alert
**スキーマ変更（マイグレーション）がある場合は、別途手動での対応が必要です。**

```bash
php bin/console doctrine:migrations:migrate --env=prod
```

マイグレーション実行前にデータベースのバックアップを取ることを強く推奨します。
:::

## このスキルの限界

- **インタラクティブなコマンドは自動化できない**: `mysql_secure_installation` 等は手動対応が必要
- **DNS設定は手動**: Let's EncryptはDNSがVPSに向いていないと失敗します
- **完全な本番運用にはさらに設定が必要**: バックアップ、監視、DBチューニング等

## まとめ

Claude Codeのカスタムスキルを使うことで、複雑なVPS初期設定からEC-CUBEのデプロイまでを `/setup-eccube-vps` の1コマンドで自動化できます。

| 従来の方法 | スキルを使った場合 |
|---|---|
| 手順書を見ながら1コマンドずつ実行 | 1コマンドで全自動 |
| 手順の抜け漏れが起きやすい | 毎回同じ手順で確実に実行 |
| チームメンバーによって手順がバラバラ | SKILL.mdを共有して標準化 |

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
