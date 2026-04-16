---
title: "Claude Codeスキルで1コマンド自動化"
---

## スキルを使う利点

前章までの手順を手動で実行すると、1〜2時間かかります。Claude Codeのカスタムスキルを使えば `/setup-eccube-vps` の1コマンドで同じ手順を自動実行できます。

| 手動 | スキル使用 |
|---|---|
| 手順書を見ながら1コマンドずつ実行 | 1コマンドで全自動 |
| 手順の抜け漏れが起きやすい | 毎回同じ手順で確実に実行 |
| 2回目のサーバー構築も同じ手間 | SKILL.mdを使い回せる |

## スキルファイルの作成

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

## Step 0: セットアップ情報の確認

ユーザーに以下の情報を確認してください。確認できたら、後続のステップで使う変数として記憶してください。

**DBパスワード・管理画面URLなどの機密情報はここで聞きません。** 次の Step 0-2 でユーザーが直接サーバーに設定します。

| 変数名 | 説明 | 例 |
|---|---|---|
| `VPS_IP` | VPSのIPアドレス | `192.0.2.1` |
| `USERNAME` | 作成するユーザー名 | `eccube-admin` |
| `DOMAIN` | ドメイン名 | `shop.example.com` |

確認後、以下のコマンドで変数をセットしてから各ステップを実行してください。

```bash
export VPS_IP="確認したIPアドレス"
export USERNAME="eccube-admin"
export DOMAIN="shop.example.com"
```

---

## Step 0-2: シークレットファイルの作成（手動・必須）

**このステップはClaude Codeを介さず、ユーザーが直接ターミナルでSSHして実行してください。**

DBパスワードや管理画面URLなどの機密情報をClaude Codeのコンテキストに渡さないよう、サーバー上のプロジェクト外に保管します。

```bash
# ユーザーがターミナルで直接実行
ssh root@YOUR_VPS_IP "
  mkdir -p /etc/eccube
  cat > /etc/eccube/secrets.env << 'EOF'
DB_PASSWORD=ここに強力なパスワードを設定（英大小文字・数字・記号を含む16文字以上推奨）
EOF
  chmod 600 /etc/eccube/secrets.env
"
```

> **管理画面のURLパスやログイン情報はGUIインストーラー（Step 11）で設定します。**

シークレットファイルの作成が完了したら、Claude Codeに「Step 1から実行して」と伝えてください。

---

## Step 1: システムの更新

```bash
ssh root@${VPS_IP} "apt update && apt upgrade -y"
```

## Step 2: 一般ユーザーの作成

```bash
ssh root@${VPS_IP} "
  adduser --disabled-password --gecos '' ${USERNAME}
  usermod -aG sudo ${USERNAME}
"
```

## Step 3: SSH公開鍵をサーバーにコピー

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub ${USERNAME}@${VPS_IP}
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
  systemctl enable fail2ban && systemctl start fail2ban
"
```

## Step 7: PHP 8.3 + Nginx + MySQLのインストール

```bash
ssh root@${VPS_IP} "
  apt install nginx -y && systemctl enable nginx
  apt install software-properties-common -y
  add-apt-repository ppa:ondrej/php -y && apt update
  apt install php8.3 php8.3-fpm php8.3-cli \
    php8.3-mysql php8.3-mbstring php8.3-xml php8.3-zip \
    php8.3-curl php8.3-gd php8.3-intl php8.3-sodium php8.3-bcmath -y
  apt install mysql-server -y && systemctl enable mysql
"
```

## Step 8: MySQLのセットアップ

シークレットファイルを読み込んでDBを作成します。パスワードはサーバー上でのみ展開されます。

```bash
ssh root@${VPS_IP} bash << 'ENDSSH'
source /etc/eccube/secrets.env
mysql -u root << EOF
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eccube_user'@'localhost' IDENTIFIED BY "${DB_PASSWORD}";
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER,
      CREATE TEMPORARY TABLES, LOCK TABLES
      ON eccube.* TO 'eccube_user'@'localhost';
