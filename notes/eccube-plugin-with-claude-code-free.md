# Claude CodeでEC-CUBEプラグインを爆速開発する方法

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

AI を活用したコーディングツールが急速に進化しています。この記事では、Anthropic が提供する **Claude Code** を使って EC-CUBE プラグインを効率的に開発する方法を紹介します。

## Claude Code とは

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) は、Anthropic が提供するターミナルベースの AI コーディングアシスタントです。

主な特徴：
- ターミナルで直接動作
- コードベース全体を理解
- ファイルの読み書き、コマンド実行が可能
- Git 操作もサポート

## EC-CUBE プラグイン開発での活用

### 1. プラグインの雛形生成

Claude Code に指示するだけで、プラグインの基本構造を生成できます。


Claude Code は以下のファイルを自動生成します：

- `Plugin.php` - プラグインのメインクラス
- `Entity/CustomerRank.php` - 会員ランクエンティティ
- `Repository/CustomerRankRepository.php` - リポジトリ
- `Controller/Admin/CustomerRankController.php` - 管理画面
- `Form/Type/Admin/CustomerRankType.php` - フォーム
- `Resource/template/` - Twig テンプレート
- `composer.json` - 依存関係

### 2. 既存コードの理解

EC-CUBE のコアコードを理解するのにも役立ちます。


Claude Code は EC-CUBE のソースコードを読み込み、処理の流れを解説してくれます。

### 3. カスタマイズの実装

既存機能のカスタマイズも指示するだけで実装できます。