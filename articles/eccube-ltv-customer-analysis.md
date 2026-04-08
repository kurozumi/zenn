---
title: "「全顧客に同じクーポン」はもう終わりに——EC-CUBEとGA4でLTV上位顧客の流入元を可視化する"
emoji: "📊"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

**「リピーター施策を打ちたいが、どこから来た顧客がリピートするのかわからない」**——そのまま全顧客に同じクーポンを配り続けることになる。

**結論から言う。** EC-CUBE 4.3 は顧客の累計購入金額を `buy_total` として標準で持っている。これと GA4 の `user_id` 連携を組み合わせると、「どの流入チャネルが LTV の高い顧客を生み出しているか」をコードほぼゼロで特定できる。

広告運用担当者が「Google 広告が効いている」と言っていても、実際には SEO 流入のほうが 1 年後の LTV が高い——という逆転は普通に起きる。この記事では、EC-CUBE のデータと GA4 を使ってその逆転を発見する手順を解説する。

:::details この記事で得られること（TL;DR）
- `dtb_customer.buy_total` がどのタイミングで更新されるか理解できる
- 管理画面だけで LTV 上位顧客の CSV を抽出できる
- GA4 の `purchase` イベントに顧客 ID を付与して流入元と LTV を紐付けられる
- デバイス別・購入回数別の LTV 傾向を DQL で集計できる
- 「高 LTV を生む流入チャネル」を特定し、広告費の再配分根拠にできる
:::

## EC-CUBE が標準で持つ LTV データ

EC-CUBE 4.3 の `Customer` エンティティ（`dtb_customer` テーブル）には、LTV関連フィールドが標準装備されている。

```php
// src/Eccube/Entity/Customer.php

/** @ORM\Column(name="buy_total", type="decimal", precision=12, scale=2, nullable=true, options={"unsigned":true,"default":0}) */
private $buy_total = '0';  // 累計購入金額

/** @ORM\Column(name="buy_times", type="decimal", precision=10, scale=0, nullable=true, options={"unsigned":true,"default":0}) */
private $buy_times = '0';  // 累計購入回数

/** @ORM\Column(name="first_buy_date", type="datetimetz", nullable=true) */
private $first_buy_date;   // 初回購入日

/** @ORM\Column(name="last_buy_date", type="datetimetz", nullable=true) */
private $last_buy_date;    // 最終購入日

/** @ORM\Column(name="point", type="decimal", precision=12, scale=0, options={"unsigned":false,"default":0}) */
private $point = '0';      // 保有ポイント
```

これらは `OrderRepository::updateOrderSummary()` によって再集計される。ただし呼び出しタイミングに注意が必要だ。

```php
// src/Eccube/Repository/OrderRepository.php

public function updateOrderSummary(Customer $Customer, array $OrderStatuses = [
    OrderStatus::NEW,
    OrderStatus::PAID,
    OrderStatus::DELIVERED,
    OrderStatus::IN_PROGRESS,
])
{
    try {
        $result = $this->createQueryBuilder('o')
            ->select('COUNT(o.id) AS buy_times, SUM(o.total) AS buy_total, MIN(o.id) AS first_order_id, MAX(o.id) AS last_order_id')
            ->where('o.Customer = :Customer')
            ->andWhere('o.OrderStatus in (:OrderStatuses)')
            ->setParameter('Customer', $Customer)
            ->setParameter('OrderStatuses', $OrderStatuses)
            ->groupBy('o.Customer')
            ->getQuery()
            ->getSingleResult();
    } catch (NoResultException $e) {
        // 受注データが存在しなければ初期化
        $Customer->setFirstBuyDate(null);
        $Customer->setLastBuyDate(null);
        $Customer->setBuyTimes(0);
        $Customer->setBuyTotal(0);
        return;
    }

    $FirstOrder = $this->find(['id' => $result['first_order_id']]);
    $LastOrder  = $this->find(['id' => $result['last_order_id']]);

    $Customer->setBuyTimes($result['buy_times']);
    $Customer->setBuyTotal((string) $result['buy_total']); // decimal(12,2) のため string
    $Customer->setFirstBuyDate($FirstOrder->getOrderDate());
    $Customer->setLastBuyDate($LastOrder->getOrderDate());
}
```

**呼び出し元は管理画面のみ。** `updateOrderSummary()` は `Admin/Order/EditController`（受注編集）と `Admin/Order/OrderController`（受注一覧のクイック更新）からしか呼ばれていない。フロントエンドの購入完了時（`ShoppingController`）には呼ばれない。

つまり更新タイミングは次のとおりだ。

| タイミング | buy_total の更新 |
|---|---|
| 顧客がフロントで購入完了 | ❌ 更新されない |
| 管理画面で受注のステータスを変更 | ✅ 更新される |

「新規→入金済み」「入金済み→発送済み」など、どのステータス変更でも呼ばれる。集計対象は `NEW / PAID / DELIVERED / IN_PROGRESS` の受注で、管理者がその受注を一度でも操作した後に初めて `buy_total` へ反映される。

