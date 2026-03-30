---
title: "チームでの安全な運用"
---

## チーム開発の基本的な流れ

個人開発とチーム開発ではデプロイの考え方が変わります。

```
EC-CUBE公式 (upstream)
        ↓ git fetch upstream && git merge upstream/4.3（アップデート時）
チームリポジトリ (origin) ← メンバーが feature ブランチで開発 → PR作成
        ↓                      マネージャーがレビュー → main にマージ
本番サーバー: ./deploy.sh（git reset --hard origin/main → キャッシュクリア）
```

この章では、このフローを実現するためのリポジトリ設定とチーム運用ルールを説明します。

## リポジトリのセットアップ

### EC-CUBE本家をForkしない理由

EC-CUBEリポジトリをForkして使う方法もありますが、以下のリスクがあります。

- GitHubの「Contribute」ボタンを誤ってクリックすると、本家リポジトリにPull Requestを送ってしまう
- Fork元と自分のリポジトリが紐づいているため混乱が生じやすい

**Forkせずに `upstream` リモートで本家を追従する方法**を推奨します。

### チームリポジトリの作成

```bash
gh repo create my-eccube --private --clone
cd my-eccube
```

| オプション | 意味 |
|---|---|
| `--private` | リポジトリを非公開にする |
| `--clone` | 作成後にローカルへ自動でクローンする |

### EC-CUBE本家を `upstream` として追加

```bash
git remote add upstream https://github.com/EC-CUBE/ec-cube.git
git fetch upstream

# --allow-unrelated-historiesは初回のみ必要（共通の親コミットがないため）
git merge upstream/4.3 --allow-unrelated-histories

git push -u origin main
```

### 本家の更新を取り込む（アップデート時）

```bash
git fetch upstream
git merge upstream/4.3
git push origin main
```

:::message alert
`git push upstream` は絶対に実行しないでください。本家リポジトリへの直接プッシュを試みることになります。
:::

### サーバーの origin をチームリポジトリに切り替える

Chapter 4/5 でサーバーに EC-CUBE を直接 clone したため、サーバーの `origin` は EC-CUBE 公式リポジトリになっています。チームの変更をデプロイできるよう、`origin` をチームリポジトリに切り替えます。

```bash
ssh eccube-admin@<サーバーのIPアドレス>
cd /var/www/eccube

# origin をチームリポジトリに変更
git remote set-url origin https://github.com/yourteam/my-eccube.git

# EC-CUBE公式を upstream として追加（サーバー側でも追跡できるようにする）
git remote add upstream https://github.com/EC-CUBE/ec-cube.git

# 設定確認
git remote -v
```

正しく設定されると以下のように表示されます。

```
origin    https://github.com/yourteam/my-eccube.git (fetch)
origin    https://github.com/yourteam/my-eccube.git (push)
upstream  https://github.com/EC-CUBE/ec-cube.git (fetch)
upstream  https://github.com/EC-CUBE/ec-cube.git (push)
```

この設定後、`deploy.sh` の `git reset --hard origin/main` がチームリポジトリの main ブランチを反映するようになります。

## メンバーの参加方法

チームリポジトリはメンバー全員が書き込み権限を持っているので、**Forkは不要**です。

```bash
git clone https://github.com/yourteam/my-eccube.git
cd my-eccube
git checkout -b feature/my-feature
```

## メンバーが抜けたときの対応

チームメンバーが退出した場合、**GitHubとサーバーの両方**からアクセスを削除する必要があります。どちらか一方だけでは不完全です。

### 1. GitHubリポジトリから削除する

GitHubの「Settings」→「Collaborators」から対象メンバーを削除します。削除後、そのメンバーはリポジトリへのアクセスができなくなります。

### 2. サーバーのSSH公開鍵を削除する

メンバーがサーバーにSSHできる場合、`~/.ssh/authorized_keys` から該当の公開鍵を削除します。

```bash
ssh eccube-admin@<サーバーのIPアドレス>
nano ~/.ssh/authorized_keys
```

該当メンバーの公開鍵の行を削除して保存します。1行が1つの公開鍵です。

```bash
# 削除後、残っている鍵を確認
cat ~/.ssh/authorized_keys
```

### 3. 機密情報をローテーションする（状況に応じて）

メンバーがDBパスワードや `.env` の内容を知っていた場合は、以下も変更してください。

```bash
# DBパスワードの変更
sudo mysql
ALTER USER 'eccube_user'@'localhost' IDENTIFIED BY '新しいパスワード';
FLUSH PRIVILEGES;

# .envのDATABASE_URLを新しいパスワードで更新
nano /var/www/eccube/.env
```

:::message alert
特にマネージャー権限を持っていたメンバーが抜ける場合は、DBパスワードと `ECCUBE_ADMIN_ROUTE` の変更を強く推奨します。
:::

## 役割でスキルを分ける

本番デプロイはマネージャーのみが行うのが基本です。Claude Codeスキルで役割を分けましょう。

| 役割 | スキル | できること |
|---|---|---|
| メンバー | `/pr-eccube` | ブランチ作成・コミット・PR作成のみ |
| マネージャー | `/deploy-eccube` | サーバーへのデプロイまで |

**メンバー用スキル** `.claude/skills/pr-eccube/SKILL.md`:

```yaml
---
name: pr-eccube
description: EC-CUBEの変更をPull Requestとして提出する
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh pr *)
---

以下の手順で変更をPull Requestとして提出してください。

## Step 1: 作業ブランチの作成
```bash
git checkout -b feature/$ARGUMENTS
```

## Step 2: 変更のコミット
```bash
git add . && git status
git commit -m "feat: $ARGUMENTS"
```

## Step 3: PRの作成
```bash
git push -u origin HEAD
gh pr create --title "$ARGUMENTS" --body "## 変更内容"
```
```

:::message alert
スキルの `allowed-tools` による制限はClaude Code上の操作制限にすぎません。**本質的な安全策はGitHubのリポジトリ権限管理**です。メンバーにはPRのみ、マネージャーにはmainへのマージ権限を設定しましょう。
:::

## デプロイスクリプトの運用

Chapter4で設置したデプロイスクリプトを使います。

```bash
ssh eccube-admin@<サーバーのIPアドレス>
cd /var/www/eccube && ./deploy.sh
```

### スキーマ変更がある場合

:::message alert
マイグレーションが絡む場合は失敗するとメンテナンスモードが残り続けるリスクがあります。

```bash
# 必ずバックアップを取ってから実行（~/.my.cnf の認証情報を使用）
mysqldump eccube | gzip > backup_$(date +%Y%m%d).sql.gz
php bin/console doctrine:migrations:migrate --env=prod
```
:::

## スキルをチームで共有する

スキルをプロジェクトの `.claude/skills/` に配置してGit管理します。

```bash
mkdir -p .claude/skills/pr-eccube
# SKILL.md を配置
git add .claude/skills/
git commit -m "Add team skills"
git push origin main
```

これでチームメンバー全員が同じスキルを使えるようになります。
