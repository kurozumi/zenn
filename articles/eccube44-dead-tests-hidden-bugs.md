---
title: "スキップされたテスト51件を棚卸ししたら、実装のバグが2件出てきた話"
emoji: "🧟"
type: "tech"
topics: ["eccube", "eccube4", "php", "phpunit", "テスト"]
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

## 結論: `markTestIncomplete()` は、バグの隠し場所になります

EC-CUBE 4.4 に、テストの棚卸しをする [PR #6945](https://github.com/EC-CUBE/ec-cube/pull/6945) が入りました（`4.4` ブランチに 2026年7月22日マージ済み、+1,335/-2,387）。

きっかけは、別 PR のレビューで `EditControllerWithMultipleTest` が `setUp()` の `markTestIncomplete()` によって**まったく実行されていない**と判明したことでした。1メソッドではなく、テストクラス丸ごとです。

そこで同種のマーカーを全件洗い出したところ、`markTestIncomplete` が **51件** ありました。調べてみると、**理由の多くが誤りか陳腐化**していたそうです。「未実装だからスキップ」と書かれたものの大半は、機能は 4.4 に実装済みで、テスト側が旧仕様・旧 API のまま取り残されているだけでした。

そして死んだテストの陰に、**実装側のバグが2件隠れていました**。

**TL;DR**

- `markTestIncomplete` を 51件 → 13件に削減（[PR #6945](https://github.com/EC-CUBE/ec-cube/pull/6945)）
- 「未実装だからスキップ」の大半は、実際には機能が実装済みでテストが古いだけだった
- 死んだテストの陰に実装バグが2件。`src/` の変更はわずか2ファイル12行
- バグ①: `Order::getTotalByTaxRate()` の null ガード漏れ。**明細を直接組み立てるプラグインから到達しうる**
- バグ②: お問い合わせ確認ページの `<title>` が入力ページのままだった
- どちらも「描画結果が変わる」変更として PR に明記されている

## テストが死ぬ2つの経路

PHPUnit でテストを止める手段はいくつかあります。今回問題になったのは `markTestIncomplete()` です。

```php
public function setUp(): void
{
    parent::setUp();
    $this->markTestIncomplete('複数配送は未実装のため');
}
```

`setUp()` に書くと、**そのクラスの全テストメソッドが実行されません**。しかも PHPUnit の出力では「Incomplete」として集計されるだけで、赤くなりません。CI は緑のままです。

もう1つの経路が、理由の陳腐化です。書かれた当時は正しかった理由が、実装が進んで嘘になる。それでも誰も見直さないので、テストは死んだままになります。今回の棚卸しで削られた38件の大半がこれでした。

数字で見ると効果が分かります。

| | Before | After |
| --- | --- | --- |
| incomplete（意図的な分を除く） | 51 | **13** |
| `ProductControllerTest` | 48 tests / Incomplete 5 / Assertions 123 | 48 tests / **Incomplete 0** / Assertions 147 |
| `tests/Web/Admin/Order/` | 78 tests / Incomplete 11 | 77 tests / **Incomplete 0** |
| `CartValidationTest` | Incomplete 15 / Assertions 96 | Incomplete 8 / **Assertions 146** |
| `TransactionListener` | 無テスト | **14 tests / 27 assertions** |

`ProductControllerTest` はテスト数が48で変わらないのに、アサーション数が123から147に増えています。**実行されていなかった分が動き出した**ということです。

残った13件のうち12件は Agent Commerce の仕様トレーサビリティ用で、意図的なマーカーだそうです。

## バグ①: 税率別合計の null ガード漏れ

ここからが本題です。

`Order` には税率ごとの集計を返すメソッドが2つあります。`getTaxByTaxRate()`（税額）と `getTotalByTaxRate()`（合計）です。4.4 の実装を並べると、こうなっています。

```php
public function getTaxByTaxRate(): array
{
    $roundingTypes = $this->getRoundingTypeByTaxRate();
    // ...
    foreach ($this->getTaxableTotalByTaxRate() as $rate => $totalPrice) {
        if (!array_key_exists($rate, $roundingTypes) || null === $roundingTypes[$rate]) {
            continue;
        }
        // ...
        $tax[$rate] = TaxRuleService::roundByRoundingType($value, $roundingTypes[$rate]->getId());
    }
```

```php
public function getTotalByTaxRate(): array
{
    $roundingTypes = $this->getRoundingTypeByTaxRate();
    // ...
    foreach ($this->getTaxableTotalByTaxRate() as $rate => $totalPrice) {
        if (!array_key_exists($rate, $roundingTypes) || null === $roundingTypes[$rate]) {
            continue;
        }
        // ...
        $total[$rate] = TaxRuleService::roundByRoundingType($value, $roundingTypes[$rate]->getId());
    }
```

いまは同じガードが入っています。ところが **#6945 の前は `getTotalByTaxRate()` にだけこのガードがありませんでした**。

`OrderItem::getRoundingType()` の戻り値は `?RoundingType` です。null になり得ます。ガードなしで `$roundingTypes[$rate]->getId()` を呼べば、`RoundingType` 未設定の課税明細が1件でもあった時点でこうなります。

```
Call to a member function getId() on null
```

`getTaxByTaxRate()` 側には 2024年3月の「Fix phpstan」というコミットで同じガードが入っていました。**片方だけ直して、対になるメソッドを見落とした**という、よくある形です。

### 単なる防御ではなく、実害があります

「null チェック漏れを直しただけ」と読むと過小評価になります。効いてくるのは帳票です。

`OrderPdfService` は2つのメソッドを突き合わせて帳票を組み立てます。

```php
foreach ($Order->getTotalByTaxRate() as $rate => $total) {
    // ... $Order->getTaxByTaxRate()[$rate] ...
}
```

片方だけが `continue` でスキップし、もう片方がスキップしないと、**集計対象の税率がずれて未定義キーを引きます**。ガードを揃えたことで、両者の税率キーが常に一致するようになりました。

### プラグイン開発者にとっての意味

通常は `PurchaseFlow` の `TaxProcessor` が `RoundingType` を必ず設定するため、この経路には到達しません。顕在化しにくいバグです。

問題は、**明細を直接組み立てるカスタマイズやプラグインからは到達しうる**ことです。`OrderItem` を自分で `new` して `Order` に追加するようなコードを書いていると、`RoundingType` の設定を忘れやすい。PurchaseFlow を通さずに明細を作る決済プラグインや、受注データを一括投入するバッチが該当します。

4.4 ではガードが入ったので fatal にはなりません。ただし**その税率が集計から静かに落ちます**。fatal で気づくほうがまだマシだったかもしれない、という類の変更です。PR でも「従来 fatal だったケースが集計スキップになる」と、描画結果が変わる点が明記されています。

`OrderItem` を手で組み立てているコードがあるなら、4.4 に上げる前に `RoundingType` を設定しているか確認しておくと安全です。

## バグ②: 確認ページのタイトルが入力ページのまま

もう1件は地味ですが、原因が面白い話です。

お問い合わせの確認ページ（`/contact` に POST した後の画面）で、`<title>` が「お問い合わせ(入力ページ)」のままになっていました。

原因はルーティングです。`ContactController` を見ると、`contact` と `contact_confirm` が**同一パス `/contact`** に割り当てられています。

```php
#[Route(path: '/contact', name: 'contact_confirm', methods: ['GET', 'POST'])]
```

Symfony のルータは、同じパスに複数のルートがあれば先に定義されたほうにマッチします。したがって `_route` は常に `contact` です。

`TwigInitializeListener` は `_route` から Page 名を引いて Twig のグローバル変数 `title` に設定します。だから確認ページでも入力ページのタイトルが出ていました。

ややこしいのは、**`meta_tags` は正しく出ていた**ことです。コントローラが `render` に渡す `Page(contact_confirm)` はそちらには効いていて、`noindex` は正しく出力されていました。`title` だけが不整合という、気づきにくい状態です。

### 修正方法の選択

`default_frame.twig` の `<title>` は `subtitle` を `title` より優先します。そこで `subtitle` に Page 名を渡して上書きする形になりました。

```php
$Page = $this->pageRepository->getPageByRoute('contact_confirm');
// ...
// contact と contact_confirm は同一パス '/contact' のため, ルータは常に
// ...
// title より優先される subtitle で確認ページ名を上書きする.
'subtitle' => $Page->getName(),
```

`ProductController` が `'subtitle' => $Product->getName()` としているのと同じ手法です。

注目すべきは、**ルーティングを変えなかった**ことです。

> **ルーティングは変更していません。** パスを分けると公開 URL が変わり後方互換性を壊すためです。

`/contact/confirm` のようにパスを分ければ根本解決ですが、公開 URL が変わります。マイナーバージョンアップでそれをやると、リンクやブックマーク、外部からの参照が壊れます。根本原因を残してでも影響範囲の小さい修正を選ぶ、という判断です。

同じ状況に置かれたとき、どこまで直すかの判断材料になると思います。

## 何を学べるか

この PR から持ち帰れるのは、テストの扱いについての2点です。

**`markTestIncomplete()` に理由を書いても、その理由は腐ります。** 今回、削られた38件の大半が「機能は実装済みなのにテストが古いまま」でした。書いた時点では正しかった理由が、実装の前進とともに嘘になる。マーカーは書いた瞬間から劣化し始めます。

**`setUp()` のマーカーはクラス丸ごとを殺します。** しかも CI は緑のまま。今回の発端がまさにこれで、レビューで指摘されるまで誰も気づきませんでした。テストが死んでいる間、その範囲のバグは検出されません。実際に2件出てきました。

自分のプラグインでも、こう確認しておくと安いコストで済みます。

```bash
grep -rn 'markTestIncomplete\|markTestSkipped' app/Plugin/*/Tests/
```

理由を読んで、いま本当にその理由が成立しているか。1つずつ外して実行してみると、EC-CUBE 本体と同じことが起きるかもしれません。

## まとめ

- EC-CUBE 4.4 で `markTestIncomplete` が 51件 → 13件に整理された（[PR #6945](https://github.com/EC-CUBE/ec-cube/pull/6945)）
- 「未実装だから」の大半は、機能は実装済みでテスト側が陳腐化していただけ
- 死んだテストの陰に実装バグが2件隠れていた
- `Order::getTotalByTaxRate()` の null ガード漏れは、明細を手で組み立てるプラグインから到達しうる。fatal は消えたが、その税率が静かに集計から落ちる
- お問い合わせ確認ページの `<title>` は、同一パスのルートが2つあることが原因。URL の後方互換を優先して `subtitle` で上書きする形に
- `setUp()` の `markTestIncomplete()` はクラス丸ごとを殺し、CI は緑のまま

テストを止めるのは、そのとき最も安く見える選択肢です。返済は後から来ます。

:::message alert
EC-CUBE 4.4 はこの記事を書いている時点（2026年8月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
