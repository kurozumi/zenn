## 問題：ネストしたフォームで `POST_SUBMIT` の `isValid()` が信頼できない

EC-CUBE の注文フォームはネスト構造を持っています。`OrderType` が親フォームで、配送先ごとに `ShippingType` が子フォームとして含まれます。


Symfony のフォームは `submit()` が呼ばれると、子フォームから順番に `POST_SUBMIT` イベントを発火させます。**バリデーションはルートフォームの `POST_SUBMIT` 時にまとめて実行**されます。


つまり `ShippingType` の `POST_SUBMIT` リスナー内で `$form->isValid()` を呼んでも、この時点ではバリデーションが走っていないため `true` が返ってしまいます。

現在の Symfony 6.4 に `POST_VALIDATE` イベントは存在しません（`FormEvents` に定義されているのは `PRE_SET_DATA`, `POST_SET_DATA`, `PRE_SUBMIT`, `SUBMIT`, `POST_SUBMIT` の5つのみ）。

### 現状の回避策

`POST_SUBMIT` の実行優先度を下げることで、バリデーションより後に処理を走らせる方法があります。


ただしこれはバリデーションの実行タイミングに依存したハックであり、フォーム構造の変化で壊れる可能性があります。

---

## Symfony 8.1 での解決策：`ValidatorFormEvents::POST_VALIDATE`

Symfony PR [#47210](https://github.com/symfony/symfony/pull/47210) では、バリデーション専用のイベントが追加されます。


### 追加されるクラス・定数

| 追加物 | 内容 |
|---|---|
| `ValidatorFormEvents::PRE_VALIDATE` | バリデーション開始前のイベント文字列 |
| `ValidatorFormEvents::POST_VALIDATE` | バリデーション完了後のイベント文字列 |
| `PreValidateEvent` | `FormEvent` を継承した final クラス |
| `PostValidateEvent` | `FormEvent` を継承した final クラス |

既存の `FormEvents` クラスには追加されず、バリデーター拡張専用の `ValidatorFormEvents` クラスとして分離されます。

### イベント発火の順序



---

## EC-CUBEプラグインでの実践：現時点での推奨パターン

### パターン1：フォームバリデーションは Symfony Constraints に任せる

フィールドの入力値チェックは Constraints として宣言的に書き、ビジネスロジック検証は PurchaseFlow に追加します。`POST_SUBMIT` は「バリデーション結果を見て何かする」用途に使わないのが安全です。


### パターン2：ビジネスロジック検証は PurchaseFlow に追加する

在庫・価格・配送に関するビジネスロジックの検証は PurchaseFlow の Processor として実装します。


---

## まとめ

| | 現在（Symfony 6.4） | PR #47210後（Symfony 8.1〜） |
|---|---|---|
| バリデーション後のイベント | なし（`POST_SUBMIT` で代替） | `ValidatorFormEvents::POST_VALIDATE` |
| 子フォームでの `isValid()` | 不正確（バリデーション前） | 正確（バリデーション後） |
| EC-CUBE コアの検証 | PurchaseFlow（FormEvents を使わない） | 変わらず |
| プラグインの推奨パターン | Constraints + PurchaseFlow Processor | 変わらず（`POST_VALIDATE` が選択肢として加わる） |

EC-CUBE のビジネスロジック検証は PurchaseFlow が担当しているため、`POST_VALIDATE` の恩恵を受けるのは主に「フォームバリデーション後に UI フィードバックを調整する」プラグインや、Symfony のフォームシステムに慣れた開発者が書くフォーム拡張コードです。

プラグインで `POST_SUBMIT` の `isValid()` が思った通りに動かないと感じたことがあれば、コメントで教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---