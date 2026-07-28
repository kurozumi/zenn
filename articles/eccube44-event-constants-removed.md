---
title: "そのフックポイント、一度も呼ばれていません。EC-CUBE 4.4で消える52定数"
emoji: "🪦"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: false
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.4 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## 結論: 動かないフックポイントを購読していたなら、4.4で気づきます

`EccubeEvents::FRONT_CART_ADD_COMPLETE` を購読して「カート追加後に何かする」プラグインを書いたのに、まったく動かなかった経験はないでしょうか。実装を疑って `dump()` を仕込んだり、優先度を変えてみたり。

原因はあなたのコードではありません。**そのイベント、EC-CUBE のどこからも `dispatch()` されていません。**

EC-CUBE 4.4 で、こうした dead 定数が **52個** まとめて削除されます（[PR #6894](https://github.com/EC-CUBE/ec-cube/pull/6894)、`4.4` ブランチに 2026年7月24日マージ済み）。

**TL;DR**

- `EccubeEvents` から未使用の定数52個が削除される（[PR #6894](https://github.com/EC-CUBE/ec-cube/pull/6894)）
- いずれも `dispatch()` 実績ゼロ。**購読しても元から呼ばれていなかった**ので、実挙動は変わらない
- ただし**定数名を書いているコードは `undefined constant` で落ちます**
- 内訳は ADMIN 系22、FRONT_CART 系13、FRONT_SHOPPING 系11、FRONT_PRODUCT 系5、FRONT_MYPAGE 系1
- `ADMIM` というタイポ定数や、3.x→4.x のカート書き換えで dispatch が消えた残骸が含まれる
- 公式ドキュメントが誤って案内していた `ADMIN_ORDER_CSV_EXPORT_SHIPPING` も対象

## 何が消えるのか

削除される52定数の全リストです。自分のプラグインを `grep` するときに使ってください。

### ADMIN 系（22個）

```
ADMIN_ADMIM_INDEX_INITIALIZE
ADMIN_CONTENT_LAYOUT_INDEX_INITIALIZE
ADMIN_CONTENT_LAYOUT_INDEX_COMPLETE
ADMIN_ORDER_MAIL_INDEX_CONFIRM
ADMIN_ORDER_MAIL_MAIL_ALL_INITIALIZE
ADMIN_ORDER_MAIL_MAIL_ALL_CHANGE
ADMIN_ORDER_MAIL_MAIL_ALL_CONFIRM
ADMIN_ORDER_MAIL_MAIL_ALL_COMPLETE
ADMIN_ORDER_DELETE_COMPLETE
ADMIN_ORDER_CSV_EXPORT_SHIPPING
ADMIN_SHIPPING_INDEX_INITIALIZE
ADMIN_SHIPPING_INDEX_SEARCH
ADMIN_PRODUCT_PRODUCT_CLASS_INDEX_INITIALIZE
ADMIN_PRODUCT_PRODUCT_CLASS_INDEX_CLASSES
ADMIN_PRODUCT_PRODUCT_CLASS_EDIT_INITIALIZE
ADMIN_PRODUCT_PRODUCT_CLASS_EDIT_COMPLETE
ADMIN_PRODUCT_PRODUCT_CLASS_EDIT_UPDATE
ADMIN_PRODUCT_PRODUCT_CLASS_EDIT_DELETE
ADMIN_PRODUCT_DISPLAY_COMPLETE
ADMIN_SETTING_SHOP_TAX_RULE_EDIT_PARAMETER_INITIALIZE
ADMIN_SETTING_SHOP_TAX_RULE_EDIT_PARAMETER_COMPLETE
ADMIN_SETTING_SYSTEM_MEMBER_DELETE_INITIALIZE
```

### FRONT_CART 系（13個）

```
FRONT_CART_INDEX_INITIALIZE
FRONT_CART_INDEX_COMPLETE
FRONT_CART_ADD_INITIALIZE
FRONT_CART_ADD_COMPLETE
FRONT_CART_ADD_EXCEPTION
FRONT_CART_UP_INITIALIZE
FRONT_CART_UP_COMPLETE
FRONT_CART_UP_EXCEPTION
FRONT_CART_DOWN_INITIALIZE
FRONT_CART_DOWN_COMPLETE
FRONT_CART_DOWN_EXCEPTION
FRONT_CART_REMOVE_INITIALIZE
FRONT_CART_REMOVE_COMPLETE
```

### FRONT_SHOPPING 系（11個）

```
FRONT_SHOPPING_INDEX_INITIALIZE
FRONT_SHOPPING_CONFIRM_INITIALIZE
FRONT_SHOPPING_CONFIRM_PROCESSING
FRONT_SHOPPING_CONFIRM_COMPLETE
FRONT_SHOPPING_DELIVERY_INITIALIZE
FRONT_SHOPPING_DELIVERY_COMPLETE
FRONT_SHOPPING_PAYMENT_INITIALIZE
FRONT_SHOPPING_PAYMENT_COMPLETE
FRONT_SHOPPING_SHIPPING_CHANGE_INITIALIZE
FRONT_SHOPPING_SHIPPING_EDIT_CHANGE_INITIALIZE
FRONT_SHOPPING_SHIPPING_MULTIPLE_CHANGE_INITIALIZE
```

### FRONT_PRODUCT 系（5個）と FRONT_MYPAGE 系（1個）

```
FRONT_PRODUCT_INDEX_COMPLETE
FRONT_PRODUCT_INDEX_DISP
FRONT_PRODUCT_INDEX_ORDER
FRONT_PRODUCT_DETAIL_FAVORITE
FRONT_PRODUCT_DETAIL_COMPLETE
FRONT_MYPAGE_MYPAGE_DELETE_INITIALIZE
```

## なぜ dead 定数が残っていたのか

削除された顔ぶれを見ると、来歴がだいたい読み取れます。

**カート系13個は 3.x → 4.x の書き換えの残骸です。** EC-CUBE 3系ではカート処理がコントローラに書かれていて、`front.cart.add.complete` のようなイベントを発火していました。4系で `CartService` と `PurchaseFlow` に処理が移った際に `dispatch()` は消えましたが、定数だけが `EccubeEvents` に残りました。

**購入フロー系11個も同じです。** 3系の購入フローは `/shopping/delivery` `/shopping/payment` と画面が分かれていました。4系で `/shopping` に統合された結果、`FRONT_SHOPPING_DELIVERY_INITIALIZE` のような画面単位のイベントが宙に浮きました。

**ADMIN 系には管理画面の Ajax 化・画面統合の残骸が混ざっています。** 商品規格編集が Ajax になり、`ADMIN_PRODUCT_PRODUCT_CLASS_EDIT_UPDATE` などが不要になったのがその例です。

そして極めつけがこれです。

```php
public const ADMIN_ADMIM_INDEX_INITIALIZE = 'admin.admin.index.initialize';
```

`ADMIM`。タイポです。定数名がタイポしていても誰も困らなかったのは、誰も使っていなかったからです。

:::message
なお `ADMIN_ADMIM_LOGIN_INITIALIZE` のほうは**削除されていません**。こちらは実際に dispatch されているため、タイポを抱えたまま残ります。名前を直すと後方互換が壊れるので、そのままです。
:::

## 公式ドキュメントが間違っていた件

削除リストの中で1つだけ性質が違うものがあります。`ADMIN_ORDER_CSV_EXPORT_SHIPPING` です。

CSV の出力項目をプラグインから増やすとき、コアを改変せずイベントを購読するのが定石です。EC-CUBE のドキュメントには、受注 CSV 用と出荷 CSV 用の2つのイベントが案内されていました。

```
- `ADMIN_ORDER_CSV_EXPORT_ORDER` / `ADMIN_ORDER_CSV_EXPORT_SHIPPING`
```

ところが `OrderController::exportCsv()` の実装は、受注 CSV でも出荷 CSV でも `ADMIN_ORDER_CSV_EXPORT_ORDER` の1つしか dispatch していませんでした。`_SHIPPING` は配線されていません。

つまり**ドキュメントに従って `ADMIN_ORDER_CSV_EXPORT_SHIPPING` を購読した人は、出荷 CSV に列を追加できずに悩んでいた**はずです。#6894 では定数の削除と合わせて、この案内も修正されています。

```
- `ADMIN_ORDER_CSV_EXPORT_ORDER`（受注・出荷 CSV 共通。`OrderController::exportCsv()` は
  受注/出荷どちらのエクスポートでもこの1イベントを dispatch する）
```

出荷 CSV に列を足したいなら、`ADMIN_ORDER_CSV_EXPORT_ORDER` を購読して出力種別で分岐する形になります。

## 自分のプラグインを確認する

実挙動は変わりません。呼ばれていなかったものが消えるだけです。ただし**定数名を書いているだけで fatal になります**。

PHP は未定義の定数を参照するとエラーになります（PHP 8 以降は `Error` 例外）。

```
PHP Fatal error: Uncaught Error: Undefined constant
Eccube\Event\EccubeEvents::FRONT_CART_ADD_COMPLETE
```

`getSubscribedEvents()` に書いてあれば、そのサブスクライバがロードされた時点で落ちます。つまり**プラグインを有効化した瞬間にサイトが死にます**。

確認はこれで足ります。

```bash
grep -rnE 'FRONT_CART_(INDEX|ADD|UP|DOWN|REMOVE)_|FRONT_SHOPPING_(INDEX_INITIALIZE|CONFIRM|DELIVERY|PAYMENT|SHIPPING_)|FRONT_PRODUCT_(INDEX_(COMPLETE|DISP|ORDER)|DETAIL_(FAVORITE|COMPLETE))|FRONT_MYPAGE_MYPAGE_DELETE_INITIALIZE|ADMIN_ADMIM_INDEX_INITIALIZE|ADMIN_CONTENT_LAYOUT_INDEX_|ADMIN_ORDER_(MAIL_|DELETE_COMPLETE|CSV_EXPORT_SHIPPING)|ADMIN_SHIPPING_INDEX_|ADMIN_PRODUCT_(PRODUCT_CLASS_|DISPLAY_COMPLETE)|ADMIN_SETTING_(SHOP_TAX_RULE_EDIT_PARAMETER_|SYSTEM_MEMBER_DELETE_INITIALIZE)' app/Plugin/ app/Customize/
```

イベント名の**文字列**（`'front.cart.add.complete'` のような値）で購読している場合は、定数が消えても `undefined constant` にはなりません。ただしそのイベントは元から発火していないので、いずれにせよ動きません。

### 引っかかったらどうするか

購読していたイベントが消えるということは、**そこでやりたかった処理の実現方法を考え直す必要がある**ということです。定数を消して終わりではありません。

カート操作に反応したいなら、`PurchaseFlow` の `ItemHolderPreprocessor` / `ItemHolderValidator` を実装するのが 4系の作法です。

```php
namespace Plugin\YourPlugin\Service\PurchaseFlow\Processor;

use Eccube\Attribute\CartFlow;
use Eccube\Entity\ItemHolderInterface;
use Eccube\Service\PurchaseFlow\ItemHolderPreprocessor;
use Eccube\Service\PurchaseFlow\PurchaseContext;

#[CartFlow]
class YourCartProcessor implements ItemHolderPreprocessor
{
    public function process(ItemHolderInterface $itemHolder, PurchaseContext $context): void
    {
        // カートの内容に応じた処理
    }
}
```

購入フローの各段階に割り込みたい場合も同様で、`PurchaseFlow` の各インターフェースか、`kernel.controller` などの Symfony 標準イベントを使うことになります。

購入完了時のフックは残っているので、そちらは従来どおりです。

## dead code を消すという判断について

52定数の削除は、機能的には何も変わらない変更です。それでも入れる価値があります。

`EccubeEvents` を開いた開発者は、そこに並んでいる定数が使えるものだと考えます。実際には半分近くが動かないとなると、**ドキュメントとしての信頼性がありません**。実際に公式ドキュメントまで誤った案内をしていたわけで、実害が出ています。

一方でリスクもあります。互換性チェックリストで、作者はこの項目にだけチェックを入れていません。

> ただし定数を名前で参照しているコードがあれば `undefined constant` になります

動かないものを消すだけだから影響ゼロ、と言い切らずに fatal になる経路を明記しているのは、誠実な書き方だと思います。

## まとめ

- EC-CUBE 4.4 で `EccubeEvents` から dead 定数52個が削除される（[PR #6894](https://github.com/EC-CUBE/ec-cube/pull/6894)）
- いずれも `dispatch()` されていないため、購読していても元から動いていない
- **定数名を参照しているコードは `undefined constant` で fatal**。プラグイン有効化時に落ちる
- 多くは 3.x → 4.x の書き換えで dispatch だけ消えた残骸
- `ADMIN_ORDER_CSV_EXPORT_SHIPPING` は公式ドキュメントが誤って案内していた。出荷 CSV も `ADMIN_ORDER_CSV_EXPORT_ORDER` で処理する
- カート操作に反応したいなら `PurchaseFlow` のプロセッサを使う

自分が過去に「このイベント効かないな」と思って諦めた記憶があるなら、それは気のせいではなかったということです。

:::message alert
EC-CUBE 4.4 はこの記事を書いている時点（2026年7月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
