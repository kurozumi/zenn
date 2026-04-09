---
title: "EC-CUBEに誕生日イベントは存在しない——それでも自動クーポン配布を実現する正しい設計"
emoji: "🎂"
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

**「毎月、誰が誕生月か調べてクーポンを送っている」——そのオペレーション、今月で終わりにできます。**

EC-CUBE 4.3 には、誕生日を検知するイベントが存在しません。多くの開発者がこの事実に気づかず EventListener での実装を試みて行き詰まります。

**結論：Console コマンド + cron の組み合わせが正解です。**

公式クーポンプラグイン（`Plugin\Coupon42`）を使えば、顧客ごとにユニークなコードを生成し、1人1枚・当月末期限のクーポンをメール自動送信する仕組みが実現できます。この記事ではその具体的な実装を解説します。

> あなたの店舗では誕生日特典をどうやって運用していますか？コメント欄でぜひ教えてください。

:::details この記事で得られること（TL;DR）
- EC-CUBE に誕生日イベントが存在しない理由と正しい設計方針
- 誕生月の顧客を DQL で取得する方法（`EXTRACT(MONTH FROM c.birth)`）
- クーポンプラグインで「1人1枚の個人クーポン」を生成する実装
- Symfony Console コマンドのプラグイン内実装パターン
- cron でのスケジュール設定方法
:::

## 設計の前提：なぜ EventListener ではなく Console コマンドなのか

EC-CUBE のイベントシステム（`EccubeEvents`）を確認すると、**誕生日に関連するイベントは定義されていません**。会員の誕生日は「購入」「ログイン」のような操作に紐付いていないため、リアルタイムでのイベント発火ができません。

誕生日クーポンの実装には、以下の設計が適切です。

```
毎日 cron が実行
  ↓
php bin/console eccube:send-birthday-coupon
  ↓
当月誕生日の会員を取得（未送信のみ）
  ↓
会員ごとにユニークなクーポンコードを生成・保存
  ↓
クーポンコードをメールで送信
```

## クーポンプラグインの制約と解決策

公式クーポンプラグイン（`Plugin\Coupon42`）には**顧客IDへの直接割り当て機能がありません**。クーポンはコードを知っていれば誰でも使える設計です。

この制約を回避するために、**顧客ごとにユニークなクーポンコードを生成し、`coupon_use_time = 1`（残使用回数1回）で登録する**方法を採用します。

```
coupon_use_time = 1  → 1回しか使えない
coupon_cd が顧客ごとにユニーク → 実質的な個人クーポンになる
coupon_member = true → 会員のみ利用可能（ゲスト購入では使えない）
```

クーポンプラグインには `CouponService::generateCouponCd($length = 12)` が用意されており、ランダムなクーポンコードを生成できます。

> **クーポンコードの安全性**: `generateCouponCd()` の実際の乱数源をプラグインのソースで確認してください。クーポンは金銭的価値を持つため、推測困難性が重要です。暗号論的に安全でない実装の場合は `random_bytes()` を使った独自生成（例: `strtoupper(bin2hex(random_bytes(8)))`）に切り替えることを検討してください。

## 実装

### 1. 誕生月の顧客を取得するメソッドを追加する

プラグイン内の独自 Repository に、当月誕生日の顧客を取得するメソッドを追加します。

`CustomerRepository` への直接変更を避けるため、プラグインのサービスクラスで `EntityManagerInterface` を通じてクエリを発行します。

```php
<?php

namespace Plugin\BirthdayCoupon\Service;

use Doctrine\ORM\EntityManagerInterface;
use Eccube\Entity\Customer;

class BirthdayCouponService
{
    public function __construct(
        private EntityManagerInterface $em,
    ) {}

    /**
     * 今月が誕生月の会員を取得する。
     *
     * birth が null の会員は除外します。
     *
     * @return Customer[]
     */
    public function findBirthdayCustomersThisMonth(): array
    {
        $month = (int) (new \DateTime())->format('n');

        return $this->em->createQueryBuilder()
            ->select('c')
            ->from(Customer::class, 'c')
            ->where('EXTRACT(MONTH FROM c.birth) = :month')
            ->andWhere('c.birth IS NOT NULL')
            ->andWhere('c.Status = 2') // 本会員のみ（CustomerStatus::REGULAR = 2）
            ->setParameter('month', $month)
            ->getQuery()
            ->getResult();
    }
}
```

