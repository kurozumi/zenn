## 3. Rate Limiter - レート制限

ログイン試行やAPI呼び出しの回数制限を実装できます。

### 設定ファイル


### 使用例


## 4. Lock Component - 排他制御

在庫更新や重複注文防止に活用できます。

### 使用例


## 5. HttpClient - 外部API連携

配送状況の確認や在庫管理システムとの連携など、外部APIとの通信に使用します。

### サービス定義


### 配送状況確認の例


## 6. Validator（カスタム制約） - 独自バリデーション

独自のバリデーションルールを作成し、FormExtension でコアのフォームに適用できます。

### 制約クラス


### バリデータクラス


### FormExtension で既存フォームに適用


## 7. ExpressionLanguage - 動的条件評価

条件式を文字列で記述し、動的に評価できます。

### 使用例


## 8. Serializer - データ変換

カスタム Normalizer を使って、コアエンティティを任意の形式に変換できます。

### カスタム Normalizer


### エクスポートサービス


## 9. Security Voter - 購入制限

会員のみ購入可能な商品など、購入制限を実装できます。

### Voterクラス


### 使用例


## 10. Service Subscriber - 遅延読み込み

必要な時だけサービスを読み込み、パフォーマンスを向上させます。

### Service Subscriberの実装


## まとめ

| 技術 | 主な用途 |
|------|----------|
| Workflow | 受注・会員ステータスの状態管理 |
| Messenger | メール送信・外部連携の非同期処理 |
| Rate Limiter | ログイン・API呼び出しの回数制限 |
| Lock | 在庫更新の排他制御 |
| HttpClient | 決済・配送サービスとの連携 |
| Validator | 商品コード重複などの独自検証 |
| ExpressionLanguage | 動的な割引・送料ルール |
| Serializer | CSV/JSONインポート・エクスポート |
| Security Voter | 商品・カテゴリへのアクセス制御 |
| Service Subscriber | サービスの遅延読み込み |

これらの技術を組み合わせることで、より堅牢で拡張性の高いプラグインを開発できます。Symfony の公式ドキュメントも併せて参照してください。

## 参考リンク

- [Symfony Documentation](https://symfony.com/doc/current/index.html)
- [EC-CUBE 4 開発者向けドキュメント](https://doc4.ec-cube.net/)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---