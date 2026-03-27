---
title: "【概念解説】Claude CodeカスタムスキルでEC-CUBEのAWSデプロイを1コマンド化するアイデア"
emoji: "🚀"
type: "tech"
topics: ["eccube", "eccube4", "aws", "claudecode", "ecs"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

:::message alert
**この記事はClaude Codeのスキル機能を使ったデプロイ自動化の概念と設計を解説したものです。**

実際に運用するには以下が別途必要です。この記事だけをそのまま本番環境に適用しないでください。

- VPC・サブネット・セキュリティグループ等のネットワーク設定
- ECSタスク定義の作成（CPU・メモリ・環境変数・ログ設定等）
- ECSサービスの作成
- ALB（ロードバランサー）の設定
- RDS（データベース）の構築
- Apacheの設定（EC-CUBEのDocumentRoot等）
- デプロイ失敗時のロールバック手順
:::

## はじめに

**結論から言います。Claude Codeのカスタムスキルを使えば、EC-CUBEのAWSデプロイが `/deploy-eccube` の1コマンドで完結します。**

ECRへのイメージプッシュ、ECSサービスの更新、デプロイ完了の待機まで、Claude Codeが自動で順番に実行します。手順書を開く必要も、コマンドを1つずつコピペする必要もありません。

「EC-CUBEをAWSに本番デプロイしたいけど、手順が複雑で毎回ドキュメントを見返している」——そういう状況に終止符を打てます。

**この記事で手に入るもの:**

- ローカルで `/deploy-eccube` と打つだけのデプロイ環境
- チームで共有できるデプロイ手順（Git管理）
- EC-CUBE本家を安全に追従するリポジトリ構成

初回セットアップは30〜60分ほど。一度作れば永続的に使えます。

この記事では以下を解説します。

- 必要なツールの準備（GitHub CLI、AWS CLI、Docker）
- EC-CUBEリポジトリのセットアップ（本家を安全に追従する方法）
- AWS インフラの準備（ECR、ECS）
- Claude Codeデプロイスキルの作成
- `/deploy-eccube` コマンドの使い方

## Claude Codeのスキルとは

Claude Codeのスキルは、`SKILL.md` という Markdownファイルに指示を書くだけで作れるカスタムコマンドです。

```
~/.claude/skills/
└── deploy-eccube/
    └── SKILL.md   ← ここに指示を書く
```

スキルを作ると `/deploy-eccube` というコマンドが使えるようになります。

| スキルの配置場所 | パス | 適用範囲 |
|---|---|---|
| 個人スキル | `~/.claude/skills/<name>/SKILL.md` | すべてのプロジェクト |
| プロジェクトスキル | `.claude/skills/<name>/SKILL.md` | そのプロジェクトのみ |

`disable-model-invocation: true` を設定すると、Claude が自動的に呼び出さなくなります。デプロイのような副作用のある操作には必ず設定しましょう。

## 必要なツールの準備

### 1. GitHub CLI

GitHub CLIは、コマンドラインからGitHubを操作するための公式ツールです。

**macOS（Homebrew）:**

```bash
brew install gh
```

**Linux（Ubuntu/Debian）:**

```bash
type -p curl >/dev/null || sudo apt install curl -y
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
  | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
  | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh -y
```

**Windows（winget）:**

```powershell
winget install --id GitHub.cli
```

インストール後、GitHubへの認証を行います。

```bash
gh auth login
```

### 2. AWS CLI

AWS CLIは、AWSサービスをコマンドラインで操作するツールです。

**macOS（Homebrew）:**

```bash
brew install awscli
```

**Linux:**

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

**Windows:**

```powershell
# PowerShellで実行
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

インストール後、AWSの認証情報を設定します。

```bash
aws configure
# AWS Access Key ID: your-access-key
# AWS Secret Access Key: your-secret-key
# Default region name: ap-northeast-1
# Default output format: json
```

:::message alert
`aws configure` で設定した認証情報は `~/.aws/credentials` にプレーンテキストで保存されます。本番環境のEC2やECSから実行する場合は、IAMロール（ECS Task Role）を使用し、アクセスキーをファイルに保存しないことを推奨します。
:::

### 3. Docker

EC-CUBEをコンテナ化するためにDockerが必要です。

**macOS / Windows:**

[Docker Desktop](https://www.docker.com/products/docker-desktop/) をインストールしてください。

**Linux:**

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# ログアウト&ログインしてグループ変更を反映
```

## EC-CUBEリポジトリのセットアップ

### Forkしない理由

EC-CUBEリポジトリを **Fork** して使う方法もありますが、以下のリスクがあります。

- GitHubの「Contribute」ボタンを誤ってクリックすると、本家リポジトリにPull Requestを送ってしまう
- Fork元と自分のリポジトリが紐づいているため、混乱が生じやすい

そこで、**Forkせずに `upstream` リモートで本家を追従する方法**を推奨します。

### セットアップ手順

**Step 1: GitHub上に空のプライベートリポジトリを作成する**

```bash
gh repo create my-eccube --private --clone
cd my-eccube
```

| オプション | 意味 |
|---|---|
| `--private` | リポジトリを非公開（プライベート）にする |
| `--clone` | 作成後にローカルへ自動でクローンする |

このコマンド1つで「リポジトリ作成 → プライベート設定 → ローカルにクローン」を同時に行います。`--clone` がない場合は別途 `git clone` が必要です。

**Step 2: EC-CUBE本家を `upstream` リモートとして追加する**

```bash
# EC-CUBE本家リポジトリをupstreamとして登録
git remote add upstream https://github.com/EC-CUBE/ec-cube.git

# upstreamの内容を取得
git fetch upstream

# EC-CUBE 4.3の内容をローカルmainブランチにマージ
git merge upstream/4.3 --allow-unrelated-histories

# 自分のリモート（origin）にプッシュ
git push -u origin main
```

**Step 3: 本家の更新を取り込む（アップデート時）**

```bash
git fetch upstream
git merge upstream/4.3
git push origin main
```

これで `upstream` が EC-CUBE本家、`origin` が自分のリポジトリと明確に分かれます。誤って本家にPull Requestを送るリスクがなくなります。

:::message alert
`git push upstream` は絶対に実行しないでください。本家リポジトリへの直接プッシュを試みることになります。
:::

リモートの設定を確認する場合は以下のコマンドを使います。

```bash
git remote -v
# origin    https://github.com/yourname/my-eccube.git (fetch)
# origin    https://github.com/yourname/my-eccube.git (push)
# upstream  https://github.com/EC-CUBE/ec-cube.git (fetch)
# upstream  https://github.com/EC-CUBE/ec-cube.git (push)
```

## AWS インフラの準備

### 必要なAWSリソース

| リソース | 用途 |
|---|---|
| ECR (Elastic Container Registry) | Dockerイメージの保存 |
| ECS (Elastic Container Service) | コンテナのオーケストレーション |
| Fargate | サーバーレスのコンテナ実行環境 |
| RDS (MySQL) | EC-CUBEのデータベース |
| S3 | 商品画像等のファイルストレージ |
| ALB (Application Load Balancer) | HTTPSトラフィックの振り分け |

### ECRリポジトリの作成

```bash
aws ecr create-repository \
  --repository-name eccube \
  --region ap-northeast-1

# リポジトリURIを確認（後の設定で使用する）
aws ecr describe-repositories \
  --repository-names eccube \
  --query 'repositories[0].repositoryUri' \
  --output text
```

### ECSクラスターの作成

```bash
aws ecs create-cluster \
  --cluster-name eccube-cluster \
  --capacity-providers FARGATE \
  --default-capacity-provider-strategy capacityProvider=FARGATE,weight=1 \
  --region ap-northeast-1
```

### 本番用 Dockerfile の準備

AWS ECS（Fargate）はDockerコンテナで動作します。EC-CUBEのプロジェクトルートに本番用の `Dockerfile` を作成します。

```dockerfile
FROM php:8.3-apache

# 必要なPHP拡張のインストール
RUN apt-get update && apt-get install -y \
    libicu-dev \
    libpq-dev \
    libzip-dev \
    unzip \
    && docker-php-ext-install \
        intl \
        pdo \
        pdo_mysql \
        zip \
    && a2enmod rewrite \
    && rm -rf /var/lib/apt/lists/*

# Composerのインストール
COPY --from=composer:latest /usr/bin/composer /usr/bin/composer

WORKDIR /var/www/html

# .dockerignore で不要ファイルを除外（後述）
COPY . .

# 本番用の依存関係インストール
RUN composer install --no-dev --optimize-autoloader

# パーミッションの設定
RUN chown -R www-data:www-data /var/www/html \
    && chmod -R 775 /var/www/html/var \
    && chmod -R 775 /var/www/html/app/Plugin \
    && chmod -R 775 /var/www/html/app/PluginData \
    && chmod -R 775 /var/www/html/html

EXPOSE 80
```

### .dockerignore の作成

`COPY . .` を実行する前に、機密ファイルや不要ファイルがイメージに含まれないよう `.dockerignore` を作成します。

```
# .dockerignore
.env
.env.local
.env.*.local
var/
.git/
.gitignore
docker-compose*.yml
*.md
tests/
```

:::message alert
`.env` には `DATABASE_URL` や `APP_SECRET` などの機密情報が含まれます。必ず `.dockerignore` に追加してください。ECRにプッシュしたイメージに認証情報が含まれるのは深刻なセキュリティリスクです。
:::

### 機密情報はAWSで管理する

`.env` をコンテナに含めない代わりに、AWS上の機密情報管理サービスを使います。

| サービス | 用途 |
|---|---|
| **AWS Systems Manager Parameter Store** | `DATABASE_URL`、`APP_SECRET`、`MAILER_DSN` などの設定値 |
| **AWS Secrets Manager** | 自動ローテーションが必要なDBパスワードやAPIキー |
| **IAM Role（ECS Task Role）** | S3へのファイルアップロードなどAWSリソースへのアクセス権限 |

ECSタスク定義でParameter StoreやSecrets Managerの値を参照することで、コンテナ起動時に自動で環境変数として注入されます。

```json
{
  "containerDefinitions": [
    {
      "name": "eccube",
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:ssm:ap-northeast-1:123456789012:parameter/eccube/DATABASE_URL"
        },
        {
          "name": "APP_SECRET",
          "valueFrom": "arn:aws:ssm:ap-northeast-1:123456789012:parameter/eccube/APP_SECRET"
        }
      ]
    }
  ]
}
```

Parameter Storeへの登録は以下のコマンドで行います。

```bash
# SecureString（暗号化）で登録
aws ssm put-parameter \
  --name "/eccube/DATABASE_URL" \
  --value "mysql://user:password@rds-endpoint:3306/eccube" \
  --type SecureString \
  --region ap-northeast-1

aws ssm put-parameter \
  --name "/eccube/APP_SECRET" \
  --value "your-app-secret" \
  --type SecureString \
  --region ap-northeast-1
```

### IAM ポリシーの設定

デプロイに使用するIAMユーザー/ロールには、以下の最小権限ポリシーを付与してください。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecr:GetAuthorizationToken",
        "ecr:BatchCheckLayerAvailability",
        "ecr:InitiateLayerUpload",
        "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutImage"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:UpdateService",
        "ecs:DescribeServices",
        "ecs:ListTasks",
        "ecs:DescribeTasks"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:GetLogEvents"
      ],
      "Resource": "*"
    }
  ]
}
```

`AdministratorAccess` などの過剰な権限は付与しないようにしましょう。

## Claude Codeデプロイスキルの作成

### スキルファイルの作成

個人スキルとして作成します（すべてのプロジェクトで使えます）。

```bash
mkdir -p ~/.claude/skills/deploy-eccube
```

`~/.claude/skills/deploy-eccube/SKILL.md` を以下の内容で作成します。

````markdown
---
name: deploy-eccube
description: EC-CUBEをAWS ECS Fargateにデプロイする
disable-model-invocation: true
allowed-tools: Bash(aws *), Bash(docker *), Bash(git *)
---

# EC-CUBE AWS デプロイスキル

以下の手順でEC-CUBEをAWS ECS Fargateにデプロイしてください。

## Step 1: 事前確認

AWS CLIとDockerの状態を確認する。

```bash
aws sts get-caller-identity
docker info --format '{{.ServerVersion}}'
git log --oneline -3
```

## Step 2: 環境変数の確認

以下の環境変数が設定されているか確認する。未設定の場合はユーザーに確認する。

```bash
echo "AWS_REGION:          ${AWS_REGION:-未設定}"
echo "ECR_REPOSITORY_URI:  ${ECR_REPOSITORY_URI:-未設定}"
echo "ECS_CLUSTER:         ${ECS_CLUSTER:-未設定}"
echo "ECS_SERVICE:         ${ECS_SERVICE:-未設定}"
```

## Step 3: ECRにログイン

```bash
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REPOSITORY_URI}
```

## Step 4: Dockerイメージのビルドとタグ付け

コミットハッシュをイメージタグとして使用する。

```bash
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t eccube:${IMAGE_TAG} .
docker tag eccube:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:${IMAGE_TAG}
docker tag eccube:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:latest
```

## Step 5: ECRへのプッシュ

```bash
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}
docker push ${ECR_REPOSITORY_URI}:latest
echo "プッシュ完了: ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"
```

## Step 6: ECSサービスの更新

```bash
aws ecs update-service \
  --cluster ${ECS_CLUSTER} \
  --service ${ECS_SERVICE} \
  --force-new-deployment \
  --region ${AWS_REGION}
