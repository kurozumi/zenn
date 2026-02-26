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
- PHP 8.1 以上、Composer がインストール済み

## 全体の流れ

1. issue を選ぶ
2. リポジトリをフォーク・クローン
3. 該当コードを特定
4. 修正を実装
5. テスト
6. PR を作成

## 1. issue を選ぶ

まず、EC-CUBE の issue 一覧を確認します。

```bash
gh issue list --repo EC-CUBE/ec-cube --state open --limit 20
```

`good-first-issue` ラベルが付いている issue は、初めてのコントリビュートに適しています。

```bash
gh issue list --repo EC-CUBE/ec-cube --label "good-first-issue" --state open
```

### 具体例：issue #6582

今回は以下の issue を例に進めます。

```bash
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

issue には該当ファイルとコードの場所が記載されています。

## 2. リポジトリをフォーク・クローン

### フォーク

GitHub で EC-CUBE リポジトリをフォークします。

```bash
gh repo fork EC-CUBE/ec-cube --clone
cd ec-cube
```

### ブランチ作成

issue 番号を含むブランチ名にすると管理しやすいです。

```bash
git checkout -b fix/6582-duplicate-data-bs-toggle
```

## 3. Claude Code で該当コードを特定

Claude Code を起動して、issue の内容を伝えます。

```
claude
```

### プロンプト例

```
issue #6582 の内容:
- 出荷登録画面の「出荷情報を削除」ボタンで data-bs-toggle が重複している
- src/Eccube/Resource/template/admin/Order/shipping.twig の247行目付近

該当コードを確認して、修正方法を提案してください。
```

### Claude Code の応答例

Claude Code がファイルを読み込み、問題を特定します。

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

`data-bs-toggle` 属性が2回指定されており、後から書いた `tooltip` が無視されています。

## 4. 修正を実装

Claude Code に修正を依頼します。

### プロンプト例

```
この問題を修正してください。Bootstrap 5 では data-bs-toggle は1つの要素に1つしか
指定できないので、tooltip は別のアプローチが必要です。
```

### 修正方法

Bootstrap 5 では、モーダルとツールチップを同時に使う場合、ボタンを `<span>` でラップしてツールチップを外側に付けるパターンがあります。

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

または、JavaScript で tooltip を初期化する方法もあります。

```twig
{# 別の修正方法: data-tooltip 属性を使用 #}
<button type="button"
        class="btn btn-ec-actionIcon"
        data-bs-toggle="modal"
        data-bs-target="#simpleModal"
        data-tooltip="tooltip"
        title="{{ 'admin.order.delete_shipping_label'|trans }}">
    <i class="fa fa-trash"></i>
</button>
```

```javascript
// JavaScript で初期化
document.querySelectorAll('[data-tooltip="tooltip"]').forEach(el => {
    new bootstrap.Tooltip(el);
});
```

### Claude Code で編集

Claude Code の Edit 機能を使って直接ファイルを編集できます。

```
shipping.twig の247行目付近を修正してください。
span でラップするアプローチで実装してください。
```

## 5. 動作確認

### EC-CUBE の起動

```bash
# 依存関係のインストール
composer install

# データベースのセットアップ（SQLite を使用）
bin/console eccube:install --no-interaction

# 開発サーバー起動
symfony server:start
```

### 確認項目

1. 管理画面にログイン
2. 受注管理 → 出荷登録画面を開く
3. 「出荷情報を削除」ボタンにホバーしてツールチップが表示されるか確認
4. ボタンをクリックしてモーダルが開くか確認

## 6. コミットと PR 作成

### コミット

```bash
git add src/Eccube/Resource/template/admin/Order/shipping.twig
git commit -m "Fix duplicate data-bs-toggle attribute on shipping delete button

refs #6582"
```

コミットメッセージに `refs #6582` を含めると、GitHub で issue と自動的にリンクされます。

### プッシュ

```bash
git push -u origin fix/6582-duplicate-data-bs-toggle
```

### PR 作成

```bash
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

## 関連 issue

refs #6582
EOF
)"
```

## Claude Code 活用のコツ

### 1. issue の内容をそのまま伝える

```
以下のissueを修正したい:
[issue の内容をコピペ]

該当ファイルを読んで、修正方法を提案してください。
```

### 2. EC-CUBE のコーディング規約を意識させる

```
EC-CUBE のコーディング規約に従って修正してください。
既存のコードスタイルに合わせてください。
```

### 3. 影響範囲を確認させる

```
この修正が他の画面に影響しないか確認してください。
同じパターンが使われている箇所を検索してください。
```

```bash
# Claude Code が実行するコマンド例
grep -r "data-bs-toggle=\"modal\"" --include="*.twig" src/
```

### 4. テストコードの有無を確認

```
この機能に関連するテストコードはありますか？
テストを追加する必要がありますか？
```

## よくある issue のパターン

### 多言語化対応

```twig
{# Before: ハードコード #}
<button onclick="return confirm('削除してもよろしいですか？')">

{# After: trans フィルター使用 #}
<button onclick="return confirm('{{ 'common.delete_confirm'|trans }}')">
```

翻訳キーは `src/Eccube/Resource/locale/messages.ja.yaml` に追加します。

### Twig テンプレートの修正

```twig
{# エスケープ漏れの修正 #}
{# Before #}
{{ variable|raw }}

{# After #}
{{ variable }}
```

### JavaScript の修正

```javascript
// jQuery から Vanilla JS への移行
// Before
$('#element').on('click', function() {});

// After
document.getElementById('element').addEventListener('click', function() {});
```

## PR がマージされるまで

1. **CI チェック**: GitHub Actions でテストが実行される
2. **レビュー**: メンテナーからフィードバックがある場合は対応
3. **マージ**: 承認されるとマージされる

### レビュー対応のコツ

レビューコメントが付いたら、Claude Code に相談できます。

```
レビューで以下のコメントをもらいました:
[コメント内容]

どう対応すべきですか？
```

## まとめ

| ステップ | Claude Code の活用 |
|---------|-------------------|
| issue 調査 | `gh issue view` で内容確認 |
| コード特定 | Grep/Read で該当箇所を検索 |
| 修正実装 | Edit で直接編集 |
| 影響調査 | 同じパターンの検索 |
| PR 作成 | `gh pr create` でテンプレート生成 |

Claude Code を使うことで、コードの調査から PR 作成までをスムーズに進められます。まずは `good-first-issue` から始めて、EC-CUBE のコントリビュートに挑戦してみてください。

## 参考リンク

- [EC-CUBE GitHub](https://github.com/EC-CUBE/ec-cube)
- [EC-CUBE 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [EC-CUBE コントリビューションガイド](https://github.com/EC-CUBE/ec-cube/blob/4.3/CONTRIBUTING.md)
