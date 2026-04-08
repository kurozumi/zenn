## Processorの種類と役割

### 1. ItemValidator - 商品単位の検証

商品1つ1つに対して検証を行います。

**例：在庫チェック（StockValidator）**


### 2. ItemHolderPreprocessor - 注文全体の前処理

カートや注文全体に対して処理を行います。

**例：送料計算（DeliveryFeePreprocessor）**


### 3. DiscountProcessor - 割引処理

クーポンやポイント値引きなどの割引処理を行います。

### 4. PurchaseProcessor - 購入確定処理

注文の仮確定・確定・取り消しを行います。


## プラグインでPurchaseFlowをカスタマイズする

### 方法1：アノテーションを使う（推奨）

クラスにアノテーションを付けるだけで、自動的にPurchaseFlowに組み込まれます。


**利用可能なアノテーション：**

| アノテーション | 対象フロー |
|---------------|-----------|
| `@CartFlow` | カートフロー |
| `@ShoppingFlow` | 購入フロー |
| `@OrderFlow` | 受注管理フロー |

### 方法2：services.yamlで設定する

より細かい制御（優先度指定など）が必要な場合は、`services.yaml`で設定します。


**タグ一覧：**

| タグ名 | Processor種類 |
|--------|---------------|
| `eccube.item.validator` | ItemValidator |
| `eccube.item.holder.validator` | ItemHolderValidator |
| `eccube.item.preprocessor` | ItemPreprocessor |
| `eccube.item.holder.preprocessor` | ItemHolderPreprocessor |
| `eccube.discount.processor` | DiscountProcessor |
| `eccube.item.holder.post.validator` | ItemHolderPostValidator |
| `eccube.purchase.processor` | PurchaseProcessor |

**flow_type：**
- `cart` - カートフロー
- `shopping` - 購入フロー
- `order` - 受注管理フロー

**priority：** 数値が大きいほど先に実行されます（デフォルト: 0）

## 実践例：購入数量の上限を設定する

商品1つあたりの購入数量を10個までに制限するValidatorを作成してみましょう。

### 1. Validatorクラスの作成


### 2. サービス登録（自動登録の場合は不要）


これだけで、カートと購入フローで数量制限が有効になります。

## 実践例：特定の条件で送料無料にする

5,000円以上の購入で送料を無料にするPreprocessorを作成します。


ℹ️ **注意**: このProcessorは `DeliveryFeePreprocessor` より後に実行される必要があります。priorityを調整するか、`services.yaml`で順序を制御してください。

## PurchaseFlowのデバッグ

現在のPurchaseFlowにどのProcessorが登録されているか確認できます。


出力例：

## まとめ

EC-CUBEのPurchaseFlowは、ストラテジーパターンにより以下のメリットを実現しています：

1. **柔軟性** - 処理を追加・削除しても他に影響しない
2. **再利用性** - 同じProcessorを複数のフローで使い回せる
3. **テスト容易性** - 各Processorを個別にテストできる
4. **保守性** - 処理の追加・変更が容易

プラグインでカスタマイズする際は：

1. 適切なProcessor種類（Validator/Preprocessor等）を選ぶ
2. アノテーションまたはservices.yamlでフローに登録する
3. 必要に応じてpriorityで実行順序を制御する

この仕組みを理解すれば、EC-CUBEの購入フローを自由自在にカスタマイズできます。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---