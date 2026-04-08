# EC-CUBEデバッグに費やす時間を9割削減した話——Claude Codeにログを渡すだけでよかった

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

「500エラーが出た。ログを見てもよくわからない」——EC-CUBE開発者なら誰もが経験する時間泥棒です。

**結論から言います。Claude Codeにログを渡すだけで、原因特定から修正まで自動でやってくれます。**
半日かかっていたデバッグが、文字通り数十秒で終わります。

この記事では、5つの実際のエラーパターンで Claude Code を使ったデバッグを実演します。コピペして使えるプロンプトも全部載せています。

## 「AIにログを渡して大丈夫？」という疑問に答える

正直に言います。本番のログには**個人情報（メールアドレス・注文情報）やDB接続情報が含まれることがあります**。そのまま渡すのは避けるべきです。

以下の点を意識してください。

- **開発・ステージング環境のログを使う**のが基本
- 本番ログを使う場合は、個人情報が含まれる行を確認・除去してから渡す
- Claude Codeはローカルで動作するため、クラウドに自動送信されることはないが、AI処理のためにデータが送信される点を念頭に置く

⚠️ 本番ログをそのままAIサービスに送信する前に、顧客の個人情報・DBパスワードなどの機密情報が含まれていないか確認してください。ローカル環境のログや、機密情報を除去したログの使用を推奨します。

このワンクッションを踏めば、Claude Codeはデバッグの最強の相棒になります。

---

## Claude Codeにログを渡す基本の方法

### ① ログの末尾をコピーして渡す

ターミナルでログの末尾を確認し、Claude Code のプロンプトに貼り付けます。

```bash
# 本番: サイト全体のログ（最新50行）
tail -50 var/log/prod/site.log

# 本番: フロント/管理画面別のログ
tail -50 var/log/prod/front.log
tail -50 var/log/prod/admin.log

# 開発: リアルタイムで確認
tail -f var/log/dev/site.log
```

ℹ️ EC-CUBE 4.3 では `rotating_file` ハンドラーを使用しているため、ファイル名に日付が付きます（例: `site-2026-03-30.log`）。最新ファイルを確認する場合は `ls -lt var/log/prod/` で日付を確認してください。

### ② Claude Code のプロジェクト内で直接指示する（推奨）

プロジェクトのルートで Claude Code を起動している場合、ファイルパスを指定するだけでログを自動で読み込んで解析します。

```
> var/log/prod/site.log を確認して、最新のエラーの原因を特定して修正して
```

Claude Code はログファイルを読み、関連するソースコードも自動で参照しながら修正します。

---

## よくあるエラーパターンと Claude Code の活用法

### パターン1：500エラー（原因不明）

**症状:** フロント・管理画面に「システムエラーが発生しました」と表示される。

**まずデバッグモードを有効化する（ローカル開発環境のみ）:**

```bash
# .env を編集
APP_ENV=dev
APP_DEBUG=1
```

⚠️ `APP_DEBUG=1` は**本番環境では絶対に有効にしないでください**。エラーの詳細（ファイルパス・DB情報など）が画面に表示されセキュリティリスクになります。

**Claude Code への指示:**

```
> var/log/prod/site.log の末尾50行を確認して、500エラーの原因を特定して
```

**ログの例と Claude Code の解析:**

```
[2026-03-01 10:23:45] prod.CRITICAL: Uncaught PHP Exception
Symfony\Component\HttpKernel\Exception\NotFoundHttpException:
"No route found for "GET /admin/secret-path""
```

Claude Code はこのログを見て「ルートが見つからない → `ECCUBE_ADMIN_ROUTE` の設定値と実際のリクエストパスが一致していない」と特定し、`.env` の修正まで提案します。

---

### パターン2：DB接続エラー

**症状:** 画面が真っ白になる、または「接続できません」エラー。

**Claude Code への指示:**

```
> var/log/prod/site.log にDB接続エラーが出ている。.env の DATABASE_URL と
  MySQL の設定を確認して原因を特定して
```

**よくある原因と Claude Code の対処:**

| ログのキーワード | 原因 | Claude Code が提案する修正 |
|---|---|---|
| `SQLSTATE[HY000] [2002]` | MySQLが起動していない | `sudo systemctl start mysql` |
| `Access denied for user` | DBユーザー・パスワード誤り | `.env` の `DATABASE_URL` を修正 |
| `Unknown database` | DB名が存在しない | DB作成コマンドを提案 |
| `Too many connections` | 接続数上限 | `max_connections` の見直しを提案 |

```
> var/log/prod/site.log を見て。SQLSTATE エラーが出ているので
  原因を特定して .env の修正方法を教えて
```

---

### パターン3：プラグイン競合・インストール後の500エラー

**症状:** プラグインを有効化したら画面が壊れた。

EC-CUBE 4では、プラグインのコードに問題があっても管理画面から無効化できなくなることがあります。

**Claude Code への指示:**

