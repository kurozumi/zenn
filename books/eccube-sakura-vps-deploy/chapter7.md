---
title: "本番運用のベストプラクティス"
---

## データベースのバックアップ

本番環境では定期的なバックアップが必須です。障害発生時にバックアップがなければ、データを復元できません。

### MySQL認証情報ファイルの設定

パスワードをコマンドラインに直接書くと `ps aux` などで他のユーザーに見えてしまいます。MySQL の認証情報ファイル（`~/.my.cnf`）に分離しておくと、手動・自動どちらのバックアップでもパスワード入力なしで実行できます。

```bash
nano ~/.my.cnf
```

```ini
[client]
user=eccube_user
password=your-strong-password
```

```bash
# 自分だけ読めるようにパーミッションを制限（必須）
chmod 600 ~/.my.cnf
```

### 手動バックアップ

```bash
# gzip圧縮してバックアップ取得（~/.my.cnf の認証情報を使用）
mysqldump eccube | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
```

### 自動バックアップ（cronで毎日実行）

```bash
sudo mkdir -p /var/backups/eccube
sudo chown eccube-admin:eccube-admin /var/backups/eccube
sudo nano /etc/cron.d/eccube-backup
```

```cron
# 毎日午前3時にバックアップを取得（30日分保持）
0 3 * * * eccube-admin mysqldump eccube | gzip > /var/backups/eccube/eccube_$(date +\%Y\%m\%d).sql.gz && find /var/backups/eccube/ -mtime +30 -delete
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

## ログローテーションの設定

Nginxのログは Ubuntu 標準の logrotate で自動的にローテーションされますが、EC-CUBE のアプリケーションログは設定が必要です。放置するとディスクが枯渇します。

```bash
sudo nano /etc/logrotate.d/eccube
```

```
/var/www/eccube/var/log/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 664 eccube-admin www-data
}
```

```bash
# 設定の動作確認（--debug で実際には実行しない）
sudo logrotate --debug /etc/logrotate.d/eccube
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

### Step 1: アップデート前にプラグインの互換性を確認する

EC-CUBE をアップデートする前に、インストール済みのプラグインが新バージョンに対応しているか確認します。対応していないプラグインがあるとアップデート後にエラーになります。

```bash
cd /var/www/eccube

# インストール済みのプラグインディレクトリを確認
ls app/Plugin/

# Composer で管理されているプラグインパッケージを確認
composer show | grep ec-cube
```

各プラグインについて、以下のいずれかで互換性を確認します。

- **EC-CUBE オーナーズストア**: プラグインのページに「対応バージョン」が記載されています
- **プラグインの GitHub**: README やリリースノートに対応バージョンが記載されていることがあります

対応バージョン外のプラグインがある場合は、**プラグインのアップデートが出るまでEC-CUBEのアップデートを見送る**のが安全です。

:::message alert
プラグインが新バージョン非対応のまま EC-CUBE をアップデートすると、管理画面が開けなくなったり、注文処理が止まったりする可能性があります。必ず事前確認を行ってください。
:::

### Step 2: バックアップを取る（必須）

アップデート失敗時に確実に戻せるよう、コードとDBの両方をバックアップします。

```bash
cd /var/www/eccube

# DBバックアップ（~/.my.cnf の認証情報を使用）
mysqldump eccube | gzip > ~/backup_before_update_$(date +%Y%m%d).sql.gz

# アップデート前のコミットハッシュを記録しておく
git log --oneline -1
```

表示されたコミットハッシュ（例: `a1b2c3d`）をメモしておきます。ロールバック時に使います。

### Step 3: アップデートを実行する

```bash
# 本家の更新を取り込む（ローカル作業）
git fetch upstream
git merge upstream/4.3

# チームリポジトリへプッシュ
git push origin main

# サーバーにデプロイ
ssh eccube-admin@<サーバーのIPアドレス>
cd /var/www/eccube && ./deploy.sh

# マイグレーションがある場合
php bin/console doctrine:migrations:migrate --env=prod
```

### Step 4: アップデート後の動作確認

```bash
# ログにエラーがないか確認
tail -50 /var/www/eccube/var/log/prod.log
tail -20 /var/log/nginx/eccube_error.log
```

- [ ] フロントのトップページが表示される
- [ ] 管理画面にログインできる
- [ ] 使用中のプラグインが正常に動作する
- [ ] 決済など重要な機能が動作する

### ロールバック手順（アップデートに失敗した場合）

アップデート後に重大な不具合が発生した場合、以下の手順で元に戻します。

#### コードを戻す

```bash
cd /var/www/eccube

# メモしておいたコミットハッシュで元に戻す
git reset --hard <アップデート前のコミットハッシュ>

# チームリポジトリも戻す（強制プッシュが必要）
git push --force origin main
```

:::message alert
`git push --force` は他のメンバーの作業を上書きする可能性があります。ロールバック時はチームに周知した上で実行してください。
:::

#### 依存関係を戻す

```bash
composer install --no-dev --optimize-autoloader
php bin/console cache:clear --env=prod --no-debug
```

#### DBを戻す（マイグレーションを実行した場合のみ）

マイグレーションを実行していた場合は、バックアップからDBを復元します。

```bash
# バックアップから復元（本番データが上書きされるため慎重に）
gunzip < ~/backup_before_update_$(date +%Y%m%d).sql.gz | mysql eccube
```

:::message alert
DB復元はアップデート後に発生した注文・会員登録などのデータが**すべて消えます**。マイグレーションを伴うアップデートは必ずメンテナンス時間帯に行い、復元前にその旨をチームで確認してください。
:::

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
| ディスク使用量確認 | 週1回 | `df -h` |
| fail2ban確認 | 月1回 | `fail2ban-client status sshd` |
| SSL証明書確認 | 月1回 | `certbot certificates` |
| EC-CUBEアップデート | リリース時 | プラグイン互換性確認 → バックアップ → 上記手順 |
