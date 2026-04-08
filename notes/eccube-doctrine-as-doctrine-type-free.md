# 「登録し忘れて実行時エラー」から解放される！Symfony #[AsDoctrineType] 属性とEC-CUBEプラグイン開発

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。


EC-CUBEプラグインでカスタムDoctrineタイプを使うとき、毎回 `doctrine.yaml` に手動で登録していませんか？

登録し忘れると実行時エラー。タイプが増えるたびにYAMLが肥大化。地味に面倒なこの作業が、**属性1行で消える日が来るかもしれません。**

Symfonyのプルリクエスト **[#63774: [DoctrineBridge] Allow custom doctrine type registration using attribute](https://github.com/symfony/symfony/pull/63774)** で提案されている `#[AsDoctrineType]` 属性がそれです。まだレビュー中ですが、EC-CUBEプラグイン開発に関わる人なら知っておく価値があります。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - Symfonyに `#[AsDoctrineType]` 属性を追加するPRが進行中
ℹ️ - 実現すれば `doctrine.yaml` へのタイプ登録が不要になる
ℹ️ - EC-CUBE 4.3（Symfony 6.4ベース）では現時点で使えないが、将来の移行準備として知っておく価値あり

## 現状：カスタムDoctrineタイプの登録が面倒

EC-CUBEプラグインでカスタムDoctrineタイプを使う場合、現在は**2つのファイルを編集する必要があります**。

### ① カスタムタイプクラスを作成


### ② doctrine.yaml に手動で登録


タイプが増えるたびに `doctrine.yaml` への追記が必要で、登録し忘れて実行時エラーになることも。

---

## PR #63774 で何が変わるか

`#[AsDoctrineType]` 属性をクラスに付けるだけで、**自動的にDoctrine DBALに登録**されるようになります。


`name` パラメータを省略すると、完全修飾クラス名がタイプ名になります。


---