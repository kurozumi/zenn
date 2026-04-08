## ステータス遷移図

EC-CUBEで定義されているステータス遷移は以下の通りです。


## OrderStateMachineの設定

EC-CUBEでは、`app/config/eccube/packages/order_state_machine.php` でステータス遷移を定義しています。


### 設定の解説

| キー | 説明 |
|------|------|
| `type` | `state_machine`（1つの状態のみ持てる） |
| `marking_store` | 状態を保存/取得する方法 |
| `supports` | このワークフローが適用されるクラス |
| `initial_marking` | 初期状態 |
| `places` | 取りうるすべての状態 |
| `transitions` | 状態遷移の定義 |

## OrderStateMachineサービス

`OrderStateMachine`サービスは、受注ステータスの遷移を管理します。

### 主要なメソッド


### 遷移時のイベント処理

`OrderStateMachine`は`EventSubscriberInterface`を実装しており、遷移時に自動的に処理が実行されます。


### 遷移ごとの処理内容

| 遷移 | 処理内容 |
|------|----------|
| `pay` | 入金日を設定 |
| `cancel` | 在庫を戻す、利用ポイントを戻す |
| `back_to_in_progress` | 在庫を減らす、利用ポイントを減らす |
| `ship` | 加算ポイントを付与 |
| `return` | 利用ポイントを戻す、加算ポイントを取り消す |
| `cancel_return` | 利用ポイントを減らす、加算ポイントを再付与 |

## プラグインでの活用

### 1. 遷移イベントをフックする

特定のステータス遷移時に独自の処理を追加できます。


### 2. 遷移前の検証（Guard）

遷移を許可するかどうかを動的に制御できます。


### 3. カスタムステータスと遷移の追加

プラグインで独自のステータスと遷移を追加する例です。

#### マイグレーションでステータスを追加


#### 遷移の追加（services.yamlで拡張）


### 4. Controllerでの使用例


## イベント一覧

Symfony Workflowが発火するイベントの一覧です。

| イベント名 | タイミング |
|------------|------------|
| `workflow.order.guard.{transition}` | 遷移前の検証 |
| `workflow.order.leave.{place}` | 状態を離れる直前 |
| `workflow.order.transition.{transition}` | 遷移中 |
| `workflow.order.enter.{place}` | 新しい状態に入った直後 |
| `workflow.order.entered.{place}` | 新しい状態に入った後 |
| `workflow.order.completed` | 遷移完了後 |
| `workflow.order.announce.{transition}` | 遷移可能になったとき |

## デバッグ

現在の受注から遷移可能なステータスを確認できます。


## まとめ

EC-CUBEのOrderStateMachineは、Symfony Workflow Componentを活用して以下を実現しています。

1. **不正な遷移の防止** - 定義されたルール以外の遷移を許可しない
2. **遷移時の自動処理** - 在庫戻し、ポイント処理などを自動実行
3. **拡張性** - プラグインで遷移のフック、ガード、カスタムステータスを追加可能

プラグインで活用する際は：

1. **イベントをフック** - `workflow.order.transition.{name}` で遷移時の処理を追加
2. **ガードで制御** - `workflow.order.guard.{name}` で遷移を動的に許可/禁止
3. **カスタムステータス** - マイグレーションと設定でステータスを追加

この仕組みを理解すれば、EC-CUBEの受注処理を柔軟にカスタマイズできます。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---