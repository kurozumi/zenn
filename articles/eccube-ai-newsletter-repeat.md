---
title: "個人情報ゼロでAIメルマガ配信 — EC-CUBE標準データだけでRFM分析する方法"
emoji: "📧"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: false
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

:::details TL;DR（要約）
- EC サイトの売上の約 80% はリピーターが生み出し、リピート購入のきっかけ 1 位はメルマガ
- AI に個人情報を渡す必要はない。顧客 ID・購入回数・購入金額・最終購入日だけで分析できる
- Claude API は商用利用規約で「API 経由のデータはモデル学習に使わない」と明記
- EC-CUBE の Customer エンティティに `buy_times`・`buy_total`・`last_buy_date` が標準搭載されており、そのまま RFM 分析に使える
- 公式メルマガ管理プラグインを使えば配信停止管理・送信履歴・テンプレート管理をそのまま使える
- Symfony Console コマンドとして実装すれば cron で全自動配信まで持っていける
:::

## 「全員に同じメルマガ」、まだ続けていますか？

「配信リストに一斉送信 → 購入ゼロ → また来月…」。

この繰り返しに心当たりがある方は、原因は文章でも商品でもなく**「誰に送るか」の精度**かもしれません。

3 ヶ月購入のない会員に「ありがとうございます」メールを送っても響きません。先週買った会員にセール案内を送れば迷惑です。AI を使えば**誰に・何を・いつ**を個人レベルで自動判定できます。

「でも AI に顧客データを渡すのは怖い」——その心配は正しい感覚です。この記事では**個人情報を一切 AI に渡さず**、EC-CUBE 標準データだけでセグメント配信を実装する方法を解説します。

## 使用するプラグイン

EC-CUBE 公式の**メルマガ管理プラグイン**を使います。

- リポジトリ: https://github.com/EC-CUBE/mail-magazine-plugin
- 機能: テンプレート管理・配信履歴・テスト配信・失敗時の再送・100件バッチ送信

このプラグインを使うことで、以下を自前実装せずに済みます。

- 配信停止（オプトアウト）管理
- 送信履歴の記録
- HTML/テキスト形式テンプレートの管理
- 大量配信時のバッチ処理

**AI は「誰に送るか」の判定だけに集中**し、実際の送信はプラグインに任せる設計です。

## 個人情報は渡さなくていい

AI がセグメント分析に必要なのは行動データだけです。

```
× 渡してはいけないデータ
　名前・メールアドレス・住所・電話番号・生年月日

✅ 渡してよいデータ（匿名化済み）
　顧客ID・購入回数・累計購入金額・最終購入日からの経過日数
```

### Claude API のデータポリシー

Anthropic の商用利用規約（Commercial Terms）には以下が明記されています：

> Anthropic may not train models on Customer Content from Services

API 経由で送信したデータはモデルの学習に使用されません。ブラウザの Claude.ai とは別扱いです。

### 個人情報保護法の観点

| 加工方法 | 定義 | 第三者提供 |
|---|---|---|
| **仮名加工情報** | 他の情報と照合しない限り個人を識別できない（顧客 ID への置き換え等） | 原則禁止 |
| **匿名加工情報** | 復元不可能に加工した情報 | 公表義務を果たせば提供可 |

自社サーバーで処理して結果だけ受け取る設計にすれば、仮名加工情報のまま扱えます。ただし顧客 ID + 行動データを外部 API に送信することになるため、自社のプライバシーポリシーに「購買行動の分析に外部 AI サービスを利用する旨」を明記することを推奨します。

## 全体構成

```
EC-CUBE DB（顧客・受注データ）
         │
         ▼
  匿名化処理（自社サーバー内）
  ※ 名前・メール・住所は除外
         │
         ▼
  Claude API（セグメント分析）
  ※ 顧客ID＋行動データのみ
         │
         ▼
  セグメント判定結果を受け取る
         │
         ▼
  メルマガ管理プラグインの送信処理
  ※ オプトアウト管理・履歴記録・バッチ送信を担当
```

名前・メールアドレス・住所は EC-CUBE DB だけにあり、AI には渡りません。

## メルマガ管理プラグインの仕組みを理解する

### オプトアウト管理

プラグインは `CustomerTrait` を使って `dtb_customer` テーブルに `plg_mailmagazine_flg` カラムを追加します。会員登録時・マイページでメルマガ受信の有無を選択できます。

```
plg_mailmagazine_flg = 1 → 受け取る
plg_mailmagazine_flg = 0 → 希望しない（配信停止）
```

:::message alert
特定電子メール法により、受信拒否の意思を示した宛先への送信は違法です。プラグインが提供する `getMailmagaFlg()` で配信停止の会員を必ず除外してください。
:::

### 送信サービス

`Plugin\MailMagazine42\Service\MailMagazineService` が送信処理を担当します。