echo "デプロイ開始"
```

## Step 7: デプロイ完了を待機

```bash
aws ecs wait services-stable \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --region ${AWS_REGION}
echo "デプロイ完了！"
```

## Step 8: 結果確認

```bash
aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --region ${AWS_REGION} \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

## エラー時のログ確認

```bash
TASK_ARN=$(aws ecs list-tasks \
  --cluster ${ECS_CLUSTER} \
  --service-name ${ECS_SERVICE} \
  --region ${AWS_REGION} \
  --query 'taskArns[0]' \
  --output text)

TASK_ID=$(echo ${TASK_ARN} | awk -F/ '{print $NF}')

aws logs get-log-events \
  --log-group-name /ecs/eccube \
  --log-stream-name "ecs/eccube/${TASK_ID}" \
  --region ${AWS_REGION} \
  --limit 50
# ※ ログストリーム名は awslogs-stream-prefix の設定によって異なります。
# 実際のログストリーム名は CloudWatch Logs コンソールで確認してください。
```
````

### 環境変数の設定

スキルが参照する環境変数を `~/.bashrc` または `~/.zshrc` に追加します。

```bash
export AWS_REGION="ap-northeast-1"
export ECR_REPOSITORY_URI="123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/eccube"
export ECS_CLUSTER="eccube-cluster"
export ECS_SERVICE="eccube-service"
```