```
> プラグインを有効化したら500エラーになった。
  var/log/prod/site.log を確認して原因のプラグインと修正方法を教えて
```

**強制無効化の流れを Claude Code に任せる:**

```
> AcmePlugin を強制的に無効化したい。
  DBのプラグインテーブルを直接更新する方法を教えて
```

Claude Code は以下のような修正を提案します。

```sql
-- 実行前に必ずバックアップを取得すること
-- まずSELECTで対象を確認してからUPDATEする
SELECT id, code, enabled FROM dtb_plugin WHERE code = 'AcmePlugin';

-- 対象を確認したらUPDATEを実行
UPDATE dtb_plugin SET enabled = 0 WHERE code = 'AcmePlugin';
```

```bash
# キャッシュをクリアして動作確認
php bin/console cache:clear --env=prod --no-debug
```

---

### パターン4：キャッシュ関連のエラー

**症状:** コードを修正したのに反映されない、またはキャッシュ生成でエラー。

```
> デプロイ後に画面が更新されない。キャッシュ関連の問題を調査して修正して
```

Claude Code が実行する典型的な手順：

```bash
# キャッシュの強制クリア
php bin/console cache:clear --env=prod --no-debug

# キャッシュディレクトリの権限確認・修正
ls -la var/cache/
# 755（所有者のみ書き込み）が安全。共用サーバーでは特に775を避けること
chmod -R 755 var/cache/
chown -R eccube-admin:www-data var/cache/
```

---

### パターン5：メモリ不足・タイムアウト

**症状:** 大量データのCSVインポートや一括処理でエラー。

**ログの例:**

```
[2026-03-01 14:00:00] prod.ERROR: Allowed memory size of 134217728 bytes exhausted
```

```
> var/log/prod/site.log にメモリ不足エラーが出ている。
  原因を特定して php.ini または bin/console の設定で解決する方法を教えて
```

Claude Code の提案例：

```bash
# コンソールコマンド実行時のメモリ上限を引き上げる
php -d memory_limit=512M bin/console eccube:xxxxxx

# または php.ini を修正
memory_limit = 512M
```

---

## Claude Code を使った体系的なデバッグフロー

手順をまとめると以下のようになります。

```
1. エラー発生
   ↓
2. Claude Code に指示
   「var/log/prod/site.log の最新エラーを確認して原因を特定して」
   ↓
3. Claude Code がログ + ソースコードを横断解析
   ↓
4. 原因特定 + 修正案の提示
   ↓
5. 修正を適用（Claude Code が自動でファイルを編集）
   ↓
6. キャッシュクリア + 動作確認
```

### 複数のログを同時に解析させる

```
> 以下を同時に確認して、500エラーの根本原因を特定して：
  - var/log/prod/site.log（アプリログ）
  - var/log/prod/front.log（フロントログ）
  - /var/log/nginx/eccube_error.log（Nginxログ）
```

---

## デバッグ効率を上げる CLAUDE.md の設定

プロジェクトルートの `CLAUDE.md` にデバッグ情報を記載しておくと、毎回説明する手間が省けます。

```markdown
# CLAUDE.md

## ログファイルの場所（EC-CUBE 4.3）
- 本番アプリログ: var/log/prod/site.log（rotating_file、日付付き）
- 本番フロントログ: var/log/prod/front.log
- 本番管理画面ログ: var/log/prod/admin.log
- 開発ログ: var/log/dev/site.log
- Nginxログ: /var/log/nginx/eccube_error.log
- MySQLログ: /var/log/mysql/error.log

## よく使うデバッグコマンド
- キャッシュクリア: php bin/console cache:clear --env=prod --no-debug
- ルート一覧: php bin/console debug:router
- サービス一覧: php bin/console debug:container

## 本番環境の注意事項
- APP_DEBUG=1 は絶対に本番で有効にしない
- DB操作前は必ずバックアップを取る
```

---

## まとめ

| エラーパターン | Claude Code への指示 |
|---|---|
| 500エラー（原因不明） | `var/log/prod/site.log の末尾を確認してエラーの原因を特定して` |
| DB接続エラー | `SQLSTATE エラーを解析して .env の修正方法を教えて` |
| プラグイン競合 | `プラグイン有効化後の500エラーを調査して強制無効化する方法を教えて` |
| キャッシュ問題 | `デプロイ後に画面が更新されない原因を調査して修正して` |
| メモリ不足 | `メモリ不足エラーを解析してphp.iniの設定変更を提案して` |

「ログを見てもよくわからない」はもう過去の話です。Claude Codeにログを渡して、デバッグの時間を開発に使いましょう。

ℹ️ **この記事の要約（シェア用）**
ℹ️ EC-CUBEの500エラー、Claude Codeに `var/log/prod/site.log を確認して原因を特定して修正して` と伝えるだけで解決できます。デバッグに費やす時間を開発に使いましょう。

あなたはEC-CUBEのデバッグにどのくらい時間を使っていますか？Claude Codeを使い始めて変わったことがあれば、ぜひコメントで教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---