- `createMailMagazineHistory($formData)` — 配信履歴を作成し、配信対象の CSV ファイルを生成
- `sendrMailMagazine($sendId, $offset, $max)` — 100件ずつバッチ送信
- `sendMailMagazineCompleateReportMail()` — 全配信完了後に管理者へ完了報告メールを送信
- `markRetry($sendId)` — 失敗分の再送処理

## EC-CUBE の標準データを活用する

`Customer` エンティティには RFM 分析に必要なフィールドが標準で揃っています。

| フィールド | 内容 | RFM |
|---|---|---|
| `id` | 顧客 ID | 識別子 |
| `last_buy_date` | 最終購入日 | **R**ecency（最近性） |
| `buy_times` | 購入回数（string 型） | **F**requency（頻度） |
| `buy_total` | 累計購入金額（string 型） | **M**onetary（金額） |
| `create_date` | 会員登録日 | 在籍期間 |
| `point` | 保有ポイント（string 型） | エンゲージメント |

これらは受注完了のたびに `OrderRepository::updateOrderSummary()` で自動更新されます。

## 実装

### 1. 必要パッケージのインストール

```bash
# メルマガ管理プラグインをインストール
php bin/console eccube:plugin:install --code=MailMagazine42

# Anthropic PHP SDK をインストール
composer require "anthropic-ai/sdk:^0.9.0"
```

### 2. ディレクトリ構成

```
app/Plugin/AiNewsletter/
├── Command/
│   └── SendNewsletterCommand.php  # cron から実行するコマンド
└── Service/
    └── CustomerSegmentService.php # 匿名化 + AI セグメント分析
```

メール送信・テンプレート管理・配信履歴はメルマガ管理プラグインに任せるため、自前の送信サービスは不要です。

### 3. 顧客セグメントサービス

```php
<?php
// app/Plugin/AiNewsletter/Service/CustomerSegmentService.php

namespace Plugin\AiNewsletter\Service;

use Anthropic\Client as AnthropicClient;
use Eccube\Entity\Customer;

class CustomerSegmentService
{
    // セグメント定数
    public const SEGMENT_VIP = 'vip';       // 高額・高頻度
    public const SEGMENT_ACTIVE = 'active'; // 通常アクティブ
    public const SEGMENT_LAPSED = 'lapsed'; // 離脱予備軍（60〜90日未購入）
    public const SEGMENT_LOST = 'lost';     // 離脱（90日超未購入）
    public const SEGMENT_NEW = 'new';       // 新規（購入1回）

    private const ALLOWED_SEGMENTS = [
        self::SEGMENT_VIP,
        self::SEGMENT_ACTIVE,
        self::SEGMENT_LAPSED,
        self::SEGMENT_LOST,
        self::SEGMENT_NEW,
    ];

    public function __construct(
        private readonly AnthropicClient $anthropic,
    ) {}

    /**
     * 顧客リストをセグメント別に分類する
     *
     * @param Customer[] $customers
     * @return array<string, Customer[]> セグメント名 => 顧客配列
     */
    public function segmentCustomers(array $customers): array
    {
        $anonymizedData = $this->buildAnonymizedData($customers);
        $segmentMap = $this->analyzeWithAI($anonymizedData);

        $result = array_fill_keys(self::ALLOWED_SEGMENTS, []);

        foreach ($customers as $customer) {
            $segment = $segmentMap[$customer->getId()] ?? self::SEGMENT_ACTIVE;
            $result[$segment][] = $customer;
        }

        return $result;
    }

    /**
     * 個人情報を除いた匿名化データを構築する
     * 名前・メールアドレス・住所・電話番号は含まない
     */
    private function buildAnonymizedData(array $customers): array
    {
        $now = new \DateTimeImmutable();
        $data = [];

        foreach ($customers as $customer) {
            $lastBuyDate = $customer->getLastBuyDate();
            $daysSinceLastBuy = $lastBuyDate
                ? (int) $now->diff($lastBuyDate)->days
                : null;

            $createDate = $customer->getCreateDate();
            $membershipDays = $createDate
                ? (int) $now->diff($createDate)->days
                : 0;

            // 渡すのは行動データのみ（個人を特定できる情報は含まない）
            // buy_times・buy_total・point は DB 上 string 型のため明示的にキャストする
            $data[] = [
                'id' => $customer->getId(),
                'buy_times' => (int) $customer->getBuyTimes(),
                'buy_total' => (float) $customer->getBuyTotal(),
                'days_since_last_buy' => $daysSinceLastBuy,
                'membership_days' => $membershipDays,
                'point' => (int) $customer->getPoint(),
            ];
        }

        return $data;
    }

    /**
     * Claude API でセグメントを判定する
     *
     * @return array<int, string> 顧客ID => セグメント名
     */
    private function analyzeWithAI(array $anonymizedData): array
    {
        $prompt = $this->buildPrompt($anonymizedData);

        $response = $this->anthropic->messages->create(
            maxTokens: 4096,
            model: 'claude-opus-4-6',
            system: <<<SYSTEM
あなたは EC サイトの顧客分析の専門家です。
匿名化された購買データを分析し、各顧客を以下のセグメントに分類してください。

セグメント定義:
- vip: 購入回数5回以上かつ累計購入金額5万円以上の優良顧客
- active: 最終購入から60日以内のアクティブ顧客
- lapsed: 最終購入から60〜90日の離脱予備軍
- lost: 最終購入から90日超または一度も購入していない
- new: 購入回数1回の新規顧客

必ず JSON 形式のみで返してください。例: {"123": "active", "456": "lapsed"}
SYSTEM,
            messages: [
                ['role' => 'user', 'content' => $prompt],
            ],
        );

        $content = $response->content[0]->text ?? '{}';

        // JSON を抽出（マークダウンコードブロックに包まれている場合も対応）
        if (preg_match('/\{.+\}/s', $content, $matches)) {
            $content = $matches[0];
        }

        $decoded = json_decode($content, true);

        if (!is_array($decoded)) {
            return [];
        }

        // セグメント値をホワイトリストで検証し、不正値はデフォルトにフォールバック
        $result = [];
        foreach ($decoded as $id => $segment) {
            $result[(int) $id] = in_array($segment, self::ALLOWED_SEGMENTS, true)
                ? (string) $segment
                : self::SEGMENT_ACTIVE;
        }

        return $result;
    }

    private function buildPrompt(array $data): string
    {
        $json = json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT);

        return <<<PROMPT
以下の顧客データを分析してセグメントを判定してください。
データには個人情報は含まれていません。

{$json}

各顧客の id をキー、セグメント名を値とする JSON のみを返してください。
PROMPT;
    }
}
```

