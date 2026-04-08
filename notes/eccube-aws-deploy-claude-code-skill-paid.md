## 必要なツールの準備

### 1. GitHub CLI

GitHub CLIは、コマンドラインからGitHubを操作するための公式ツールです。

**macOS（Homebrew）:**


**Linux（Ubuntu/Debian）:**


**Windows（winget）:**


インストール後、GitHubへの認証を行います。


### 2. AWS CLI

AWS CLIは、AWSサービスをコマンドラインで操作するツールです。

**macOS（Homebrew）:**


**Linux:**


**Windows:**


インストール後、AWSの認証情報を設定します。



### 3. Docker

デプロイスキルはローカルマシンで `docker build`（イメージのビルド）と `docker push`（ECRへのアップロード）を実行します。そのためローカルマシンへのDockerインストールが必要です。


**macOS / Windows:**

[Docker Desktop](https://www.docker.com/products/docker-desktop/) をインストールしてください。

**Linux:**


## EC-CUBEリポジトリのセットアップ

### Forkしない理由

EC-CUBEリポジトリを **Fork** して使う方法もありますが、以下のリスクがあります。

- GitHubの「Contribute」ボタンを誤ってクリックすると、本家リポジトリにPull Requestを送ってしまう
- Fork元と自分のリポジトリが紐づいているため、混乱が生じやすい

そこで、**Forkせずに `upstream` リモートで本家を追従する方法**を推奨します。

### セットアップ手順

**Step 1: GitHub上に空のプライベートリポジトリを作成する**


| オプション | 意味 |
|---|---|
| `--private` | リポジトリを非公開（プライベート）にする |
| `--clone` | 作成後にローカルへ自動でクローンする |

このコマンド1つで「リポジトリ作成 → プライベート設定 → ローカルにクローン」を同時に行います。`--clone` がない場合は別途 `git clone` が必要です。

**Step 2: EC-CUBE本家を `upstream` リモートとして追加する**


ℹ️ `--allow-unrelated-histories` が必要なのは**初回の1回だけ**です。`my-eccube`（空リポジトリ）と `upstream/4.3`（EC-CUBE本家）は共通の親コミットを持たないため、このオプションなしだと `fatal: refusing to merge unrelated histories` というエラーになります。一度マージすると共通の親ができるので、次回以降は不要です。

**Step 3: 本家の更新を取り込む（アップデート時）**


これで `upstream` が EC-CUBE本家、`origin` が自分のリポジトリと明確に分かれます。誤って本家にPull Requestを送るリスクがなくなります。


リモートの設定を確認する場合は以下のコマンドを使います。


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


### ECSクラスターの作成


### 本番用 Dockerfile の準備

AWS ECS（Fargate）はDockerコンテナで動作します。EC-CUBEのプロジェクトルートに本番用の `Dockerfile` を作成します。


### .dockerignore の作成

`COPY . .` を実行する前に、機密ファイルや不要ファイルがイメージに含まれないよう `.dockerignore` を作成します。



### 機密情報はAWSで管理する

`.env` をコンテナに含めない代わりに、AWS上の機密情報管理サービスを使います。

| サービス | 用途 |
|---|---|
| **AWS Systems Manager Parameter Store** | `DATABASE_URL`、`APP_SECRET`、`MAILER_DSN` などの設定値 |
| **AWS Secrets Manager** | 自動ローテーションが必要なDBパスワードやAPIキー |
| **IAM Role（ECS Task Role）** | S3へのファイルアップロードなどAWSリソースへのアクセス権限 |

ECSタスク定義でParameter StoreやSecrets Managerの値を参照することで、コンテナ起動時に自動で環境変数として注入されます。


Parameter Storeへの登録は以下のコマンドで行います。


### IAM ポリシーの設定

デプロイに使用するIAMユーザー/ロールには、以下の最小権限ポリシーを付与してください。


`AdministratorAccess` などの過剰な権限は付与しないようにしましょう。

## Claude Codeデプロイスキルの作成

### スキルファイルの作成

個人スキルとして作成します（すべてのプロジェクトで使えます）。


`~/.claude/skills/deploy-eccube/SKILL.md` を以下の内容で作成します。

bash
aws sts get-caller-identity
docker info --format '{{.ServerVersion}}'
git log --oneline -3
bash
echo "AWS_REGION:          ${AWS_REGION:-未設定}"
echo "ECR_REPOSITORY_URI:  ${ECR_REPOSITORY_URI:-未設定}"
echo "ECS_CLUSTER:         ${ECS_CLUSTER:-未設定}"
echo "ECS_SERVICE:         ${ECS_SERVICE:-未設定}"
bash
ECR_REGISTRY=$(echo ${ECR_REPOSITORY_URI} | cut -d/ -f1)
aws ecr get-login-password --region ${AWS_REGION} | \
  docker login --username AWS --password-stdin ${ECR_REGISTRY}
bash
IMAGE_TAG=$(git rev-parse --short HEAD)
docker build -t eccube:${IMAGE_TAG} .
docker tag eccube:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:${IMAGE_TAG}
docker tag eccube:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:latest
bash
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}
docker push ${ECR_REPOSITORY_URI}:latest
echo "プッシュ完了: ${ECR_REPOSITORY_URI}:${IMAGE_TAG}"
bash
aws ecs update-service \
  --cluster ${ECS_CLUSTER} \
  --service ${ECS_SERVICE} \
  --force-new-deployment \
  --region ${AWS_REGION}
