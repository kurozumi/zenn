---
title: "サーバーセキュリティの基礎"
---

## なぜセキュリティ設定が必要か

VPSを公開した瞬間から、インターネット上の無数のボットがポートスキャンや不正ログインを試みます。セキュリティ設定なしでは、数時間以内に不正アクセスの試行が始まります。

この章では以下を設定します。

| 設定 | 防ぐ攻撃 |
|---|---|
| 一般ユーザー作成 | rootへの直接攻撃 |
| SSH鍵認証 | パスワードの総当たり攻撃 |
| rootログイン禁止 | rootへの不正ログイン |
| ufw | 不要なポートへのアクセス |
| fail2ban | 繰り返しの不正アクセス試行 |

:::message alert
この章の設定は**必ず順番通りに**行ってください。SSH鍵の設定が完了する前にパスワード認証を無効にすると、サーバーに入れなくなります。万が一ロックアウトした場合はさくらVPSのコントロールパネルからVNCコンソールで復旧できます。
:::

## システムを最新に更新する

```bash
apt update && apt upgrade -y
```

## 一般ユーザーを作成する

rootで常時作業するのは危険です。一般ユーザーを作成してsudo権限を付与します。

```bash
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

**別のターミナルを開いて**ログインできることを確認します。

```bash
ssh eccube-admin@<サーバーのIPアドレス>
sudo whoami  # root と表示されればOK
```

## SSH鍵認証を設定する

パスワード認証はブルートフォース攻撃に弱いため、SSH鍵認証に切り替えます。

### ローカルマシンで鍵ペアを生成する

```bash
# ローカルのターミナルで実行
ssh-keygen -t ed25519 -C "eccube-vps"
# 保存先: ~/.ssh/id_ed25519（そのままEnter）
# パスフレーズ: 設定することを強く推奨
```

`ed25519` はRSAより安全で鍵のサイズも小さい現代的なアルゴリズムです。

### 公開鍵をサーバーにコピーする

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub eccube-admin@<サーバーのIPアドレス>
```

### 鍵でログインできることを確認する

```bash
ssh -i ~/.ssh/id_ed25519 eccube-admin@<サーバーのIPアドレス>
```

ログインできたら次のステップに進みます。**必ずここで確認してください。**

## SSHの設定を強化する

```bash
sudo nano /etc/ssh/sshd_config
```

以下の項目を変更します。

```
# rootログインを禁止
PermitRootLogin no

# パスワード認証を無効化
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

## ファイアウォール（ufw）を設定する

必要なポートだけ開けて、それ以外はすべてブロックします。

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
sudo ufw status verbose
```

:::message alert
MySQLポート（3306）は `deny incoming` によりデフォルトでブロックされています。`ufw allow 3306` は絶対に実行しないでください。外部からDBに直接接続できる状態になります。

MySQLがlocalhostのみをリッスンしていることを確認します。
```bash
sudo ss -tlnp | grep 3306
# 127.0.0.1:3306 と表示されればOK
```
:::

## fail2banで不正アクセスを防ぐ

fail2banは、繰り返しログインに失敗したIPアドレスを自動的にブロックします。

```bash
sudo apt install fail2ban python3-systemd -y
```

:::message
`python3-systemd` はUbuntu 24.04でfail2banがsystemdのジャーナルログを読むために必要です。これがないとSSHのログを正しく監視できません。
:::

設定ファイルを作成します（`jail.conf` は直接編集せず `jail.local` を作る）。

```bash
sudo nano /etc/fail2ban/jail.local
```

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

```bash
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# 動作確認
sudo fail2ban-client status sshd
```

## セキュリティ設定の確認

この章の設定が完了したら以下を確認してください。

- [ ] `eccube-admin` ユーザーでSSHログインできる
- [ ] rootユーザーでSSHログインできない（拒否される）
- [ ] パスワードでSSHログインできない（拒否される）
- [ ] `sudo ufw status` でファイアウォールが `active` になっている
- [ ] `sudo fail2ban-client status sshd` でfail2banが動作している