### 4. Console コマンド

AI でセグメントを判定し、セグメントに対応するメルマガテンプレートをプラグインの送信処理に渡します。

```php
<?php
// app/Plugin/AiNewsletter/Command/SendNewsletterCommand.php

namespace Plugin\AiNewsletter\Command;

use Eccube\Entity\Customer;
use Eccube\Repository\CustomerRepository;
use Plugin\AiNewsletter\Service\CustomerSegmentService;
use Plugin\MailMagazine42\Repository\MailMagazineTemplateRepository;
use Plugin\MailMagazine42\Service\MailMagazineService;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Input\InputOption;
use Symfony\Component\Console\Output\OutputInterface;
use Symfony\Component\Console\Style\SymfonyStyle;

#[AsCommand(
    name: 'ai-newsletter:send',
    description: 'AI でセグメント分析してメルマガを送信する',
)]
class SendNewsletterCommand extends Command
{
    // セグメントとメルマガテンプレート ID のマッピング
    // 管理画面でテンプレートを作成し、ID を設定してください
    private const SEGMENT_TEMPLATE_MAP = [
        CustomerSegmentService::SEGMENT_VIP => 1,    // 「VIP会員様限定ご優待」テンプレート
        CustomerSegmentService::SEGMENT_LAPSED => 2, // 「お久しぶりです」テンプレート
        CustomerSegmentService::SEGMENT_ACTIVE => 3, // 「新着商品のご案内」テンプレート
        CustomerSegmentService::SEGMENT_NEW => 3,    // 新規もアクティブ用テンプレートを使用
    ];

    public function __construct(
        private readonly CustomerRepository $customerRepository,
        private readonly CustomerSegmentService $segmentService,
        private readonly MailMagazineService $mailMagazineService,
        private readonly MailMagazineTemplateRepository $templateRepository,
    ) {
        parent::__construct();
    }

    protected function configure(): void
    {
        $this->addOption(
            'dry-run',
            null,
            InputOption::VALUE_NONE,
            'メールを送信せずに分析結果だけ表示する',
        );
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $io = new SymfonyStyle($input, $output);
        $isDryRun = $input->getOption('dry-run');

        $io->title('AI メルマガ送信');

        // メルマガ受信同意済み（plg_mailmagazine_flg = 1）の退会していない会員を取得
        // プラグインの AdminCustomerQueryCustomizer が mailmaga_flg の WHERE 句を追加する
        $allCustomers = $this->customerRepository->getNonWithdrawingCustomers([]);
        $customers = array_filter(
            $allCustomers,
            fn(Customer $c) => $c->getMailmagaFlg()
        );

        if (empty($customers)) {
            $io->warning('配信対象の顧客が見つかりませんでした。');
            return Command::SUCCESS;
        }

        $io->info(sprintf('%d 件の顧客を分析します...', count($customers)));

        // AI でセグメント分類
        $segmented = $this->segmentService->segmentCustomers(array_values($customers));

        foreach ($segmented as $segment => $segmentCustomers) {
            $count = count($segmentCustomers);
            $io->section(sprintf('[%s] %d 件', $segment, $count));

            // 離脱済みはメール送信しない
            if ($segment === CustomerSegmentService::SEGMENT_LOST || $count === 0) {
                continue;
            }

            if ($isDryRun) {
                continue;
            }

            $templateId = self::SEGMENT_TEMPLATE_MAP[$segment] ?? null;
            if ($templateId === null) {
                $io->warning(sprintf('セグメント "%s" のテンプレートが設定されていません。', $segment));
                continue;
            }

            $template = $this->templateRepository->find($templateId);
            if ($template === null) {
                $io->error(sprintf('テンプレート ID %d が見つかりません。', $templateId));
                continue;
            }

            // プラグインの送信処理を使って配信履歴を作成・送信
            $formData = [
                'subject' => $template->getSubject(),
                'body' => $template->getBody(),
                'html_body' => $template->getHtmlBody(),
                'mail_method' => $template->getMailMethod(),
                'plg_mailmagazine_flg' => 1,
            ];

            try {
                $sendHistory = $this->mailMagazineService->createMailMagazineHistory($formData);
                $this->mailMagazineService->sendrMailMagazine(
                    $sendHistory->getId(),
                    0,
                    100
                );
                $io->success(sprintf('[%s] 配信完了', $segment));
            } catch (\Exception $e) {
                $io->error(sprintf('[%s] 配信失敗: %s', $segment, $e->getMessage()));
            }
        }

        if ($isDryRun) {
            $io->note('dry-run モードのため送信はスキップしました。');
        }

        return Command::SUCCESS;
    }
}
```

