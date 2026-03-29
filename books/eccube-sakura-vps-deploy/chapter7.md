---
title: "本番運用のベストプラクティス"
---

## データベースのバックアップ

本番環境では定期的なバックアップが必須です。障害発生時にバックアップがなければ、データを復元できません。

### 手動バックアップ

```bash
# gzip圧縮してバックアップ取得
mysqldump -u eccube_user -p eccube | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 自動バックアップ（cronで毎日実行）

```bash
sudo nano /etc/cron.d/eccube-backup
```

```cron
# 毎日午前3時にバックアップを取得（30日分保持）
0 3 * * * eccube-admin mysqldump -u eccube_user -p'your-password' eccube | gzip > /var/backups/eccube/eccube_$(date +\%Y\%m\%d).sql.gz && find /var/backups/eccube/ -mtime +30 -delete
```

```bash
sudo mkdir -p /var/backups/eccube
sudo chown eccube-admin:eccube-admin /var/backups/eccube
```

:::message alert
バックアップはVPS内だけでなく、S3等の**外部ストレージにも保存**することを推奨します。サーバー障害時にバックアップごと失うリスクを防ぎます。
:::

## ログの確認方法

### Nginxのログ

```bash
# エラーログ
sudo tail -f /var/log/nginx/eccube_error.log

# アクセスログ
sudo tail -f /var/log/nginx/eccube_access.log
```

### EC-CUBEのログ

```bash
tail -f /var/www/eccube/var/log/prod.log
```

### fail2banのログ（ブロックされたIPの確認）

```bash
sudo fail2ban-client status sshd
sudo zgrep "Ban" /var/log/fail2ban.log
```

## SSL証明書の更新

Let's Encryptの証明書は90日で期限切れになりますが、certbotが自動更新します。

```bash
# 自動更新の確認
sudo systemctl status certbot.timer

# 手動で更新テスト
sudo certbot renew --dry-run
```

## EC-CUBEのアップデート

EC-CUBEの新バージョンがリリースされたら以下の手順でアップデートします。

```bash
# バックアップを取ってから実行
mysqldump -u eccube_user -p eccube | gzip > backup_before_update.sql.gz

# 本家の更新を取り込む
git fetch upstream
git merge upstream/4.3

# 依存関係を更新
composer install --no-dev --optimize-autoloader

# マイグレーションがある場合
php bin/console doctrine:migrations:migrate --env=prod

# キャッシュをクリア
php bin/console cache:clear --env=prod --no-debug
```

## サーバーのセキュリティアップデート

定期的にシステムパッケージをアップデートします。

```bash
sudo apt update && sudo apt upgrade -y
```

自動セキュリティアップデートを有効にすることも可能です。

```bash
sudo apt install unattended-upgrades -y
sudo dpkg-reconfigure unattended-upgrades
```

## 監視の設定

### ディスク使用量の確認

```bash
df -h
du -sh /var/www/eccube/var/log/*
```

### メモリ・CPU使用量の確認

```bash
htop  # sudo apt install htop -y
free -h
```

### Nginxのステータス確認

```bash
sudo systemctl status nginx
sudo nginx -t
```

## よくあるトラブルと対処法

### 500エラーが出る

```bash
# Nginxのエラーログを確認
sudo tail -50 /var/log/nginx/eccube_error.log

# EC-CUBEのログを確認
tail -50 /var/www/eccube/var/log/prod.log

# パーミッションを確認
ls -la /var/www/eccube/var/
```

### デプロイ後に画面が更新されない

```bash
cd /var/www/eccube
php bin/console cache:clear --env=prod --no-debug
```

### MySQLに接続できない

```bash
# MySQLの状態確認
sudo systemctl status mysql

# 接続テスト
mysql -u eccube_user -p -e "SELECT 1"
```

### Let's Encryptの証明書が更新されない

```bash
# DNSとポート80が正しく設定されているか確認
sudo ufw status
curl -I http://your-domain.com

# 強制更新
sudo certbot renew --force-renewal
```

## まとめ

本番運用で最低限行うべきことをまとめます。

| 作業 | 頻度 | コマンド |
|---|---|---|
| バックアップ確認 | 毎日（自動） | `ls -la /var/backups/eccube/` |
| セキュリティアップデート | 週1回 | `apt update && apt upgrade -y` |
| ログ確認 | 異常時 | `tail -f /var/log/nginx/eccube_error.log` |
| fail2ban確認 | 月1回 | `fail2ban-client status sshd` |
| SSL証明書確認 | 月1回 | `certbot certificates` |
| EC-CUBEアップデート | リリース時 | 上記アップデート手順 |