設定後、シェルを再読み込みします。

```bash
source ~/.bashrc  # または source ~/.zshrc
```

:::message alert
`ECR_REPOSITORY_URI` には接続先情報が含まれますが、AWSアクセスキーやシークレットキーは環境変数に直接書かないでください。`aws configure` で設定した認証情報が自動的に使われます。
:::

## 使い方

すべての準備が整ったら、Claude Code内で以下のコマンドを実行します。

```
/deploy-eccube
```

Claude Codeが以下を自動で実行します。

1. AWS CLI・Dockerの動作確認
2. 環境変数のチェック
3. ECRへのDockerログイン
4. Dockerイメージのビルド（コミットハッシュをタグに使用）
5. ECRへのプッシュ
6. ECSサービスの更新（ローリングデプロイ）
7. デプロイ完了の待機
8. 結果の表示

## チームで共有する場合

### 役割でスキルを分ける

チーム運用では、**本番デプロイはマネージャーのみ**が行うのが基本です。メンバーが誤って本番に反映してしまうリスクを防ぐために、役割ごとにスキルを分けましょう。

| 役割 | スキル | できること |
|---|---|---|
| メンバー | `/pr-eccube` | ブランチ作成・コミット・PR作成のみ |
| マネージャー | `/deploy-eccube` | ECRプッシュ・ECSデプロイまで |

