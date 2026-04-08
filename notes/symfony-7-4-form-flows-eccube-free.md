# 100行のセッション管理が3行に。Symfony 7.4 Form FlowsでEC-CUBEの購入フローが変わる

⚠️ ## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！
⚠️ 
⚠️ プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。
⚠️ 
⚠️ 👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## 結論：100行のセッション管理コードが、3行になった

**「あなたのEC-CUBEプロジェクトに、こんなコードはありませんか？」**

- セッションに一時データを保存
- ステップごとにリダイレクト制御
- 戻るボタンの状態復元
- バリデーションエラー時の再表示...

**これ、全部いらなくなります。**

Symfony 7.4で導入された**Form Flows**を使えば、上記の処理がすべて自動化されます。

```php
// Before: セッションに保存、リダイレクト、状態管理...約100行
// After: たった3行
$builder->addStep('shipping', ShippingType::class);
$builder->addStep('payment', PaymentType::class);
$builder->addStep('confirm', ConfirmType::class);
```

**これだけです。**

## 前提条件

- PHP 8.2以上
- Symfony 7.4以上
- EC-CUBE 4.3以上（将来的にSymfony 7.x対応時に利用可能）