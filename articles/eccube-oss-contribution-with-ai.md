---
title: "Claude CodeでEC-CUBEのissueを解決してPRを送る方法"
emoji: "🔧"
type: "tech"
topics: ["eccube", "eccube4", "php", "oss", "ai"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

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

## 全体の流れ

1. CLAUDE.md を準備（初回のみ）
2. issue を選ぶ
3. worktree でブランチを作成
4. Claude Code に修正を依頼
5. PR を作成（プロンプトで指示するだけ）

## 1. CLAUDE.md を準備する（初回のみ）

Claude Code はプロジェクトルートの `CLAUDE.md` を読み込んで、プロジェクト固有のルールを理解します。EC-CUBE へのコントリビュート用に CLAUDE.md を作成しておくと、毎回指示しなくても適切な PR を作成してくれます。

### フォークとクローン

```bash
gh repo fork EC-CUBE/ec-cube --clone
cd ec-cube
```

### upstream の設定

```bash
git remote add upstream https://github.com/EC-CUBE/ec-cube.git
```

### CLAUDE.md の作成

```bash
cat > CLAUDE.md << 'EOF'
# EC-CUBE コントリビューションガイド

## コミットメッセージ

- 英語で記述
- 末尾に `refs #issue番号` を含める
- Co-Authored-By は不要

## PR 作成

- `--repo EC-CUBE/ec-cube` を指定してフォーク元にPRを送る
- タイトルは日本語でOK
- 本文に以下を含める:
  - 概要
  - 変更内容
  - 確認方法
  - `refs #issue番号`

## コーディング規約

- PSR-12 準拠
- 既存のコードスタイルに合わせる
- Twig テンプレートは EC-CUBE の既存パターンに従う
EOF
```

これで Claude Code が EC-CUBE のコントリビュートルールを理解した状態で作業できます。

## 2. issue を選ぶ

Claude Code を起動して issue を確認します。

```bash
claude
```

プロンプトで指示するだけで、Claude Code が gh コマンドを実行します。

### プロンプト例

```
EC-CUBE/ec-cube の open な issue を20件表示して
```

### Claude Code が実行するコマンド

```bash
gh issue list --repo EC-CUBE/ec-cube --state open --limit 20
```

`good-first-issue` ラベルが付いている issue は、初めてのコントリビュートに適しています。

```
good-first-issue ラベルの issue を表示して
```

```bash
# Claude Code が実行
gh issue list --repo EC-CUBE/ec-cube --label "good-first-issue" --state open
```

### 具体例：issue #6582

```
issue #6582 の詳細を見せて
```

```bash
# Claude Code が実行
gh issue view 6582 --repo EC-CUBE/ec-cube
```

```
title:  出荷登録画面 data-bs-toggleが重複しているタグがある
state:  OPEN
labels: bug

### 概要
「出荷情報を削除」ボタンで data-bs-toggle="modal" と data-bs-toggle="tooltip" が
重複しており、tooltip が動作していない。

### 該当ファイル
src/Eccube/Resource/template/admin/Order/shipping.twig#L247
```

## 3. worktree でブランチを作成

複数の issue を並行して作業する場合、`git worktree` が便利です。ブランチごとに別のディレクトリで作業できます。

### 最新の main を取得

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### worktree でブランチを作成

```bash
# worktree 用のディレクトリを作成
mkdir -p ../ec-cube-worktrees

# issue #6582 用の worktree を作成
git worktree add ../ec-cube-worktrees/fix-6582 -b fix/6582-duplicate-data-bs-toggle
```

### CLAUDE.md をシンボリックリンク

worktree で作成したディレクトリには CLAUDE.md がありません。main ブランチの CLAUDE.md をシンボリックリンクすると、どの worktree でも同じルールで作業できます。

```bash
cd ../ec-cube-worktrees/fix-6582
ln -s ../../ec-cube/CLAUDE.md CLAUDE.md
```

:::message
シンボリックリンクにすることで、CLAUDE.md を更新したときにすべての worktree に反映されます。
:::

### worktree の一覧確認

```bash
git worktree list
```

```
/path/to/ec-cube                          abc1234 [main]
/path/to/ec-cube-worktrees/fix-6582       def5678 [fix/6582-duplicate-data-bs-toggle]
```

## 4. Claude Code に修正を依頼

worktree のディレクトリで Claude Code を起動します。

```bash
cd ../ec-cube-worktrees/fix-6582
claude
```

### プロンプト例

```
issue #6582 を修正して。

内容:
- 出荷登録画面の「出荷情報を削除」ボタンで data-bs-toggle が重複している
- src/Eccube/Resource/template/admin/Order/shipping.twig の247行目付近
```

Claude Code が自動的に以下を実行します：

1. **ファイルを読み込み**
2. **問題を特定**
3. **修正を実装**

### Claude Code の動作例

```bash
# Claude Code が実行するコマンド（Read ツール）
# shipping.twig を読み込んで問題箇所を確認
```

```twig
{# 問題のあるコード #}
<button type="button"
        class="btn btn-ec-actionIcon"
        data-bs-toggle="modal"
        data-bs-toggle="tooltip"
        data-bs-target="#simpleModal"
        title="{{ 'admin.order.delete_shipping_label'|trans }}">
    <i class="fa fa-trash"></i>
</button>
```

Claude Code が問題を特定し、修正案を提示します。

```twig
{# 修正後のコード #}
<span data-bs-toggle="tooltip" title="{{ 'admin.order.delete_shipping_label'|trans }}">
    <button type="button"
            class="btn btn-ec-actionIcon"
            data-bs-toggle="modal"
            data-bs-target="#simpleModal">
        <i class="fa fa-trash"></i>
    </button>
</span>
```

Bootstrap 5 では `data-bs-toggle` は1つの要素に1つしか指定できないため、ボタンを `<span>` でラップしてツールチップを外側に付けます。

## 5. PR を作成（プロンプトで指示するだけ）

修正が完了したら、プロンプトで PR 作成を指示するだけです。

### プロンプト例

```
この修正をコミットして PR を作成して
```

**これだけで OK です。** Claude Code が CLAUDE.md のルールに従って、以下を自動実行します。

### Claude Code が実行するコマンド

```bash
# 変更をステージング
git add src/Eccube/Resource/template/admin/Order/shipping.twig

# コミット（CLAUDE.md のルールに従って英語 + refs #issue番号）
git commit -m "Fix duplicate data-bs-toggle attribute on shipping delete button

refs #6582"

# プッシュ
git push -u origin fix/6582-duplicate-data-bs-toggle

# PR 作成（CLAUDE.md のルールに従って --repo EC-CUBE/ec-cube を指定）
gh pr create --repo EC-CUBE/ec-cube --title "出荷登録画面のdata-bs-toggle重複を修正" --body "$(cat <<'EOF'
## 概要

出荷登録画面の「出荷情報を削除」ボタンで `data-bs-toggle` 属性が重複しており、
ツールチップが動作していない問題を修正しました。

## 変更内容

- ボタンを `<span>` でラップし、ツールチップは外側の要素に付与
- モーダルトリガーはボタン要素に残す

## 確認方法

1. 管理画面 > 受注管理 > 出荷登録画面を開く
2. 「出荷情報を削除」ボタンにホバー → ツールチップが表示される
3. ボタンをクリック → モーダルが開く

refs #6582
EOF
)"
```

CLAUDE.md にルールを書いておくことで、毎回細かく指示しなくても適切な PR が作成されます。

## worktree の後片付け

PR がマージされたら、worktree を削除します。

```bash
# worktree を削除
git worktree remove ../ec-cube-worktrees/fix-6582

# ブランチも削除
git branch -d fix/6582-duplicate-data-bs-toggle
```

## CLAUDE.md をさらに充実させる

プロジェクトに慣れてきたら、CLAUDE.md に追加のルールを書いておくとさらに便利です。

```markdown
# EC-CUBE コントリビューションガイド

## コミットメッセージ

- 英語で記述
- 末尾に `refs #issue番号` を含める
- Co-Authored-By は不要

## PR 作成

- `--repo EC-CUBE/ec-cube` を指定してフォーク元にPRを送る
- タイトルは日本語でOK
- 本文に以下を含める:
  - 概要
  - 変更内容
  - 確認方法
  - `refs #issue番号`

## コーディング規約

- PSR-12 準拠
- 既存のコードスタイルに合わせる
- Twig テンプレートは EC-CUBE の既存パターンに従う

## よくある修正パターン

### 多言語化対応

ハードコードされた日本語は `|trans` フィルターを使う。
翻訳キーは `src/Eccube/Resource/locale/messages.ja.yaml` に追加。

### data-bs-toggle の重複

Bootstrap 5 では1要素に1つまで。
モーダル + ツールチップの場合は span でラップする。

## テスト

- 修正したら必ず動作確認の手順を PR に記載する
- 既存のテストが壊れていないか確認する
```

## まとめ

| ポイント | 効果 |
|---------|------|
| CLAUDE.md を準備 | 毎回指示しなくても適切な PR が作成される |
| worktree を使用 | 複数の issue を並行して作業できる |
| シンボリックリンク | すべての worktree で同じルールを適用 |
| プロンプトで指示 | コマンドを覚えなくても PR まで完了 |

Claude Code + CLAUDE.md + worktree の組み合わせで、EC-CUBE へのコントリビュートがスムーズになります。まずは `good-first-issue` から始めて、OSS コントリビュートに挑戦してみてください。

## 参考リンク

- [EC-CUBE GitHub](https://github.com/EC-CUBE/ec-cube)
- [EC-CUBE 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [EC-CUBE コントリビューションガイド](https://github.com/EC-CUBE/ec-cube/blob/4.3/CONTRIBUTING.md)
- [Git Worktree ドキュメント](https://git-scm.com/docs/git-worktree)

---

:::message alert
**EC-CUBEのカスタマイズをお待ちしております！**

EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。

この記事が役に立ったら、ぜひ**バッジを贈っていただけると励みになります！**
:::