**メンバー用スキル** `.claude/skills/pr-eccube/SKILL.md`:

```yaml
---
name: pr-eccube
description: EC-CUBEの変更をPull Requestとして提出する
disable-model-invocation: true
allowed-tools: Bash(git *), Bash(gh pr *)
---

# EC-CUBE PR 提出スキル

以下の手順で変更をPull Requestとして提出してください。

## Step 1: 作業ブランチの作成

```bash
git checkout -b feature/$ARGUMENTS
```

## Step 2: 変更のコミット

```bash
git add .
git status
git commit -m "feat: $ARGUMENTS"
```

## Step 3: PRの作成

```bash
git push -u origin HEAD
gh pr create --title "$ARGUMENTS" --body "## 変更内容\n\n"
```
```

`allowed-tools` に `Bash(aws *)` や `Bash(docker *)` を含めないことで、メンバーがAWS操作系のコマンドを実行できないよう制限できます。

:::message alert
ただし、スキルによる制限はあくまで **Claude Codeの操作制限** です。本質的な防衛線は **AWS IAM** にあります。メンバーのIAMユーザーにはECR/ECSの権限を付与しないことが、本当の意味での安全策です。スキルとIAMの両方で二重に制限することを推奨します。
:::

### メンバーの参加方法

チームリポジトリ（`my-eccube`）はメンバー全員が書き込み権限を持っているので、**forkは不要**です。直接クローンしてブランチを切るだけです。