> **大規模サイトでの注意**: `getResult()` は全件をメモリに一括ロードします。顧客数が多い場合は `toIterable()`（Doctrine ORM 2.8+）を使ってストリーミング処理に切り替えてください。また、ループ内で定期的に `$this->em->clear()` を呼び出してエンティティキャッシュを解放することを推奨します。
```

> `EXTRACT(MONTH FROM ...)` は EC-CUBE 4.3 が `doctrine.yaml` でカスタム DQL 関数として登録している `Eccube\Doctrine\ORM\Query\Extract` によって使用できます。Doctrine ORM の標準機能ではありませんが、MySQL・PostgreSQL・SQLite の全てで動作します。`EXTRACT(DAY FROM ...)` も同様に使用可能です。

### 2. クーポンを生成して保存するメソッドを追加する

クーポンプラグインの `CouponService` と `EntityManagerInterface` を使って、顧客ごとにクーポンを生成します。

```php
<?php

namespace Plugin\BirthdayCoupon\Service;

use Doctrine\ORM\EntityManagerInterface;
use Eccube\Entity\Customer;
use Plugin\Coupon42\Entity\Coupon;
use Plugin\Coupon42\Service\CouponService;

class BirthdayCouponService
{
    public function __construct(
        private EntityManagerInterface $em,
        private CouponService $couponService,
    ) {}

    /**
     * 誕生日クーポンを生成して保存する。
     *
     * クーポンコードはランダムな12文字で生成します。
     * coupon_use_time=1 にすることで1人1回限りの利用を保証します。
     */
    public function createBirthdayCoupon(Customer $Customer): Coupon
    {
        $now = new \DateTime();
        // 有効期限: 当月末まで
        $endOfMonth = (clone $now)->modify('last day of this month')->setTime(23, 59, 59);

        $Coupon = new Coupon();
        $Coupon->setCouponCd($this->couponService->generateCouponCd(12));
        $Coupon->setCouponName('誕生日クーポン');
        $Coupon->setCouponType(Coupon::ALL); // 全商品対象
        $Coupon->setDiscountType(Coupon::DISCOUNT_PRICE); // 定額割引
        $Coupon->setDiscountPrice('1000'); // 1,000円割引
        $Coupon->setDiscountRate(0);
        $Coupon->setCouponUseTime(1); // 1回のみ使用可能
        $Coupon->setCouponRelease(1);
        $Coupon->setCouponLowerLimit('0');
        $Coupon->setCouponMember(true); // 会員限定
        $Coupon->setEnableFlag(true);
        $Coupon->setVisible(true);
        $Coupon->setAvailableFromDate($now);
        $Coupon->setAvailableToDate($endOfMonth);

        $this->em->persist($Coupon);
        $this->em->flush();

        return $Coupon;
    }
}
```

### 3. Console コマンドを実装する

プラグイン内に Console コマンドを作成します。

```php
<?php

namespace Plugin\BirthdayCoupon\Command;

use Eccube\Repository\BaseInfoRepository;
use Plugin\BirthdayCoupon\Service\BirthdayCouponService;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;
use Symfony\Component\Mailer\MailerInterface;
use Symfony\Component\Mime\Address;
use Symfony\Component\Mime\Email;