FLUSH PRIVILEGES;
EOF
ENDSSH
```

## Step 8-2: MySQL認証情報ファイルの設定

バックアップコマンドをパスワードなしで実行できるよう、`~/.my.cnf` を設定します。
rootで実行し、シークレットファイルを読み込んで一般ユーザーのホームに配置します。

```bash
ssh root@${VPS_IP} bash << ENDSSH
source /etc/eccube/secrets.env
cat > /home/${USERNAME}/.my.cnf << EOF
[client]
user=eccube_user
password=\${DB_PASSWORD}
EOF
chown ${USERNAME}:${USERNAME} /home/${USERNAME}/.my.cnf
chmod 600 /home/${USERNAME}/.my.cnf
ENDSSH
```

## Step 9: Composerのインストール

```bash
ssh root@${VPS_IP} "
  php -r \"copy('https://getcomposer.org/installer', 'composer-setup.php');\"
  php -r \"if (hash_file('sha384', 'composer-setup.php') === file_get_contents('https://composer.github.io/installer.sig')) { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;\"
  php composer-setup.php && php -r \"unlink('composer-setup.php');\"
  mv composer.phar /usr/local/bin/composer
"
```

## Step 10: EC-CUBEパッケージのダウンロードと展開

GitHubリリースから最新の4.3.x パッケージを取得してサーバーに展開します。

```bash
ssh root@${VPS_IP} bash << ENDSSH
apt install unzip -y
ECCUBE_VERSION=\$(curl -s 'https://api.github.com/repos/EC-CUBE/ec-cube/releases' \
  | grep -o '"tag_name":"4\\.3\\.[^"]*"' | head -1 | cut -d'"' -f4)
mkdir -p /var/www/eccube
curl -L "https://github.com/EC-CUBE/ec-cube/releases/download/\${ECCUBE_VERSION}/eccube-\${ECCUBE_VERSION}.zip" \
  -o /tmp/eccube.zip
