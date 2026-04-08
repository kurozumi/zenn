# Claude CodeでEC-CUBEのissueを解決してPRを送る方法

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBE はオープンソースのECパッケージです。GitHub で issue が公開されており、誰でもコントリビュートできます。この記事では、Claude Code を使って issue を解決し、プルリクエストを送るまでの流れを解説します。

## 前提条件

- GitHub アカウント
- Claude Code がインストール済み
- GitHub CLI（gh コマンド）がインストール済み
- PHP 8.1 以上、Composer がインストール済み

## GitHub CLI のセットアップ

この記事では GitHub CLI（`gh` コマンド）を使用します。ターミナルから GitHub の操作（issue の確認、PR の作成など）ができる公式ツールです。

### インストール

```bash
# macOS（Homebrew）
brew install gh

# Windows（winget）
winget install GitHub.cli

# Ubuntu/Debian
sudo apt install gh
```

その他の環境は [公式ドキュメント](https://cli.github.com/manual/installation) を参照してください。

### 認証

インストール後、GitHub アカウントでログインします。

```bash
gh auth login
```

対話形式で進みます。HTTPS と SSH のどちらかを選び、ブラウザで認証を完了させてください。

### 動作確認

```bash
gh --version
gh auth status
```

`Logged in to github.com` と表示されれば準備完了です。