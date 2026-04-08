# EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

EC-CUBE 4では、受注ステータスの遷移管理にSymfony Workflow Componentを採用しています。この記事では、OrderStateMachineの仕組みを詳しく解説し、プラグインでの活用方法を紹介します。

## Symfony Workflow Componentとは

Symfony Workflow Componentは、**状態遷移**を管理するためのコンポーネントです。「ある状態から別の状態への移動ルール」を定義し、不正な遷移を防ぐことができます。

### 日常の例：信号機

信号機を例に考えてみましょう。

[青] → [黄] → [赤] → [青] ...

- 青 → 黄 ✅ OK
- 青 → 赤 ❌ NG（いきなり赤にはならない）
- 赤 → 青 ✅ OK

このような「状態の変化ルール」をコードで管理するのがWorkflow Componentです。

### WorkflowとStateMachineの違い

Symfony Workflowには2つのタイプがあります。

| タイプ | 特徴 | 用途 |
|--------|------|------|
| **Workflow** | 複数の状態を同時に持てる | 承認フロー（複数人の承認待ちなど） |
| **StateMachine** | 常に1つの状態のみ | 受注ステータスなど |

EC-CUBEのOrderStateMachineは、名前の通り**StateMachine**タイプを使用しています。

## EC-CUBEの受注ステータス

EC-CUBEでは以下の受注ステータスが定義されています。

| ID | 定数名 | 表示名 |
|----|--------|--------|
| 1 | `NEW` | 新規受付 |
| 3 | `CANCEL` | 注文取消し |
| 4 | `IN_PROGRESS` | 対応中 |
| 5 | `DELIVERED` | 発送済み |
| 6 | `PAID` | 入金済み |
| 7 | `PENDING` | 決済処理中 |
| 8 | `PROCESSING` | 購入処理中 |
| 9 | `RETURNED` | 返品 |