---
title: "EC-CUBE の会員に親子関係を持たせて、会社単位で発注させる"
emoji: "🏢"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "doctrine"]
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

BtoB のサイトでは、買うのは「人」ではなく「会社」です。卸価格も、支払方法も、締めも会社ごとに決まっていて、実際に画面を触る担当者は何人もいる。ところが EC-CUBE の会員は、どこまでいっても1人1アカウントです。

この隙間を埋めるために、[取引先アカウント管理プラグイン](https://github.com/kurozumi/eccube-plugin-b2b-company)を作りました。会員に親子関係を持たせて、親を会社、子を担当者として扱います。

コードはすべて公開しているので、この記事では機能の紹介より、**なぜその作りにしたか**のほうを書きます。EC-CUBE の会員まわりを拡張するときに同じ壁に当たる話がいくつかあります。

## 取引先エンティティを作らなかった

最初に迷ったのはここです。`dtb_b2b_company` のようなテーブルを新しく作って、会員をそこに紐付けるほうが素直に見えます。

作らなかった理由は、価格の根拠が二重になるからです。EC-CUBE の卸価格は会員グループで決まります（[会員グループ管理プラグイン](https://github.com/kurozumi/eccube-plugin-customer-group)を入れた場合）。ここに会社エンティティを足すと、「この会員の価格は会員グループで決まるのか、所属する会社で決まるのか」という問いが生まれます。答えを1つに保つ自信がなかったので、会社という箱を作らず、会員そのものに親を持たせました。

```php
#[EntityExtension(\Eccube\Entity\Customer::class)]
trait CustomerTrait
{
    #[ORM\ManyToOne(targetEntity: \Eccube\Entity\Customer::class, inversedBy: 'ChildCustomers')]
    #[ORM\JoinColumn(name: 'parent_customer_id', referencedColumnName: 'id', nullable: true, onDelete: 'RESTRICT')]
    private $ParentCustomer;

    #[ORM\OneToMany(targetEntity: \Eccube\Entity\Customer::class, mappedBy: 'ParentCustomer')]
    private $ChildCustomers;
}
```

`Customer` から `Customer` への自己参照です。親を持たない会員が取引先の管理者、親を持つ会員がその担当者。それだけ。

### onDelete は RESTRICT にした

`SET NULL` にすると、担当者がぶら下がっている取引先を管理画面から削除できてしまいます。残された担当者は会社名も会員グループも持ったまま親だけを失って、取引先一覧に独立した会社として並びます。卸価格のグループが付いたままなので、会社が存在しないのに卸価格で発注できる。

`RESTRICT` にすると本体が「関連するデータがあるため削除できませんでした」と出して止まります。取引先をやめるときは削除ではなく退会を使ってもらう、という運用に寄せました。

## 「取引先である」の判定を1か所に集める

これが一番やり直した部分です。

最初は場所によって判定がばらばらでした。ある画面では「担当者が1人以上いる会員」、別の画面では「会社名が入っている会員」。どちらも単独では使えません。

- 担当者の有無だけで見ると、取引先は必ず担当者0人から始まるので、**最初の1人を自分で追加できない**。自己登録した取引先はこれで詰みます
- 会社名だけで見ると、本体の会員登録にも会社名の欄があるので、**登録時に勤務先を書いただけの個人会員が担当者を発行できてしまう**

そこで `companyAccount` という印を足して、条件を3つ揃えました。

```php
public function isCompany(Customer $Customer): bool
{
    if (null !== $Customer->getParentCustomer()) {
        return false;
    }

    if ('' === trim((string) $Customer->getCompanyName())) {
        return false;
    }

    return $Customer->isCompanyAccount() || !$Customer->getChildCustomers()->isEmpty();
}
```

会社名を条件に残したのは、表示と権限を揃えるためです。取引先一覧も会員一覧の印も会社名で出し分けているので、会社名だけ空にすると画面上は個人に見えるのに取引先の権限だけ残る、という気持ち悪い状態になります。

3つめが `||` なのは、印の無い既存データを切り捨てないためです。会員編集で親を指定して手で組んだ取引先には印が付いていません。

### 同じ判定が2か所にある

一覧の絞り込みは会員を全部読み込むわけにいかないので、SQL 側にも同じ条件が要ります。

```php
public static function companyCondition(string $alias): string
{
    return sprintf(
        '%1$s.ParentCustomer IS NULL'
        .' AND %1$s.company_name IS NOT NULL'
        ." AND TRIM(%1\$s.company_name) != ''"
        .' AND (%1$s.companyAccount = true'
        .' OR EXISTS (SELECT company_condition_child.id FROM %2$s company_condition_child'
        .' WHERE company_condition_child.ParentCustomer = %1$s))',
        $alias,
        Customer::class
    );
}
```

`isCompany()` はまだ保存していないオブジェクトにも答えないといけないので PHP が要る。絞り込みは読み込む前に篩にかけたいので DQL が要る。どちらか一方には寄せられません。

寄せられないなら、ずれたときに気づけるようにする。両者を総当たりで突き合わせるテストを1本置いて、条件を足すときは対で直せばテストが通る、という形にしました。

## Doctrine の onFlush で殴られた話

会員グループの継承で、けっこう長く詰まりました。

やりたいことは単純です。既存の会員に「所属する取引先」を指定したら、その会社の会員グループと会社情報を引き継ぐ。ところが会員編集で親を選んだとき、変更として現れるのは `ParentCustomer` の付け替えだけです。エンティティはすでに存在しているので `prePersist` は走りません。

`onFlush` で拾うところまではすぐでした。問題はその場で書き込もうとしたときです。

- `computeChangeSet()` を呼ぶと、すでに計算済みの変更を作り直してしまい、**`ParentCustomer` の変更ごと消える**。グループだけ引き継がれて、担当者にならない
- `recomputeSingleEntityChangeSet()` なら親は残るものの、**会員グループの多対多が書き込まれない**。コレクションを書き出す予定は `onFlush` に入る前に決まっていて、あとから積む口（`scheduleCollectionUpdate()`）は公開されていない

どちらも例外は出ません。片方だけ保存されて静かに壊れます。

結局、`onFlush` では見つけるだけにして、`postFlush` でもう一度 flush する形に落ち着きました。

```php
public function onFlush(OnFlushEventArgs $args): void
{
    $uow = $args->getObjectManager()->getUnitOfWork();

    foreach ($uow->getScheduledEntityUpdates() as $entity) {
        if (!$entity instanceof Customer) {
            continue;
        }

        $changeSet = $uow->getEntityChangeSet($entity);
        if (!isset($changeSet['ParentCustomer'])) {
            continue;
        }

        if (!$changeSet['ParentCustomer'][1] instanceof Customer) {
            continue;
        }

        $this->pending[] = $entity;
    }
}

public function postFlush(PostFlushEventArgs $args): void
{
    $pending = $this->pending;
    $this->pending = [];

    // 自分が起こした flush で呼ばれた分は積み直さない
    if ([] === $pending || $this->flushing) {
        return;
    }

    // ... 引き継いで ...

    $this->flushing = true;
    try {
        $args->getObjectManager()->flush();
    } finally {
        $this->flushing = false;
    }
}
```

`$this->flushing` のフラグが無いと、自分で呼んだ flush の `postFlush` でまた同じことをやって無限に回ります。

なお、親を外したときは何もしません。取引先から切り離しただけで卸価格まで消えると、切り離した側が意図していない値引き停止が起きるからです。

### グループの変更を捕まえる場所

取引先側のグループを後から変えたときも担当者に配りたい。ただし変え方は管理画面の会員編集だけではなく、CSV取込も、他プラグインからの独自コードもあります。どこから変えても効かせたいので、ORM が変更を書き出す直前で捕まえます。

多対多の付け外しはエンティティ自身の changeSet には現れず、コレクションの変更として出てきます。

```php
foreach ($uow->getScheduledCollectionUpdates() as $collection) {
    $parent = $this->parentOf($collection);
    // ...
}

foreach ($uow->getScheduledCollectionDeletions() as $collection) {
    $parent = $this->parentOf($collection);
    // ...
}
```

配り方は「足す」ではなく「合わせる」にしました。足すだけにすると、取引先をグループから外したときに担当者だけ卸価格のまま残ります。担当者ごとに違うグループを当てる運用はできなくなりますが、会社単位で価格が決まるという前提のほうを採っています。

## 担当者に触らせない画面を塞ぐ

担当者には触らせたくない画面があります。退会手続きと、お届け先の登録。会社が決めた出荷先以外へ商品を流されると困るので。

テンプレートからリンクを消すだけでは、URL を直接叩けば開けます。実際に止めるのは `kernel.controller` です。

```php
private const GUARDED_ROUTES = [
    'mypage_withdraw' => 'withdraw',
    'mypage_delivery' => 'delivery',
    // 購入手続きから届け先を新規登録する
    'shopping_shipping_edit' => 'delivery',
    'shopping_shipping_multiple_edit' => 'delivery',
    // 購入手続きから既存の届け先を書き換える・消す
    'shopping_shipping_customer_address' => 'delivery',
];
```

ここで自分が踏んだ穴が、**お届け先の登録口はマイページだけではない**ことです。購入手続きの中にも `shopping_shipping_edit` と `shopping_shipping_multiple_edit` という新規登録の口があります。マイページだけ塞いだ状態では、担当者は購入手続きから任意の住所を登録して、そこへ出荷させられました。

ルート名の前方一致で見ているのは、確認・完了の画面まで拾いたいからです。ただし `shopping_shipping` と `shopping_shipping_multiple` には当ててはいけません。あれは登録済みの届け先から選んだり商品を振り分けたりする画面で、届け先そのものは増えない。ここを塞ぐと複数お届け先の運用ごと止まります。接頭辞に `_edit` や `_customer_address` まで含めてあるのはそのためです。

止めるときは 404 ではなく `AccessDeniedHttpException` を投げています。404 にすると、店側が設定で閉じたのか本体の不具合なのか切り分けられません。

テンプレート側は、押しても 403 になるリンクを並べておかないための後始末という位置づけです。ただし購入手続き一覧の「お届け先を追加する」ボタンだけは消しません。あれは追加ボタンではなく複数お届け先画面への導線で、担当者でも会社が登録した届け先の間で商品を振り分けられます。ラベルが嘘をついているだけなので、文言だけ差し替えました。

## 受注に取引先を控える

会社単位の注文履歴を、いまの親子関係で引くと壊れます。

担当者 A が B 社から C 社へ移ったとします。所属を付け替えた瞬間、A が B 社在籍中に出した注文が C 社の管理者に見えるようになる。逆に、B 社の管理者からは A の注文が消えます。どちらも会社の履歴としては誤りです。

なので受注の側に、その時点の取引先を控えます。

```php
#[EntityExtension(\Eccube\Entity\Order::class)]
trait OrderTrait
{
    /** 受注時点の取引先の会員ID。参照整合性は持たない */
    #[ORM\Column(name: 'company_account_id', type: 'integer', nullable: true, options: ['unsigned' => true])]
    private $companyAccountId;

    /** 受注時点の取引先の会社名 */
    #[ORM\Column(name: 'company_account_name', type: 'string', length: 255, nullable: true)]
    private $companyAccountName;
}
```

外部キーは張っていません。`dtb_order` は拡張が最も集中するテーブルで、外部キーを張るとアンインストール時にテーブルを落とせなくなったり、他プラグインの導入でスキーマが作り直されたときに設定が戻ったりします。会員が削除されても名前だけは残したいので、ID と名前の両方を素の値で持っています。

書き込みは購入フローの `ItemHolderPreprocessor` で。一度控えたら書き換えません。

```php
public function process(ItemHolderInterface $itemHolder, PurchaseContext $context): void
{
    if (!$itemHolder instanceof Order) {
        return;
    }

    if (null !== $itemHolder->getCompanyAccountId()) {
        return;
    }

    $Customer = $itemHolder->getCustomer();
    if (!$Customer instanceof Customer) {
        return;
    }

    $Company = $this->hierarchy->findRoot($Customer);

    if (!$this->hierarchy->isCompany($Company)) {
        return;
    }

    $itemHolder->setCompanyAccountId($Company->getId());
    $itemHolder->setCompanyAccountName($Company->getCompanyName());
}
```

本体が受注管理用メモを明細へ写しているのと同じ考え方です。あとから変わりうるものは、受注の側に固定する。

引く側は控えを優先し、控えの無い受注（この機能を入れる前のもの）だけ従来どおり顔ぶれで拾います。

```php
$qb->andWhere($qb->expr()->orX(
    $qb->expr()->eq($alias.'.companyAccountId', ':b2bCompanyAccountId'),
    $qb->expr()->andX(
        $qb->expr()->isNull($alias.'.companyAccountId'),
        $qb->expr()->in($alias.'.Customer', ':b2bCompanyMemberIds')
    )
));
```

この絞り込みは `OrderVisibilityScopeInterface` として切り出して、`#[AsTaggedItem(priority: 0)]` で登録しています。「部署単位で見せたい」「役職者だけ全体を見せたい」といった要望は、大きい priority で自作のスコープを足せば先に効きます。

取引先名は受注CSV・配送CSVの項目としても登録済みです。既定は「出力しない」なので既存のCSVの列は増えません。

## 連鎖退会をどこで拾うか

取引先が退会したら担当者もまとめて退会させる、という機能があります。EC-CUBE の退会は会員を消すのではなく状態を変えるだけなので、放っておくと退会した会社の担当者がそのままログインして発注できてしまいます。

最初は `FRONT_MYPAGE_WITHDRAW_INDEX_COMPLETE` だけを拾っていました。これがほぼ空振りでした。

法人の担当者がマイページから自分で退会することは、まずありません。取引終了は営業への連絡で起きて、店側が管理画面で会員のステータスを退会に切り替えます。つまり `ADMIN_CUSTOMER_EDIT_INDEX_COMPLETE` のほうが主経路です。設定を入れていても実際にはほとんど効かず、取引を切った会社の担当者が発注できる状態が残っていました。

```php
public static function getSubscribedEvents(): array
{
    return [
        EccubeEvents::FRONT_MYPAGE_WITHDRAW_INDEX_COMPLETE => 'onWithdrawComplete',
        EccubeEvents::ADMIN_CUSTOMER_EDIT_INDEX_COMPLETE => 'onAdminEditComplete',
    ];
}
```

管理画面側は保存のたびに走るので、ステータスが退会になったときだけに絞ります。連れて行くときはメールアドレスもダミーへ差し替えます。解放しないと、同じ人が別の取引先で登録し直せません。差し替え方は本体（`WithdrawController` と `CustomerEditController`）に揃えました。経路によってアドレスの残り方が違うと、運用でも移行でも扱いに困るので。

## 会員グループ管理は必須にしなかった

卸価格は会員グループで決まるので、実運用では[会員グループ管理プラグイン](https://github.com/kurozumi/eccube-plugin-customer-group)とセットになります。ただ依存は張っていません。

| 機能 | 会員グループ管理あり | なし |
| --- | --- | --- |
| 親子関係・会社情報の固定・連鎖退会・担当者アカウント | ○ | ○ |
| 取引先を作るときの会員グループ割り当て | ○ | 項目が出ません |
| 担当者への会員グループの継承・同期 | ○ | 何もしません |
| 取引先の自己登録（`/entry/company`） | ○ | グループ無しで登録されます |

コード上は `method_exists($Customer, 'getGroups')` で分岐しています。`EntityExtension` で足されたメソッドなので、プラグインが無ければ生えていません。

```php
if (!method_exists($Company, 'getGroups')) {
    return;
}
```

きれいなやり方ではありませんが、任意依存を扱う現実的な手だと思っています。

## インストール

```bash
composer require ec-cube/b2bcompany
bin/console eccube:plugin:install --code=B2BCompany
bin/console eccube:plugin:enable --code=B2BCompany
```

動作要件は EC-CUBE 4.4 系、PHP 8.2 / 8.3 です。

このプラグインは親子関係だけを持っていて、その上に載せるものは別に分けています。

- [発注承認アドオン](https://github.com/kurozumi/eccube-plugin-b2b-order-approval)：担当者の発注を承認待ちで止め、上長が承認してから店舗へ流します
- [月締め請求管理アドオン](https://github.com/kurozumi/eccube-plugin-b2b-billing)：取引先単位で受注をまとめて請求します
- [会員登録承認制](https://github.com/kurozumi/eccube-plugin-customer-approval)：取引先登録ページからの申し込みを仮会員で止めます

「誰が誰の下にいるか」を1か所で持っておくと、その上に載る話がだいぶ楽になります。承認も締めも、結局は同じ親子関係を見ているだけなので。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
