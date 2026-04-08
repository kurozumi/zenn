# EC-CUBEの受注ステータス遷移図、コードを読まずに1コマンドで確認できる【workflow:dump】

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBEの受注ステータスを「キャンセル」に遷移させたのに、在庫が戻っていない——そんな経験はありませんか？

実は EC-CUBE の受注ステータス管理は **Symfony Workflow コンポーネント**で厳密に制御されており、「どの遷移で在庫が戻るか」「どの遷移でポイントが付与されるか」はすべてビジネスロジックとして定義されています。

これを知らないままカスタマイズすると、想定外の状態遷移でデータ不整合が起きます。これを防ぐ最短の方法が **`workflow:dump` コマンド**です。EC-CUBE 4.3 環境ならば今すぐ使えます。

ℹ️ **この記事のポイント（TL;DR）**
ℹ️ - EC-CUBEの受注ステータス管理はSymfony Workflowで実装されている
ℹ️ - `php bin/console workflow:dump order` で状態遷移図（Graphviz/PlantUML/Mermaid）を出力できる
ℹ️ - Symfony 8.1（PR #63809）では `--with-listeners` でイベントリスナーも図に含められる予定

## EC-CUBEの受注ステータスはSymfony Workflowで管理されている

EC-CUBE 4.3 の受注ステータス管理は、Symfonyの **Workflowコンポーネント**（`symfony/workflow: ^6.4`）を使って実装されています。

定義ファイルは `app/config/eccube/packages/order_state_machine.php`、実装クラスは `src/Eccube/Service/OrderStateMachine.php` です。

### 受注ステータスの状態（Places）

| 定数 | 値 | 日本語名 |
|---|---|---|
| `OrderStatus::NEW` | 1 | 新規受付 |
| `OrderStatus::CANCEL` | 3 | 注文取り消し |
| `OrderStatus::IN_PROGRESS` | 4 | 対応中 |
| `OrderStatus::DELIVERED` | 5 | 発送済み |
| `OrderStatus::PAID` | 6 | 入金済み |
| `OrderStatus::PENDING` | 7 | 決済処理中 |
| `OrderStatus::PROCESSING` | 8 | 購入処理中 |
| `OrderStatus::RETURNED` | 9 | 返品 |

初期状態（`initial_marking`）は **新規受付（1）** です。

### 受注ステータスの遷移（Transitions）

| 遷移名 | 遷移元 | 遷移先 |
|---|---|---|
| `pay` | 新規受付 | 入金済み |
| `packing` | 新規受付、入金済み | 対応中 |
| `cancel` | 新規受付、対応中、入金済み | 注文取り消し |
| `back_to_in_progress` | 注文取り消し | 対応中 |
| `ship` | 新規受付、入金済み、対応中 | 発送済み |
| `return` | 発送済み | 返品 |
| `cancel_return` | 返品 | 発送済み |

---

## workflow:dump コマンドで状態遷移図を出力する

Symfony には `workflow:dump` コマンドが標準で搭載されています。EC-CUBE 4.3 の環境でそのまま使えます。


### Graphviz（dot形式）の出力を画像にする

dot形式の出力はGraphvizをインストールすることで画像に変換できます。


### Mermaid形式でそのまま確認する

Mermaid形式はGitHubのMarkdownや各種ドキュメントツールで直接レンダリングできます。


出力例：


### --with-metadata オプション

メタデータ付きで出力することもできます。


---