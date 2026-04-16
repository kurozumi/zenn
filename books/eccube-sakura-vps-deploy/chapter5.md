---
title: "Claude Codeスキルで1コマンド自動化"
---

## スキルを使う利点

前章までの手順を手動で実行すると、1〜2時間かかります。Claude Codeのカスタムスキルを使えば `/setup-eccube-vps` の1コマンドでサーバー設定からEC-CUBEのデプロイまでを自動実行できます。EC-CUBEのインストール設定はブラウザのGUIウィザードで行うため、DBパスワードや管理者情報がClaude Codeのコンテキストに入りません。

| 手動 | スキル使用 |
|---|---|
| 手順書を見ながら1コマンドずつ実行 | 1コマンドで自動実行（GUIインストール以外） |
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
allowed-tools: AskUserQuestion, Bash(ssh *), Bash(ssh-copy-id *)
---

# EC-CUBE VPS セットアップスキル

## Step 0: セットアップ情報の確認

`AskUserQuestion` ツールを使って以下の3つを順番に確認してください。パスワード類はここでは聞きません。

- VPSのIPアドレス（`VPS_IP`）
- 作成する一般ユーザー名（`USERNAME`、例: `eccube-admin`）※ EC-CUBEやサービス名を連想させない名前を推奨
- EC-CUBEを公開するドメイン名（`DOMAIN`、例: `shop.example.com`）

確認後、以下のコマンドで変数をセットしてから各ステップを実行してください。

```bash
export VPS_IP="確認したIPアドレス"
export USERNAME="確認したユーザー名"
export DOMAIN="確認したドメイン名"
```

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

## Step 8: データベースの作成（手動）

**このステップはClaude Codeを介さず、ユーザーが直接ターミナルでSSHして実行してください。**

```bash
# ユーザーがターミナルで直接実行
ssh root@YOUR_VPS_IP
mysql -u root
```

```sql
CREATE DATABASE eccube CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'eccube_user'@'localhost' IDENTIFIED BY 'パスワードを設定';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, DROP, INDEX, ALTER,
      CREATE TEMPORARY TABLES, LOCK TABLES
      ON eccube.* TO 'eccube_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

設定したパスワードは後のGUIインストーラー（Step 11）で使用します。完了したら `AskUserQuestion` ツールでユーザーに完了を確認し、Step 9 に進んでください。

## Step 9: Composerのインストール

```bash
ssh root@${VPS_IP} "
  php -r \"copy('https://getcomposer.org/installer', 'composer-setup.php');\"
  php -r \"if (hash_file('sha384', 'composer-setup.php') === file_get_contents('https://composer.github.io/installer.sig')) { echo 'Installer verified'; } else { echo 'Installer corrupt'; unlink('composer-setup.php'); } echo PHP_EOL;\"
  php composer-setup.php && php -r \"unlink('composer-setup.php');\"
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
  rm -f .env
"
```

## Step 11: パーミッション設定

```bash
ssh root@${VPS_IP} "
  chown -R ${USERNAME}:www-data /var/www/eccube
  find /var/www/eccube -type d -exec chmod 755 {} \;
  find /var/www/eccube -type f -exec chmod 644 {} \;
  chmod -R 775 /var/www/eccube/var /var/www/eccube/html \
    /var/www/eccube/app/Plugin /var/www/eccube/app/PluginData \
    /var/www/eccube/app/proxy /var/www/eccube/app/template \
    /var/www/eccube/vendor
  chmod 664 /var/www/eccube/composer.json /var/www/eccube/composer.lock
"
```

## Step 12: Nginx設定・SSL取得

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
"
```

コマンドが完了したら、`AskUserQuestion` ツールでユーザーに以下を伝えてください：

**「ブラウザで `https://${DOMAIN}/install` を開き、インストールウィザードを完了してください。**
**完了したら「Step 13 を実行して」と教えてください。」**

インストールウィザードは6ステップです。入力が必要な項目は以下の通りです。

**ステップ3：サイトの設定**

| 項目 | 内容 |
|---|---|
| あなたの店名 | 任意の店名 |
| メールアドレス | 受注メール等の宛先アドレス |
| 管理画面ログインID | 半角英数字4〜50文字（推測されにくいものを） |
| 管理画面パスワード | 半角英数字12〜50文字 |
| 管理画面のディレクトリ名 | 半角英数字4〜50文字（推測されにくいものを） |
| SSL制限 | SSLは設定済みのためチェック推奨 |
| 管理画面のIPアドレス制限 | 任意（固定IPがあれば設定推奨） |
| SMTPホスト | localhost（メール送信の設定は後で変更可） |
| SMTPポート | 25 |
| SMTPユーザー・パスワード | 空欄でも可 |

**ステップ4：データベースの設定**

| 項目 | 値 |
|---|---|
| データベースの種類 | MySQL |
| データベースのホスト名 | 127.0.0.1 |
| データベースのポート番号 | 3306 |
| データベース名 | eccube |
| ユーザ名 | eccube_user |
| パスワード | Step 8 で設定したパスワード |

## Step 13: デプロイスクリプト設置

```bash
ssh root@${VPS_IP} "
  cat > /var/www/eccube/deploy.sh << 'DEPLOY'
#!/bin/bash
set -euo pipefail
cd /var/www/eccube
echo '=== デプロイ開始 ==='
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
if [ \"\$CREATED_MAINTENANCE\" = true ]; then
  rm -f .maintenance
  echo 'メンテナンスモード: OFF'
fi
echo '=== デプロイ完了！ ==='
DEPLOY
  chmod +x /var/www/eccube/deploy.sh
  chown ${USERNAME}:www-data /var/www/eccube/deploy.sh
"
```

## Step 14: 完了確認

```bash
ssh ${USERNAME}@${VPS_IP} "
  sudo ufw status
  sudo fail2ban-client status sshd
  curl -s -o /dev/null -w 'HTTP Status: %{http_code}' https://${DOMAIN}/
"
```

````

## スキルの実行方法

**ローカルマシン**でClaude Codeを開き、以下を実行します。

```
/setup-eccube-vps
```

Claude Codeが`AskUserQuestion`でVPS_IP・USERNAME・DOMAINを確認してからStep 1〜14を実行します。DBパスワードはClaude Codeに渡しません。Step 12完了後にブラウザのGUIインストーラー操作を求められるので、完了後に「Step 13 を実行して」と伝えると残りのステップが続行されます。

## スキルのカスタマイズ

SKILL.md を編集することで、自分の環境に合わせてカスタマイズできます。

- **複数ドメイン対応**: Step 12のNginx設定を複数サーバーブロックに変更
- **PostgreSQL対応**: Step 8のMySQL設定をPostgreSQLに置き換え
- **PHP-FPMチューニング追加**: Step 7の後にチューニングステップを追加
