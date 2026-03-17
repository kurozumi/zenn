---
title: EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理
tags:
  - PHP
  - Symfony
  - EC-CUBE
private: false
updated_at: '2026-03-17T22:47:07+09:00'
id: 147381d54d59ead48369
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理](https://zenn.dev/and_and/articles/eccube-order-state-machine)**

---

EC-CUBE 4では、受注ステータスの遷移管理にSymfony Workflow Componentを採用しています。この記事では、OrderStateMachineの仕組みを詳しく解説し、プラグインでの活用方法を紹介します。

## Symfony Workflow Componentとは

Symfony Workflow Componentは、**状態遷移**を管理するためのコンポーネントです。「ある状態から別の状態への移動ルール」を定義し、不正な遷移を防ぐことができます。

### 日常の例：信号機

信号機を例に考えてみましょう。

```
[青] → [黄] → [赤] → [青] ...
```

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4のOrderStateMachineを理解する - Symfony Workflowで実現する受注ステータス管理](https://zenn.dev/and_and/articles/eccube-order-state-machine)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