#[AsCommand(
    name: 'eccube:send-birthday-coupon',
    description: '今月が誕生月の会員に誕生日クーポンをメール送信します。',
)]
class SendBirthdayCouponCommand extends Command
{
    public function __construct(
        private BirthdayCouponService $birthdayCouponService,
        private MailerInterface $mailer,
        private BaseInfoRepository $baseInfoRepository,
    ) {
        parent::__construct();
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $io->title('誕生日クーポン送信バッチ');

        // 管理画面で設定したショップのメールアドレスを使用する
        $BaseInfo = $this->baseInfoRepository->get();
        $fromAddress = new Address($BaseInfo->getEmail01(), $BaseInfo->getShopName());

        $customers = $this->birthdayCouponService->findBirthdayCustomersThisMonth();

        if (empty($customers)) {
            $io->info('今月が誕生月の会員はいません。');
            return Command::SUCCESS;
        }

        $io->info(sprintf('%d 件の会員に送信します。', count($customers)));

        $successCount = 0;
        $failCount = 0;

        foreach ($customers as $Customer) {
            try {
                $Coupon = $this->birthdayCouponService->createBirthdayCoupon($Customer);

                $email = (new Email())
                    ->from($fromAddress)
                    ->to($Customer->getEmail())
                    ->subject('【お誕生日】特別クーポンをお届けします')
                    ->text(sprintf(
                        "%s 様\n\nお誕生日おめでとうございます！\n\n" .
                        "以下のクーポンコードをご利用ください。\n\n" .
                        "クーポンコード: %s\n" .
                        "割引金額: 1,000円\n" .
                        "有効期限: %s まで\n\n" .
                        "ご来店をお待ちしております。",
                        $Customer->getName01(),
                        $Coupon->getCouponCd(),
                        $Coupon->getAvailableToDate()->format('Y年n月j日'),
                    ));

                $this->mailer->send($email);
                $successCount++;

                $io->writeln(sprintf(
                    '✓ %s <%s> → %s',
                    $Customer->getName01(),
                    $Customer->getEmail(),
                    $Coupon->getCouponCd(),
                ));
            } catch (\Exception $e) {
                $failCount++;
                $io->error(sprintf(
                    '送信失敗: %s <%s> - %s',
                    $Customer->getName01(),
                    $Customer->getEmail(),
                    $e->getMessage(),
                ));
            }
        }

        $io->success(sprintf('完了: 成功 %d 件 / 失敗 %d 件', $successCount, $failCount));

        return Command::SUCCESS;
    }
}
```

### 4. cron に登録する

月初めに1回だけ実行するよう cron に登録します。

```bash
# 毎月1日 午前8時に実行
0 8 1 * * /path/to/php /path/to/ec-cube/bin/console eccube:send-birthday-coupon --env=prod >> /var/log/birthday-coupon.log 2>&1
```

> **ログの取り扱い注意**: ログファイルにはメールアドレスが記録されます。ファイルのパーミッションは `600`（オーナーのみ読み書き）に設定し、ログローテーションと保存期間を設定して個人情報が長期保存されないようにしてください。

毎日実行して当日誕生日の会員に送信する場合は、`findBirthdayCustomersThisMonth()` を当日の月・日で絞り込むよう変更します。

```php
// 当日誕生日の会員を取得するクエリ（毎日実行する場合）
$month = (int) (new \DateTime())->format('n');
$day   = (int) (new \DateTime())->format('j');

return $this->em->createQueryBuilder()
    ->select('c')
    ->from(Customer::class, 'c')
    ->where('EXTRACT(MONTH FROM c.birth) = :month')
    ->andWhere('EXTRACT(DAY FROM c.birth) = :day')
    ->andWhere('c.birth IS NOT NULL')
    ->andWhere('c.Status = 2')
    ->setParameter('month', $month)
    ->setParameter('day', $day)
    ->getQuery()
    ->getResult();
```

> `EXTRACT(DAY FROM ...)` も DQL で使用できます。

## 重複送信を防ぐ設計

このまま実装すると、月初に全会員分を一括送信しますが、コマンドを誤って2回実行した場合に重複送信が発生します。送信済みフラグを管理するために、プラグイン独自のテーブルを追加することを検討してください。

```php
// 例: 送信済みチェック用エンティティ（年・会員IDで重複チェック）
// プラグインの Entity として実装する

class BirthdayCouponHistory
{
    private int $id;
    private Customer $Customer;
    private int $sentYear;     // 送信した年（同じ年に2回送らないため）
    private string $couponCd;
    private \DateTime $sentAt;
}
```

送信前に「今年すでに送信済みか」を確認することで冪等性を確保できます。

## まとめ

- EC-CUBE には誕生日イベントが存在しないため、Console コマンド + cron による定期実行が正しい設計方針です
- クーポンプラグインの個人割り当て機能の制約は、**顧客ごとにユニークなクーポンコードを生成して `coupon_use_time=1` にする**ことで回避できます
- `EXTRACT(MONTH FROM c.birth)` は DQL で使用でき、誕生月による会員絞り込みが可能です
- `#[AsCommand]` アトリビュートで Console コマンドをプラグイン内に定義できます
- 実運用では送信済み管理テーブルを追加して重複送信を防ぐ設計が必要です

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
