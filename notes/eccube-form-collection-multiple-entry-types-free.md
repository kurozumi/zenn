# EC-CUBEプラグインで「ブロックごとに異なるフォーム」をCollectionTypeで実装する

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

「テキストブロック・画像ブロック・ボタンブロックをひとつのコレクションで管理したい」——EC-CUBEのコンテンツ管理プラグインや商品オプション実装で、こういった要件に直面したことはありませんか？

現在の Symfony `CollectionType` は**全アイテムに同一の FormType**しか使えません。これを無理やり実装しようとすると、JavaScript や hidden フィールドで型を判定するハック的なコードが生まれます。

Symfony PR [#63487](https://github.com/symfony/symfony/pull/63487) では `entry_types` オプションが追加され、**アイテムごとに異なる FormType を使えるようになります**。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - 現在の `CollectionType` は `entry_type`（単数）で全アイテムに同一 FormType しか使えない
ℹ️ - PR #63487（Symfony 8.1向け）で `entry_types`（複数）オプションが追加される
ℹ️ - `EntryTypeProviderInterface` でデータに応じて型を切り替える
ℹ️ - EC-CUBE のコンテンツ管理・商品オプション・BtoB 受発注などポリモーフィックなフォームに有用