> **注意:** 顧客が購入してから管理者がステータスを変更するまでの間、`buy_total` は古い値のままになる。リアルタイム性が必要な分析には、`dtb_order` を直接集計するクエリを使うほうが正確だ。

## 管理画面でLTV上位顧客を抽出する

管理画面の「会員管理」では `buy_total_start` / `buy_total_end` による絞り込みが標準で使える。

`CustomerRepository::getQueryBuilderBySearchData()` が以下の条件をサポートしている。

```php
// 使える検索条件（searchData のキー）
[
    'buy_total_start'          => '100000',   // 累計購入金額 ○円以上
    'buy_total_end'            => '500000',   // 累計購入金額 ○円以下
    'buy_times_start'          => '3',        // 購入回数 ○回以上
    'buy_times_end'            => null,
    'last_buy_datetime_start'  => new \DateTime('-6 months'),  // 直近6ヶ月以内に購入
    'last_buy_datetime_end'    => null,
]
```

管理画面の「会員管理 > 検索」から「累計購入金額」の下限を設定し、CSV エクスポートするだけで LTV 上位顧客リストが作れる。

## DQL でセグメント別 LTV を集計する

プラグインや独自の分析画面を作る場合、以下のような DQL でセグメント別の LTV 分布を把握できる。

### 購入回数別の平均 LTV

```php
use Eccube\Entity\Customer;
use Doctrine\ORM\EntityManagerInterface;

class CustomerLtvAnalyzer
{
    public function __construct(
        private EntityManagerInterface $em,
    ) {}

    /**
     * 購入回数ごとの平均LTV・顧客数を集計する。
     */
    public function getLtvByBuyTimes(): array
    {
        return $this->em->createQueryBuilder()
            ->select('c.buy_times, COUNT(c.id) AS customer_count, AVG(c.buy_total) AS avg_ltv')
            ->from(Customer::class, 'c')
            ->where('c.buy_times > 0')
            ->groupBy('c.buy_times')
            ->orderBy('c.buy_times', 'ASC')
            ->getQuery()
            ->getArrayResult();
    }

    /**
     * LTV 上位 N 件の顧客を取得する。
     */
    public function getTopLtvCustomers(int $limit = 100): array
    {
        return $this->em->createQueryBuilder()
            ->select('c')
            ->from(Customer::class, 'c')
            ->where('c.buy_times >= 2')
            ->orderBy('c.buy_total', 'DESC')
            ->setMaxResults($limit)
            ->getQuery()
            ->getResult();
    }
}
```

### 初回購入からの経過日数と LTV の関係

初回購入から最終購入までの経過日数が長い顧客ほど LTV が高い傾向がある。以下のクエリで確認できる。

```php
// DBAL を使った生 SQL（日数計算は DB 依存のため DBAL が適切）
use Doctrine\DBAL\Connection;

$sql = "
    SELECT
        DATEDIFF(last_buy_date, first_buy_date) AS lifetime_days,
        COUNT(id)                               AS customer_count,
        AVG(buy_total)                          AS avg_ltv
    FROM dtb_customer
    WHERE buy_times >= 2
      AND first_buy_date IS NOT NULL
      AND last_buy_date IS NOT NULL
    GROUP BY DATEDIFF(last_buy_date, first_buy_date)
    ORDER BY lifetime_days ASC
";

$result = $connection->executeQuery($sql)->fetchAllAssociative();
```

> DATEDIFF は MySQL 構文です。PostgreSQL を使う場合は `(last_buy_date - first_buy_date)` を使ってください。

## デバイス別の購入傾向を把握する

`dtb_order` には `device_type_id` が記録されており、注文がスマートフォンから来たかPCから来たかを区別できる。

```php
// src/Eccube/Entity/Master/DeviceType.php
class DeviceType extends AbstractMasterEntity
{
    public const DEVICE_TYPE_MB = 2;   // スマートフォン
    public const DEVICE_TYPE_PC = 10;  // PC
}
```

デバイス別の LTV 傾向を集計するには、`dtb_order` と `dtb_customer` を JOIN する。

```php
use Eccube\Entity\Order;
use Eccube\Entity\Master\DeviceType;

$result = $this->em->createQueryBuilder()
    ->select(
        'dt.id AS device_type_id',
        'COUNT(DISTINCT o.Customer) AS customer_count',
        'AVG(c.buy_total) AS avg_ltv',
        'AVG(c.buy_times) AS avg_buy_times',
    )
    ->from(Order::class, 'o')
    ->join('o.Customer', 'c')
    ->join('o.DeviceType', 'dt')
    ->where('c.buy_times >= 1')
    ->groupBy('dt.id')
    ->getQuery()
    ->getArrayResult();
```

「スマートフォンで初回購入した顧客の方がLTVが高い」といった傾向が見えてくることがある。

## 流入元分析は GA4 で行う