| 対象 | 方法 | 理由 |
|---|---|---|
| EC-CUBE本家 | upstream リモートで追従 | 書き込み権限がないため |
| チームの `my-eccube` | 直接クローン＆ブランチ | 書き込み権限があるため |

```bash
# メンバーの参加手順
git clone https://github.com/yourteam/my-eccube.git
cd my-eccube

# 作業ブランチを切る
git checkout -b feature/my-feature

# 作業してPRを送る（/pr-eccube スキルを使うと便利）
git push origin feature/my-feature
gh pr create
```

### スキルをGitで管理する

スキルをプロジェクトの `.claude/skills/` に配置してGitで管理することで、チームメンバー全員が同じスキルを使えるようになります。

```bash
mkdir -p .claude/skills/pr-eccube
mkdir -p .claude/skills/deploy-eccube
# 各 SKILL.md を配置
git add .claude/skills/
git commit -m "Add EC-CUBE team skills"
git push origin main
```

## このスキルの限界

### メンテナンスモードの自動化はリスクがある

デプロイ中にメンテナンスモードを自動で ON/OFF することは技術的には可能ですが、**スキーマ変更（マイグレーション）が絡む場合は注意が必要**です。

スキーマ変更なしの通常デプロイであれば、以下の流れで自動化できます。

```
メンテナンス ON → イメージビルド＆プッシュ → ECS更新 → 完了待機 → メンテナンス OFF
```

一方、マイグレーションが絡む場合はリスクが高まります。

```
メンテナンス ON
  ↓
マイグレーション実行 ← 失敗したら？
  ↓
ECS更新             ← 失敗したら？
  ↓
メンテナンス OFF
```

途中で失敗すると**メンテナンスモードが残ったままサイトがダウンし続ける**最悪のケースが起こり得ます。

| ケース | 推奨する対応 |
|---|---|
| スキーマ変更なし | スキルで自動化しても問題少ない |
| スキーマ変更あり | マネージャーが手動で確認しながら実施 |

現実的な落とし所として、スキルにスキーマ変更の有無をユーザーに確認するステップを入れ、変更ありの場合は手動対応に切り替える設計が安全です。

```yaml
## Step 0: スキーマ変更の確認

デプロイを開始する前に、ユーザーに以下を確認する。

「今回のデプロイにデータベースのスキーマ変更（マイグレーション）は含まれますか？
含まれる場合は、マイグレーションのタイミングと失敗時のロールバック手順を確認してから進めてください。」

スキーマ変更がある場合はデプロイを中断し、手動での対応を促す。
```

### IAMによる権限制御が本質的な安全策

スキルの `allowed-tools` による制限はClaude Code上の操作制限にすぎません。**AWS IAMで適切な権限を設定することが本質的な安全策**です。スキルとIAMを組み合わせて二重に制限することを推奨します。

## まとめ

Claude Codeのカスタムスキルを使うことで、複雑なデプロイ手順を `/deploy-eccube` の一言で実行できるようになります。

| 従来の方法 | スキルを使った場合 |
|---|---|
| ドキュメントを都度参照 | `/deploy-eccube` の一言で実行 |
| コマンドを手動で順番に実行 | 自動で順番に実行・確認 |
| チームによって手順がバラバラ | SKILL.md をGit管理してチームで統一 |
| ミスが起きやすい | 環境変数チェック等で事前確認 |

また、EC-CUBE本家リポジトリの追従には **Fork** ではなく **upstreamリモート** を使うことで、誤って本家にPull Requestを送るリスクをなくせます。ぜひ試してみてください！

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
