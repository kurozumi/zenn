---
title: "EC-CUBE商品ページに★を出す方法、実は4.4で本体に組み込まれていた"
emoji: "🔍"
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
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## 結論: レビュープラグインが「星」をGoogle検索結果に出せるようになります

「レビュー機能を実装したのに、検索結果に★が出ない」――EC-CUBEでレビュー・口コミプラグインを作ったことがある人なら、一度はこの壁にぶつかったのではないでしょうか。原因は、商品詳細ページのJSON-LD(構造化データ)にプラグイン側から `aggregateRating` を差し込む手段が本体になかったことです。結果として、Google検索結果に★を出したければ `detail.twig` のJSON-LDをプラグインが丸ごと上書きするという、壊れやすく保守しづらい実装を強いられてきました。

EC-CUBE 4.4(未リリース)では、この状況が変わります。商品詳細ページのJSON-LDがGoogleの商品構造化データ仕様に沿って本体側で拡充され、**プラグインからは新設イベント1本に評価データを渡すだけ**で★表示に対応できるようになりました。

**TL;DR**
- **新設イベント `front.product.detail.json_ld` で、レビュープラグインから `aggregateRating` / `review` を注入できるようになる**(本体テンプレートの改変が不要に)
- EC-CUBE 4.4本体の商品詳細ページで、JSON-LD(`schema.org/Product`)がGoogle商品構造化データ仕様に沿って拡充される([PR #6883](https://github.com/EC-CUBE/ec-cube/pull/6883)、`4.4` ブランチにマージ済み)
- 組み立てロジックは新設の `ProductStructuredDataService` に集約され、単体テストで検証可能な設計になっている
- セール中の商品は `priceSpecification` で取消線価格を表現。ただし規格違いの価格帯表現に使われた `AggregateOffer` は、Googleの仕様上は非推奨パターンに該当する(詳細は本文)
- `json_ld` Twigフィルタは `JSON_HEX_TAG` 等でエスケープしており、構造化データ経由のXSSにも対策済み
- **現時点(2026年7月)で EC-CUBE 4.4 は未リリース**。`ProductStructuredDataService` は4.3系には存在しない

## この記事の位置づけ(重要)

この機能は EC-CUBE 本体リポジトリの [PR #6883](https://github.com/EC-CUBE/ec-cube/pull/6883)(Closes #6149)として実装され、**`4.4` ブランチにマージ済み**です。GitHub上で実際に確認したところ、`4.3` 系ブランチには `ProductStructuredDataService.php` は存在せず、`EccubeExtension.php` にも `json_ld` フィルタはありません。

つまりこの記事も「次バージョンで入る予定の実装を先取りして読む」記事です。実際のリリース時には細部が変わる可能性がある点にご注意ください。

## なぜ商品詳細ページにJSON-LDが要るのか

Googleは商品ページに構造化データ(JSON-LD)を埋め込むことで、検索結果に価格・在庫・評価などをリッチリザルトとして表示できるようにしています。Google公式ドキュメントでは用途によって2種類の仕様が案内されています。

- **Product snippet**(商品を直接購入できないページ向け): `name` に加えて `review` / `aggregateRating` / `offers` のいずれかが必須
- **Merchant listing**(その場で購入できるページ向け): `name` / `image` / `offers`(`Offer` 型)が必須。`Offer` の中に `price`(または `priceSpecification.price`)と `priceCurrency` が必須

EC-CUBEの商品詳細ページは「その場で購入できるページ」なので、基本的にはMerchant listing側の要件を満たす形で実装されています。ただし後述するAggregateOfferの扱いのように、両仕様の間で解釈に注意が必要な箇所もあります。

## 実装方針: Fatコントローラを避けてテスト可能にする

このPRの設計面での特徴は、JSON-LDの組み立てロジックを**`ProductStructuredDataService`という単体テスト可能なビルダークラスに集約**したことです。

- `ProductController::detail` はビルダを呼び出し、戻り値をテンプレート変数として渡すだけ
- Twig側は `json_ld` フィルタで `json_encode` するだけの薄いアダプタ

以前は `detail.twig` にJSON文字列を直接組み立てるロジックが書かれていましたが、これをサービスクラスに切り出すことで、絶対URLや通貨コードといったHTTPリクエスト依存の値も引数として受け取る形にし、PHPUnitで戻り値の配列を直接アサートできるようにしています。実際に8件のテストケース(`ProductStructuredDataServiceTest.php`)が追加されています。

## 実装を読む: ProductStructuredDataService

中心となる `createProductJsonLd()` メソッドは次のような構成です(実際のソースから抜粋)。

```php
public function createProductJsonLd(Product $Product, string $baseUrl, string $productUrl, string $currency): array
{
    $Product->_calc();

    $data = [
        '@context' => 'https://schema.org/',
        '@type' => 'Product',
        'name' => $Product->getName(),
        'image' => $this->buildImages($Product, $baseUrl),
    ];

    // description, sku, category, offers を条件付きで追加していく

    // プラグイン等が aggregateRating / review 等を配列へ注入するための拡張点
    $event = new EventArgs(['json_ld' => $data, 'Product' => $Product]);
    $this->eventDispatcher->dispatch($event, EccubeEvents::FRONT_PRODUCT_DETAIL_JSON_LD);
    $data = $event->getArgument('json_ld');

    return $data;
}
```

イベントは `$data` 配列を組み上げた**直後、returnする前**に発行されます。プラグインが割り込む余地を、配列の最終形が固まった段階に限定しているのがポイントです。

### 価格: Offer と AggregateOffer の出し分け

もっとも実装として作り込まれているのが価格まわりです。`buildOffers()` の該当部分を見てみます。

```php
private function buildOffers(Product $Product, string $productUrl, string $currency): ?array
{
    $priceMin = $Product->getPrice02IncTaxMin();
    if ($priceMin === null) {
        return null; // 価格が取得できない商品は offers 自体を出さない
    }
    $priceMax = $Product->getPrice02IncTaxMax();
    $availability = $Product->getStockFind() ? 'InStock' : 'OutOfStock';

    // 規格(バリエーション)で価格が異なる商品は AggregateOffer
    if ($priceMax !== null && (float) $priceMin !== (float) $priceMax) {
        return [
            '@type' => 'AggregateOffer',
            'url' => $productUrl,
            'priceCurrency' => $currency,
            'lowPrice' => $priceMin,
            'highPrice' => $priceMax,
            'offerCount' => $this->countVisibleProductClasses($Product),
            'availability' => $availability,
            'itemCondition' => 'NewCondition',
        ];
    }

    $offers = [
        '@type' => 'Offer',
        'url' => $productUrl,
        'priceCurrency' => $currency,
        'price' => $priceMin,
        'availability' => $availability,
        'itemCondition' => 'NewCondition',
    ];

    // 通常価格(price01) > 販売価格(price02) のときのみ取消線価格を付与（税込同士で比較）
    $listPrice = $Product->getPrice01IncTaxMin();
    if ($listPrice !== null && (float) $listPrice > 0 && (float) $listPrice > (float) $priceMin) {
        $offers['priceSpecification'] = [
            '@type' => 'UnitPriceSpecification',
            'priceType' => 'StrikethroughPrice',
            'price' => $listPrice,
            'priceCurrency' => $currency,
        ];
    }

    return $offers;
}
```

読み解くポイントは3つです。

**1. 価格が取れない商品は `offers` を出さない**

`$priceMin === null` の場合は即 `null` を返し、呼び出し元(`createProductJsonLd`)も `offers` キー自体を出力しません。Merchant listingの要件は「`offers` を出すなら `price` が必須(かつ0より大きい)」であり、無理に `price: 0` を出すよりは、そもそも `offers` を出さない方が仕様違反を避けられます。

**2. 単一価格は `Offer`、価格帯は `AggregateOffer`**

規格(色・サイズなど)によって価格が異なる商品は `AggregateOffer` で `lowPrice`/`highPrice`/`offerCount` を出力します。`offerCount` は単純な規格数ではなく、`countVisibleProductClasses()` という専用メソッドで「規格自体が非表示でなく、かつ紐づくクラスカテゴリ1・2も非表示でない」ものだけを数えています。非公開の規格が件数に混ざらないよう配慮された実装です。

ここで一つ、実装上かなり重要な注意点があります。Google公式のMerchant listingドキュメントには次の一文があります。

> "Product snippets accept an `Offer` or `AggregateOffer` but merchant listings require an `Offer` as the merchant has to be the seller of the product in order to be eligible for merchant listing experiences."

つまり「言及がない」のではなく、**Merchant listing(購入可能ページ)では `AggregateOffer` は要件を満たさないと明記されています**。さらにProduct snippet側のドキュメントには、こう釘を刺す一文まであります。

> "Don't use `AggregateOffer` to describe a set of product variants."

これはまさに、今回EC-CUBEが実装した「規格(バリエーション)違いの価格帯を `AggregateOffer` で表現する」パターンそのものを名指しで非推奨としている記述です。EC-CUBEの商品詳細ページは「その場で購入できるページ」なのでMerchant listingの対象であり、その意味では規格違い商品の `AggregateOffer` 表現は、Googleが求めるMerchant listingとしての要件を満たしていない可能性が高いと考えられます。

もっとも、`AggregateOffer` 自体がschema.orgの語彙として不正というわけではなく、あくまで「Googleのリッチリザルト表示の要件に沿うかどうか」という話です。バリエーション商品を扱っている場合は、実装をそのまま信用せず、[リッチリザルトテスト](https://search.google.com/test/rich-results)で実際にMerchant listingとして認識されるかを個別に確認することを強くおすすめします。

**3. 取消線価格は税込同士で比較し、片方だけに`priceType`を付与**

セール価格の表現は、Googleの仕様に沿って `priceSpecification` に `UnitPriceSpecification` を1件追加し、`priceType: StrikethroughPrice` を付与する形です。ここで重要なのが「`price01`(通常価格)と`price02`(販売価格)を税込同士で比較し、通常価格の方が高い場合だけ付与する」という条件です。この条件がないと、たとえば通常価格が未設定(null)の商品や、実質値上げのケースで誤って「セール中」と表示してしまう可能性があります。

Google公式の例では現在価格と取消線価格をそれぞれ独立した `UnitPriceSpecification` として2件並べる形が示されていますが、EC-CUBEの実装では現在価格は `Offer.price` で表現し、`priceSpecification` には**取消線価格(元の価格)だけ**を1件持たせる形になっています。どちらもschema.org上の`Offer`の使い方としては成立しますが、この違いは実装を読むときに意識しておくとよいでしょう。

### description: HTML除去して300文字に丸める

```php
private function buildDescription(Product $Product): string
{
    $description = $Product->getDescriptionList() ?: $Product->getDescriptionDetail();
    // ...
    $description = strip_tags($description);
    $description = preg_replace('/\s+/u', ' ', $description) ?? $description;
    $description = trim($description);

    return mb_substr($description, 0, 300);
}
```

商品の紹介文(一覧用説明文が空なら詳細説明文にフォールバック)から `strip_tags()` でHTMLタグを除去し、連続する空白を1つに正規化した上で300文字に丸めています。管理画面でHTMLタグ付きの説明文を書いていても、そのままJSON-LDに漏れ出すことはありません。

### category: 親カテゴリを`>`で連結

```php
private function buildCategory(Product $Product): string|array|null
{
    // Category::getPath() で祖先カテゴリを辿り、" > " で連結
    // 複数カテゴリに属する商品は文字列配列、単一なら文字列、無ければ null
}
```

`Category::getPath()` で祖先を辿って `implode(' > ', $names)` するシンプルな実装です。「アイスサンド > フルーツ」のようなパンくず的な文字列になります。複数カテゴリに属する商品は配列になる点も、実装を見て初めて分かる仕様です。

## 出力側: json_ld フィルタとXSS対策

Twig側の実装はフィルタ1つに集約されています(`EccubeExtension.php`)。

```php
public function encodeJsonLd(array $data): string
{
    $json = json_encode(
        $data,
        JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE | JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT
    );

    if ($json === false) {
        log_error('JSON-LD のエンコードに失敗しました: '.json_last_error_msg());
        return '{}';
    }

    return $json;
}
```

テンプレート側の呼び出しはこうなっています(`detail.twig`)。

```twig
{% if product_json_ld is defined and product_json_ld %}
<script type="application/ld+json">{{ product_json_ld|json_ld }}</script>
{% endif %}
```

ここで効いているのが `JSON_HEX_TAG` フラグです。PHP公式マニュアルの説明では「すべての `<` および `>` を、それぞれ対応するUnicodeエスケープ表記(`U+003C`・`U+003E`)に変換する」とされています(HTMLエンティティに変換されるわけではない点に注意してください)。`<script type="application/ld+json">` の中身に商品名などのユーザー入力由来の文字列がそのまま埋め込まれる設計上、たとえば商品名に `</script><script>alert(1)</script>` のような文字列が含まれていた場合、エスケープなしで出力すると **HTMLパーサーが `</script>` の時点でscriptタグを閉じてしまい、後続の文字列がスクリプトとして実行されてしまう**という古典的なXSSパターンが成立します。`JSON_HEX_TAG` によって `<` `>` がUnicodeエスケープに変換されるため、HTMLパーサー上は `</script>` という文字列自体が現れず、この種の離脱型XSSを機械的に防いでいます。

実際、テストコード(`ProductStructuredDataServiceTest.php`)にも `name` に `evil</script><script>alert(1)</script>` を仕込み、出力に生の `</script>` / `<script>` が含まれないことを確認するテストケースが用意されています。地味ですが、構造化データを自前でテンプレートに直書きしていた頃には抜けがちな観点です。

`json_encode` が失敗した場合(不正なUTF-8混入など)は例外を投げず、ログに残した上で空の `{}` を返すようにしているのも、商品詳細ページ自体の表示を壊さないための実務的な配慮です。

## プラグイン開発者向け: レビュー機能との連携

このPRのもう一つの目玉が、新設イベント `EccubeEvents::FRONT_PRODUCT_DETAIL_JSON_LD`(文字列値: `front.product.detail.json_ld`)です。

```php
public const FRONT_PRODUCT_DETAIL_JSON_LD = 'front.product.detail.json_ld';
```

EC-CUBE本体にはレビュー・口コミ機能そのものは含まれていません(PR本文でも明示的に対象外とされています)。しかし、レビュープラグインが集計した平均評価・件数を、このイベント経由でJSON-LDに注入できるようになっています。テストコードから実際のリスナー実装パターンを確認できます。

```php
// プラグインのイベントリスナー実装イメージ
public function onProductDetailJsonLd(EventArgs $event): void
{
    $data = $event->getArgument('json_ld');

    // 自プラグインが集計した評価データを注入する
    $data['aggregateRating'] = [
        '@type' => 'AggregateRating',
        'ratingValue' => $averageRating,
        'reviewCount' => $reviewCount,
    ];

    $event->setArgument('json_ld', $data);
}
```

`services.yaml` 等でこのリスナーを `front.product.detail.json_ld` イベントに登録しておけば、`ProductStructuredDataService` が組み立てた配列に対して後から `aggregateRating` を足し込めます。本体側のテンプレートやコントローラを一切改変せず、イベントリスナーだけで完結する点が実装上のメリットです。

ただし、レビュー機能を実装する際はGoogleの評価に関するポリシーにも注意が必要です。公式ドキュメントには「レビュー対象の事業者自身がレビューを管理している場合、`Organization` 系の構造化データはリッチリザルト(星表示)の対象外になる」旨、また「評価は実際のユーザーから直接得られたものでなければならない」旨が明記されています。自作自演のダミーレビューを注入するような実装は、リッチリザルト非表示どころか、サイト全体の評価に悪影響を及ぼしかねません。

### 動作確認の方法

JSON-LDを実装・カスタマイズした際は、Googleの[リッチリザルトテスト](https://search.google.com/test/rich-results)にURLを入力するか、生成されたHTMLを貼り付けることで、構造化データの構文エラーやリッチリザルトとしての適格性を確認できます。本体のマージを待たずとも、同じ設計(`ProductStructuredDataService` 相当のビルダー + イベント注入)を自分のプラグインや4.3系のカスタマイズに先取りして組み込み、このツールで検証しておくと安心です。

## このPRが対象外とした範囲

PR本文には、今回スコープ外として派生Issueに分割された項目が明記されています。

- `Brand`(ブランド情報)
- `JAN`/`GTIN`(商品識別コード)
- `hasMerchantReturnPolicy`(返品ポリシー)
- `priceValidUntil`(セール価格の有効期限)
- `shippingDetails`(配送情報)
- `color`/`size`/`material` の型付け
- `availability` の段階表現(取り寄せ中等)
- レビュー機能本体(注入イベントの受け皿のみ今回で対応)

「新フィールドを増やさず今あるデータで出せる範囲」に責務を絞ったという方針通り、既存のエンティティにない情報(ブランド、JANコードなど)は今回のスコープに含まれていません。プラグインでこれらの項目を補いたい場合も、同じ `front.product.detail.json_ld` イベントを使って配列に追加していく形になります。

## おまけ: 仕様書に書いていない挙動、どこまで実測で確認していますか

`AggregateOffer` の一件のように、公式ドキュメントが名指しで非推奨としている実装が、テストコードも用意された上で本体にマージされてしまうことがあります。構造化データはコンパイルエラーにもテスト失敗にもならないため、こうしたズレは気づきにくいのが厄介なところです。

みなさんは構造化データを実装するとき、「動くには動くが仕様通りかどうか」をどこまでリッチリザルトテストの実測で確認していますか。この記事の指摘に誤りがあれば、ぜひコメントで教えてください。

## まとめ

- EC-CUBE 4.4(未リリース)で、商品詳細ページのJSON-LDがGoogleの商品構造化データ仕様に沿って拡充されます。
- 組み立てロジックは `ProductStructuredDataService` に集約され、価格分岐・取消線価格・カテゴリパスなどのロジックが単体テストで検証可能です。
- `json_ld` Twigフィルタは `JSON_HEX_TAG` 等でエスケープしており、構造化データ経由のscript離脱型XSSを防いでいます。
- 新設イベント `front.product.detail.json_ld` を使えば、レビュープラグインなどから `aggregateRating` をJSON-LDに注入できます。
- 規格違い商品の価格帯を `AggregateOffer` で表現していますが、Google公式ドキュメントはMerchant listingでの `AggregateOffer` 利用を要件外とし、バリエーション表現への使用も名指しで非推奨としています。バリエーション商品を扱う場合はリッチリザルトテストでの実測確認をおすすめします。
- ブランド・JAN/GTIN・返品ポリシーなど、既存データにない項目は今回のスコープ外で、今後の別PRに持ち越されています。

正式リリース時には実装が変わっている可能性があるため、最終的な仕様は公式のリリースノートや doc4.ec-cube.net でご確認ください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