EC-CUBE の `dtb_order` および `dtb_customer` には UTM パラメータや参照元 URL を格納するフィールドが**標準では存在しない**。流入元（Google 広告・SNS・SEO など）の分析は GA4 側で行う必要がある。

EC-CUBE 4.3 には `Block/google_analytics.twig` が標準で存在し、管理画面から設定した `BaseInfo.ga_id` を使ってページビューを計測している。ただし ecommerce イベント（`purchase` など）の送信は実装されていないため、注文完了画面に追記が必要になる。

### GA4 の purchase イベントに customer_id を付与する

注文完了画面（`Shopping/complete.twig`）で GA4 の `purchase` イベントを送信する際に、EC-CUBE の顧客 ID を `user_id` として渡すことで、GA4 のレポートと EC-CUBE の顧客データを紐付けられる。

```twig
{# src/Eccube/Resource/template/default/Shopping/complete.twig #}
{% block main %}
  {# ... 既存のHTML ... #}

  <script>
    // GA4 purchase イベント
    gtag('config', 'G-XXXXXXXXXX', {
      {% if app.user %}
      {# 顧客IDは整数だが、JS文字列コンテキストに出力するため |e('js') を付与する #}
      'user_id': '{{ app.user.id|e('js') }}',
      {% endif %}
    });

    gtag('event', 'purchase', {
      transaction_id: '{{ Order.orderNo|e('js') }}',
      value:          {{ Order.paymentTotal|default(0) }},
      currency:       '{{ Order.currencyCode|e('js') }}',
      items: [
        {% for item in Order.productOrderItems %}
        {
          item_id:   '{{ item.productClass.id|e('js') }}',
          item_name: '{{ item.productName|e('js') }}',
          price:     {{ item.priceIncTax|default(0) }},
          quantity:  {{ item.quantity|default(0) }},
        },
        {% endfor %}
      ],
    });
  </script>
{% endblock %}
```

> `app.user` はログイン中の顧客エンティティを返します。ゲスト購入の場合は `null` になります。
>
> **注意:** `user_id` に EC-CUBE の顧客 ID（主キー）をそのまま使用する場合、HTML ソースや GA4 のデバッグ画面から顧客 ID が第三者に見える可能性があります。セキュリティ要件が厳しい場合は、Controller 側で HMAC などによるハッシュ値を生成してテンプレートに渡し、生の主キーを露出しない設計を検討してください。また、GA4 への `user_id` 送信は個人情報の第三者提供に該当する場合があるため、プライバシーポリシーへの明記と同意取得が必要です。

### GA4 でのセグメント分析手順

1. GA4 の「探索」>「ユーザー探索」を開く
2. セグメントに「purchase イベントを2回以上実施したユーザー」を設定
3. ディメンションに「セッションのデフォルト チャネル グループ」を追加
4. 指標に「購入による収益」「トランザクション数」を追加
5. チャネル別の LTV・購入回数を比較する

`user_id` を設定しておくことで、同一顧客が複数デバイスで購入した際もGA4側で名寄せされ、より正確なLTV分析ができる。

## 高LTV顧客の典型的な行動パターン

EC-CUBE のデータと GA4 を合わせて分析すると、高 LTV 顧客には以下のような共通パターンが見えてくることが多い。

- **初回購入から2回目購入までの期間が短い**（30日以内）
- **特定の商品カテゴリから入っている**（入口商品の存在）
- **メルマガ経由で戻ってくる割合が高い**（メール施策との相性）
- **スマートフォンで閲覧してPCで購入する**（デバイスをまたいだ行動）

これらのパターンを把握することが、リピーター施策の設計に直結する。

## 分析結果をリピーター施策に活かす

| 分析結果 | 施策例 |
|---|---|
| オーガニック検索流入のLTVが高い | SEO強化・コンテンツマーケティング予算を増加 |
| 初回購入後30日以内にメール開封した顧客がリピートしやすい | 初回購入後30日フォローメールの内容を改善 |
| 特定カテゴリ購入者のLTVが高い | そのカテゴリへの広告費を集中投下 |
| スマートフォンユーザーのリピート率が高い | アプリ・プッシュ通知の導入を検討 |

「全顧客に同じ施策」から「LTVデータを根拠にしたセグメント別施策」への転換が、限られたリソースで最大の効果を生む。

## まとめ

- EC-CUBE の `dtb_customer` には `buy_total`（累計購入金額）・`buy_times`・`first_buy_date`・`last_buy_date` が標準装備されており、そのままLTV分析に使える
- 管理画面の会員検索で `buy_total` の範囲指定が使えるため、コードなしで高LTV顧客のCSV出力が可能
- デバイス別傾向は `dtb_order.device_type_id`（MB=2 / PC=10）で分析できる
- 流入元分析はEC-CUBEのDBには記録されないため、GA4の `purchase` イベントに `user_id`（顧客ID）を付与して連携する
- 分析の目的は「高LTV顧客を生む流入チャネル・行動パターンの特定」→「同じパターンを量産する施策設計」

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