### 5. サービス定義

```php
<?php
// app/Plugin/AiNewsletter/Service/AnthropicClientFactory.php

namespace Plugin\AiNewsletter\Service;

use Anthropic\Anthropic;
use Anthropic\Client;

class AnthropicClientFactory
{
    public function __invoke(): Client
    {
        return Anthropic::client(apiKey: $_ENV['ANTHROPIC_API_KEY']);
    }
}
```

```yaml
# app/Plugin/AiNewsletter/Resource/config/services.yaml
services:
    Plugin\AiNewsletter\Service\AnthropicClientFactory: ~

    Anthropic\Client:
        factory: '@Plugin\AiNewsletter\Service\AnthropicClientFactory'

    Plugin\AiNewsletter\Service\CustomerSegmentService:
        arguments:
            - '@Anthropic\Client'

    Plugin\AiNewsletter\Command\SendNewsletterCommand:
        tags:
            - { name: console.command }
```

```bash
# .env.local（API キーは必ず環境変数で管理する。.gitignore に追加すること）
ANTHROPIC_API_KEY=sk-ant-...
```

:::message alert
API キーをソースコードにハードコードしないでください。`.env.local` で管理し、`.gitignore` に追加して Git にコミットしないようにしてください。
:::

### 6. cron 設定

```bash
# 毎週火曜日の朝 10 時に送信（実行ユーザーを www-data に限定する）
0 10 * * 2 www-data cd /var/www/html && php bin/console ai-newsletter:send >> /var/log/ai-newsletter.log 2>&1
```

本番実行前に必ず dry-run で動作確認してください。

```bash
php bin/console ai-newsletter:send --dry-run
```

### 7. 管理画面でテンプレートを作成する

コマンド内の `SEGMENT_TEMPLATE_MAP` に対応するテンプレートをプラグインの管理画面から作成します。

| セグメント | テンプレート例 |
|---|---|
| `vip` | 「VIP 会員様限定ご優待のご案内」 |
| `lapsed` | 「お久しぶりです。期間限定クーポンをご用意しました」 |
| `active` / `new` | 「新着商品のご案内」 |

テンプレート作成後、管理画面で確認できるテンプレート ID を `SEGMENT_TEMPLATE_MAP` に設定してください。

## 役割分担まとめ

| 役割 | 担当 |
|---|---|
| セグメント分析（誰に送るか） | Claude API（匿名化データで判定） |
| 配信停止管理 | メルマガ管理プラグイン（`plg_mailmagazine_flg`） |
| テンプレート管理 | メルマガ管理プラグイン（管理画面で編集） |
| 送信履歴の記録 | メルマガ管理プラグイン（`plg_mailmaga_send_history`） |
| バッチ送信・再送 | メルマガ管理プラグイン（100件ずつ処理） |
| 定期実行 | Console コマンド + cron |

EC-CUBE 標準の顧客データだけで RFM 分析からメール送信まで自動化できます。「個人情報を AI に渡す」ことなく、プライバシーを守りながら精度の高いメルマガ施策が実現できます。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
