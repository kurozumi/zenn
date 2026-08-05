---
title: "選べない支払方法の手数料が請求されていた。EC-CUBE 4.4が直した集計バグ"
emoji: "💸"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
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

## 結論: 画面に出ていない支払方法の手数料が、合計に乗っていました

支払方法には利用可能金額の条件を付けられます。代引きは10万円まで、郵便振替は1,000円まで、といった設定です。自分が関わった案件でも、たいてい何かしら条件が入っていました。

EC-CUBE 4.3 以前には、この設定でお金が合わなくなるバグがありました。**利用条件から外れて選択肢に表示されない支払方法の手数料が、注文手続き画面の合計に加算される**というものです。

[PR #6870](https://github.com/EC-CUBE/ec-cube/pull/6870)（`4.4` ブランチに 2026年7月8日マージ済み）で修正されました。

**TL;DR**

- 利用条件付き・手数料ありの支払方法を先頭に置くと、条件外の注文でもその手数料が加算されていた（[Issue #6200](https://github.com/EC-CUBE/ec-cube/issues/6200)）
- 原因は「初期選択される支払方法」と「ユーザーが選べる選択肢」でフィルタ条件が違ったこと
- `OrderHelper::setDefaultPayment()` は**支払総額が確定する前**に呼ばれるため、利用条件で絞れない
- 4.4 では集計後に選択肢と突き合わせ、含まれていなければ選択可能な先頭へ再設定する
- 選択可能な支払方法が1つもない場合は未選択（`null`）に戻す

## 再現手順

PR に書かれている手順がそのまま使えます。

1. 先頭の支払方法（例: 郵便振替）に **手数料 ¥500 / 利用条件 ¥0〜¥1,000** を設定する
2. **¥1,000 を超える商品**（例: ¥3,080）をカートに追加する
3. レジへ進み、注文手続き画面を開く

修正前は、郵便振替が選択肢に**表示されていないのに**手数料 ¥500 が加算され、合計に上乗せされます。

画面に出ていない支払方法の手数料なので、購入者からは理由が分かりません。「なぜか500円高い」という問い合わせになります。

## なぜ起きるのか

原因は、支払方法を絞り込む処理が**2箇所にあって条件が違う**ことです。

### 1. 初期選択: `OrderHelper::setDefaultPayment()`

カートから受注データを作るときに、初期の支払方法を設定します。

```php
// 利用可能な支払い方法を抽出.
// ここでは支払総額が決まっていないため、利用条件に合致しないものも選択対象になる場合がある
$Payments = $this->paymentRepository->findAllowedPayments($Deliveries, true);

// 初期の支払い方法を設定.
$Payment = current($Payments);
if ($Payment) {
    $Order->setPayment($Payment);
    $Order->setPaymentMethod($Payment->getMethod());
}
```

コメントに書いてあるとおりです。**この時点では支払総額が決まっていません。** 送料も手数料も税もまだ計算されていない段階なので、`rule_min` / `rule_max` による利用条件のフィルタができません。

だから配送業者に紐づく支払方法をそのまま取ってきて、先頭（`current()`）を初期値にします。

### 2. 選択肢: `OrderType::filterPayments()`

一方、注文手続き画面のフォームは別の処理で選択肢を作ります。こちらは集計後に走るので、**利用条件も手数料も込みで正しく絞り込めます**。

### ずれが残る

結果として、こうなります。

| | 絞り込み条件 | タイミング |
| --- | --- | --- |
| 初期選択（手数料の出どころ） | 配送業者のみ | 集計前 |
| 画面の選択肢 | 配送業者 + 利用条件 + 手数料 | 集計後 |

`Order` にセットされた支払方法が手数料の計算元になります。画面の選択肢から外れても、`Order` 側の支払方法は差し替わりません。**選べないのに手数料だけ残る**、という状態です。

## 4.4 の修正

`ShoppingController::index()` に、集計後の突き合わせが入りました。

```php
// 初期選択された支払方法が利用条件に合致せず選択肢に含まれない場合は,
// 選択可能な支払方法の先頭に再設定し, 手数料を再集計する.
// @see https://github.com/EC-CUBE/ec-cube/issues/6200
if ($this->reselectUnavailablePayment($Order, $form)) {
    $flowResult = $this->executePurchaseFlow($Order, false);
    $this->entityManager->flush();
    // ...
}
```

判定の中身はこうです。

```php
private function reselectUnavailablePayment(Order $Order, FormInterface $form): bool
{
    if (!$form->has('Payment')) {
        return false;
    }

    /** @var Payment[] $Payments */
    $Payments = $form->get('Payment')->getConfig()->getOption('choices');
    $Payment = $Order->getPayment();

    // 選択中の支払方法が選択肢に含まれていれば補正不要.
    $selectableIds = array_map(static fn (Payment $p) => $p->getId(), $Payments);
    if ($Payment && in_array($Payment->getId(), $selectableIds, true)) {
        return false;
    }

    $NewPayment = $Payments ? reset($Payments) : null;
    // 既に同じ状態(共にnull)であれば補正不要.
    if ($Payment === $NewPayment) {
        return false;
    }

    $Order->setPayment($NewPayment ?: null);
    $Order->setPaymentMethod($NewPayment ? $NewPayment->getMethod() : null);

    return true;
}
```

読みどころが3つあります。

**フォームの `choices` を正解として使っている点。** 利用条件のロジックを再実装するのではなく、`$form->get('Payment')->getConfig()->getOption('choices')` でフォームが実際に持っている選択肢を引いています。判定ロジックが二重管理にならないので、`filterPayments()` 側が将来変わっても追従します。

**選択可能な支払方法がゼロなら `null` に戻す点。** `$Payments` が空なら `$NewPayment` は `null` になり、`setPayment(null)` されます。適当な支払方法を残さないので、誤った手数料が残りません。

**再設定したときだけ再集計する点。** 戻り値が `true` のときだけ `executePurchaseFlow()` を呼び直します。毎回集計し直すと無駄なので、必要なときだけです。

## プラグイン開発者への影響

決済プラグインを書いている方は、2点確認しておくと安全です。

**支払方法が `null` になり得ます。** 選択可能な支払方法が1つもない構成では、`$Order->getPayment()` が `null` を返します。修正前は「条件外でも何かしら入っている」状態だったので、null チェックを省いていたコードがあるかもしれません。

**`ShoppingController::index()` で `PurchaseFlow` がもう一度走ります。** 再設定が発生した場合に限りますが、`ItemHolderPreprocessor` などが同一リクエスト内で2回呼ばれることになります。プロセッサが冪等でない（呼ばれるたびに明細を追加する等）と、二重計上になります。

自作プロセッサが冪等かどうかは、この機会に見ておく価値があります。既存明細を探して更新するのではなく、毎回 `addItem()` しているようなコードは危険です。

## 設定を見直す価値もあります

コード側が直っても、**支払方法の並び順は運用の問題として残ります**。

初期選択されるのは「配送業者に紐づく支払方法の先頭」です。4.4 では条件外なら差し替わりますが、そのぶん `PurchaseFlow` が余分に1回走ります。

利用条件の厳しい支払方法（少額限定の郵便振替など）を先頭に置いている場合は、条件のゆるいものを先頭に持ってくるほうが素直です。管理画面の「支払方法設定」で並び順を変えられます。

## まとめ

- 利用条件から外れて選択肢に出ない支払方法の手数料が、合計に加算されるバグがあった（[#6200](https://github.com/EC-CUBE/ec-cube/issues/6200) / [PR #6870](https://github.com/EC-CUBE/ec-cube/pull/6870)）
- 原因は「初期選択」と「画面の選択肢」でフィルタ条件が違ったこと。初期選択は支払総額の確定前に走るため利用条件を見られない
- 4.4 では集計後にフォームの `choices` と突き合わせ、外れていれば選択可能な先頭に再設定する
- 選択可能な支払方法がなければ `null` に戻すので、`getPayment()` の null チェックが要る
- 再設定時は `PurchaseFlow` が同一リクエストで2回走る。自作プロセッサの冪等性を確認しておくこと

金額がずれるバグは、購入者からは「なんか高い」としか見えません。気づかれないまま積み上がるタイプなので、4.3 以前を運用していて利用条件を使っているなら、一度合計を確認してみることをおすすめします。

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