unzip -q /tmp/eccube.zip -d /tmp/eccube-extract
mv /tmp/eccube-extract/eccube-\${ECCUBE_VERSION}/* /var/www/eccube/
rm -rf /tmp/eccube.zip /tmp/eccube-extract
chown -R ${USERNAME}:www-data /var/www/eccube
ENDSSH
```

## Step 11: パーミッション設定とGUIインストール

パーミッションを設定した後、ユーザーがブラウザでインストールウィザードを完了します。

```bash
ssh root@${VPS_IP} "
  chown -R ${USERNAME}:www-data /var/www/eccube
  find /var/www/eccube -type d -exec chmod 755 {} \;
  find /var/www/eccube -type f -exec chmod 644 {} \;
  chmod -R 775 /var/www/eccube/var /var/www/eccube/html \
    /var/www/eccube/app/Plugin /var/www/eccube/app/PluginData \
    /var/www/eccube/app/proxy /var/www/eccube/app/template
"
```

コマンドが完了したら、ユーザーに以下を伝えてください：

**「ブラウザで `https://${DOMAIN}/install.php` を開き、インストールウィザードを完了してください。**
**完了したら「Step 11-2 を実行して」と教えてください。」**

インストールウィザードの入力項目：

| ステップ | 入力項目 |
|---|---|
| サイト設定 | 店名・メールアドレス・管理画面ログインID・パスワード・管理画面ディレクトリ名 |
| データベース設定 | 種類（MySQL）・ホスト（localhost）・DB名（eccube）・ユーザー名（eccube_user）・パスワード |

## Step 11-2: GUIインストール後の機密情報をシークレットファイルに移動

GUIインストーラーが生成した `.env` から機密情報を取り出し、シークレットファイルと PHP-FPM 設定に移動します。

```bash
ssh root@${VPS_IP} bash << ENDSSH
source /etc/eccube/secrets.env

# GUIインストーラーが.envに書き込んだ値を取得
DATABASE_URL=\$(grep '^DATABASE_URL=' /var/www/eccube/.env | cut -d= -f2-)
AUTH_MAGIC=\$(grep '^ECCUBE_AUTH_MAGIC=' /var/www/eccube/.env | cut -d= -f2-)
ADMIN_ROUTE=\$(grep '^ECCUBE_ADMIN_ROUTE=' /var/www/eccube/.env | cut -d= -f2-)

# シークレットファイルに追記
echo "DATABASE_URL=\${DATABASE_URL}" >> /etc/eccube/secrets.env
echo "ECCUBE_AUTH_MAGIC=\${AUTH_MAGIC}" >> /etc/eccube/secrets.env

# deployスクリプト（${USERNAME}実行）がシークレットファイルを読めるよう権限を設定
chown root:${USERNAME} /etc/eccube/secrets.env
chmod 640 /etc/eccube/secrets.env

# PHP-FPMプールにWebリクエスト用の環境変数を追加
cat >> /etc/php/8.3/fpm/pool.d/www.conf << EOF

env[DATABASE_URL] = \${DATABASE_URL}
env[ECCUBE_AUTH_MAGIC] = \${AUTH_MAGIC}
env[ECCUBE_ADMIN_ROUTE] = \${ADMIN_ROUTE}
EOF

# .envから機密情報を削除
sed -i '/^DATABASE_URL=/d' /var/www/eccube/.env
sed -i '/^ECCUBE_AUTH_MAGIC=/d' /var/www/eccube/.env
sed -i '/^ECCUBE_ADMIN_ROUTE=/d' /var/www/eccube/.env
chmod 600 /var/www/eccube/.env

systemctl restart php8.3-fpm
ENDSSH
```

## Step 12: Nginx設定・SSL取得・デプロイスクリプト設置

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
    add_header Referrer-Policy 'strict-origin-when-cross-origin' always;
    location / { try_files \$uri /index.php\$is_args\$args; }
    location ~ ^/index\.php(/|$) {
        fastcgi_pass unix:/run/php/php8.3-fpm.sock;
        fastcgi_split_path_info ^(.+\.php)(/.*)$;
        include fastcgi_params;
        fastcgi_param SCRIPT_FILENAME \$realpath_root\$fastcgi_script_name;
        fastcgi_param DOCUMENT_ROOT \$realpath_root;
        internal;
    }
    location ~ /\.(?!well-known) { deny all; }
    location ~ \.php$ { return 404; }
}
NGINX
  ln -sf /etc/nginx/sites-available/eccube /etc/nginx/sites-enabled/
  nginx -t && systemctl reload nginx
  apt install certbot python3-certbot-nginx -y
  certbot --nginx -d ${DOMAIN} --non-interactive --agree-tos -m admin@${DOMAIN}
  cat > /var/www/eccube/deploy.sh << 'DEPLOY'
#!/bin/bash
set -euo pipefail
cd /var/www/eccube
echo '=== デプロイ開始 ==='
set -a; source /etc/eccube/secrets.env; set +a
CREATED_MAINTENANCE=false
if [ ! -f .maintenance ]; then
  touch .maintenance
  CREATED_MAINTENANCE=true
  echo 'メンテナンスモード: ON'
fi
git fetch origin && git reset --hard origin/main
composer install --no-dev --optimize-autoloader
php bin/console cache:clear --env=prod --no-debug
php bin/console cache:warmup --env=prod --no-debug
chmod -R 775 /var/www/eccube/var
if [ "$CREATED_MAINTENANCE" = true ]; then
  rm -f .maintenance
  echo 'メンテナンスモード: OFF'
fi
echo '=== デプロイ完了！ ==='
DEPLOY
  chmod +x /var/www/eccube/deploy.sh
  chown ${USERNAME}:www-data /var/www/eccube/deploy.sh
"
```

## Step 13: 完了確認

```bash
ssh ${USERNAME}@${VPS_IP} "
  sudo ufw status
  sudo fail2ban-client status sshd
  curl -s -o /dev/null -w 'HTTP Status: %{http_code}' https://${DOMAIN}/
"
```
````

## スキルの実行方法

VPSにrootでSSH接続した状態でClaude Codeを開き、以下を実行します。

```
/setup-eccube-vps
```

Claude Codeが必要情報を確認してから自動でStep 1〜13を実行します。

## スキルのカスタマイズ

SKILL.md を編集することで、自分の環境に合わせてカスタマイズできます。

- **複数ドメイン対応**: Step 12のNginx設定を複数サーバーブロックに変更
- **PostgreSQL対応**: Step 8のMySQL設定をPostgreSQLに置き換え
- **PHP-FPMチューニング追加**: Step 7の後にチューニングステップを追加
