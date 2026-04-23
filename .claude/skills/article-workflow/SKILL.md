---
name: article
description: EC-CUBE/Symfony関連の技術記事を作成する。事前調査チームが一次ソースを確認してから執筆し、専門レビューチームが精度を担保する。
---

# 記事作成ワークフロー

あなたは技術記事作成のオーケストレーターです。以下のワークフローに従って記事を作成してください。

## 引数

`$ARGUMENTS` には記事のテーマが渡されます。例：「Twig 3.24の新機能」「EC-CUBEのセキュリティ対策」

---

## ワークフロー

### Step 1: 事前調査（並列・必須）

**⚠️ 重要: WebSearchのAI要約は一次ソースとして使わない。必ず公式リポジトリ・ドキュメントを直接確認すること。**

以下の2つのAgentを**同時に**起動して調査します：

```
Agent 1: EC-CUBEソース調査員
- subagent_type: general-purpose
- prompt: |
    以下のテーマについて、EC-CUBE 4.3 の実装を調査してください。

    テーマ: {$ARGUMENTS}

    調査先（必ずGitHubのソースコードを直接確認すること）:
    - https://github.com/EC-CUBE/ec-cube（ソースコード・PR・Issues）
    - https://doc4.ec-cube.net/（公式ドキュメント）

    確認すること:
    - テーマに関連するEC-CUBEのクラス名・メソッド名・ファイルパスの正確な記述
    - EC-CUBE 4.3 での実際の動作（composer.json のバージョン確認を含む）
    - 関連するPR・Issuesの状況
    - WebSearchのAI要約は使わず、必ずWebFetchで実際のページを確認すること

    調査結果を事実のみ箇条書きで報告してください。不明な点は「確認できなかった」と明記してください。

Agent 2: Symfony/ライブラリバージョン調査員
- subagent_type: general-purpose
- prompt: |
    以下のテーマについて、Symfony・Doctrine等のライブラリの仕様を調査してください。

    テーマ: {$ARGUMENTS}

    EC-CUBE 4.3 の依存バージョン:
    - Symfony: ^6.4
    - Doctrine ORM: ^2.14 || ^3.0
    - Doctrine DBAL: ^3.3
    - PHP: ^8.1

    調査先（必ずGitHubのソースコードまたは公式ドキュメントを直接確認すること）:
    - https://github.com/symfony/symfony
    - https://github.com/doctrine/orm
    - https://github.com/doctrine/dbal
    - https://symfony.com/doc/current/

    確認すること:
    - テーマに関連するAPIの正確なシグネチャ・使い方
    - EC-CUBE 4.3 が使うバージョンでの動作（非推奨・削除されたAPIを含む）
    - WebSearchのAI要約は使わず、必ずWebFetchで実際のページを確認すること

    調査結果を事実のみ箇条書きで報告してください。不明な点は「確認できなかった」と明記してください。
```

### Step 2: 下書き作成

**Step 1の調査結果のみを根拠として**記事を作成します。調査で確認できなかった情報は記事に含めないか、「未確認」と明記します。

**ファイル配置:**
- `articles/` ディレクトリに作成
- ファイル名: 半角英数字とハイフンのみ（12〜50文字）

**フロントマター:**
```yaml
---
title: "記事タイトル（最大70文字）"
emoji: "適切な絵文字"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: false
---
```

**冒頭のブロック（必須・順番厳守）:**
```markdown
:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::
```

**末尾のCTA（必須）:**
```markdown
---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
```

### Step 3: 専門レビュー（並列）

下書き完成後、以下の3つのAgentを**同時に**起動します：

```
Agent 1: EC-CUBE/Symfonyファクトチェッカー
- subagent_type: general-purpose
- prompt: |
    以下の記事のすべての技術的な事実をチェックしてください。

    記事パス: {記事のパス}

    チェック方法（必ずGitHubのソースを直接確認すること）:
    - コード例のクラス名・メソッド名・シグネチャを EC-CUBE/Symfony の実際のソースで確認
    - ファイルパス・設定ファイルの場所を実際のリポジトリ構造で確認
    - バージョン固有の動作（非推奨API等）を当該バージョンのソースで確認
    - CLIコマンドの存在と正確な引数をソースで確認

    確認先:
    - https://github.com/EC-CUBE/ec-cube
    - https://github.com/symfony/symfony
    - https://github.com/doctrine/orm
    - https://github.com/doctrine/dbal

    誤りがあれば行番号と修正案を示してください。
    確認できなかった箇所も明記してください。

Agent 2: セキュリティレビュアー
- subagent_type: general-purpose
- prompt: |
    以下の記事のセキュリティ観点でのチェックをしてください。

    記事パス: {記事のパス}

    チェックポイント:
    - 脆弱性を生むコード例がないか（SQLインジェクション・XSS・CSRF等）
    - セキュリティのベストプラクティスに従っているか
    - 危険なコマンド・設定を注意書きなしに推奨していないか
    - 本番環境で使うと問題になる設定（APP_DEBUG=1等）への警告があるか
    - 機密情報・個人情報が含まれていないか

    問題があれば具体的な修正案を提示してください。

    記事パス: {記事のパス}

Agent 3: バズ改善提案
- subagent_type: general-purpose
- prompt: |
    以下の記事をよりバズりやすくする改善案を提案してください。

    チェックポイント:
    - タイトルにインパクトがあるか（数字・問いかけ・対立構造・読者の痛みへの言及）
    - 冒頭で結論を先に書いているか（PREP法）
    - 読者の「自分事」として感じられる導入か
    - SNSでシェアされやすいTL;DRがあるか
    - 議論を誘発する問いかけがあるか

    具体的な改善案（タイトル案3つ・冒頭の書き直し案）を提示してください。

    記事パス: {記事のパス}
```

### Step 4: フィードバック統合

3つのレビュー結果を統合して記事を改善します。

- ファクトチェックの指摘 → **必ず修正**（確認できない情報は削除または「未確認」と明記）
- セキュリティの指摘 → **必ず修正**
- バズ改善提案 → タイトルと冒頭は採用、その他は適宜判断

### Step 5: PR作成

```bash
git checkout -b article/{スラッグ}
git add articles/{ファイル名}
git commit -m "Add article about {テーマ}"
git push -u origin article/{スラッグ}
gh pr create --title "{記事タイトル}" --body "..."
```

### Step 6: 完了報告

ユーザーに以下を報告します：

- PRのURL
- 記事の概要
- 事前調査で判明した重要な事実
- 3つのレビューで指摘された主な点と対応内容

---

## 絶対に守るルール

- `published: false` で作成する（公開はユーザーが判断）
- **タイトルは最大70文字**（Zennの上限。超えると公開時エラーになる）
- **WebSearchのAI要約を事実の根拠にしない**。必ずWebFetchで一次ソースを確認する
- 確認できなかった情報は記事に含めない
- EC-CUBE 4.3（Symfony 6.4・DBAL 3.x）での動作を前提とする
- コード例は実際のソースコードで確認したもののみ記載する
- **文体はです・ます調で統一する**（だ・である調は使わない）