echo "デプロイ開始"
bash
aws ecs wait services-stable \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --region ${AWS_REGION}
echo "デプロイ完了！"
bash
aws ecs describe-services \
  --cluster ${ECS_CLUSTER} \
  --services ${ECS_SERVICE} \
  --region ${AWS_REGION} \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
bash
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
`

### 環境変数の設定

スキルが参照する環境変数を `~/.bashrc` または `~/.zshrc` に追加します。


設定後、シェルを再読み込みします。



ℹ️ 実際のチーム運用では、**GitHub ActionsのCI/CDパイプラインをデプロイのトリガーにする**のがベストプラクティスです。mainブランチへのマージを契機に自動でデプロイが走る設計にすることで、テストをパスしたコードだけが本番に反映されます。
ℹ️ 
ℹ️ この記事のスキルは「概念の理解」や「緊急時の手動デプロイ」を想定しています。

## 使い方

すべての準備が整ったら、Claude Code内で以下のコマンドを実行します。


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

bash
git checkout -b feature/$ARGUMENTS
bash
git add .
git status
git commit -m "feat: $ARGUMENTS"
bash
git push -u origin HEAD
gh pr create --title "$ARGUMENTS" --body "## 変更内容\n\n"

`allowed-tools` に `Bash(aws *)` や `Bash(docker *)` を含めないことで、メンバーがAWS操作系のコマンドを実行できないよう制限できます。


### メンバーの参加方法

チームリポジトリ（`my-eccube`）はメンバー全員が書き込み権限を持っているので、**forkは不要**です。直接クローンしてブランチを切るだけです。

| 対象 | 方法 | 理由 |
|---|---|---|
| EC-CUBE本家 | upstream リモートで追従 | 書き込み権限がないため |
| チームの `my-eccube` | 直接クローン＆ブランチ | 書き込み権限があるため |


### スキルをGitで管理する

スキルをプロジェクトの `.claude/skills/` に配置してGitで管理することで、チームメンバー全員が同じスキルを使えるようになります。


## このスキルの限界

### メンテナンスモードの自動化はリスクがある

デプロイ中にメンテナンスモードを自動で ON/OFF することは技術的には可能ですが、**スキーマ変更（マイグレーション）が絡む場合は注意が必要**です。

スキーマ変更なしの通常デプロイであれば、以下の流れで自動化できます。


一方、マイグレーションが絡む場合はリスクが高まります。


途中で失敗すると**メンテナンスモードが残ったままサイトがダウンし続ける**最悪のケースが起こり得ます。

| ケース | 推奨する対応 |
|---|---|
| スキーマ変更なし | スキルで自動化しても問題少ない |
| スキーマ変更あり | マネージャーが手動で確認しながら実施 |

現実的な落とし所として、スキルにスキーマ変更の有無をユーザーに確認するステップを入れ、変更ありの場合は手動対応に切り替える設計が安全です。


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