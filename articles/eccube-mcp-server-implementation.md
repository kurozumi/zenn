---
title: "EC-CUBE 4用MCPサーバーを作ってAI開発を効率化する"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "php", "mcp", "ai"]
published: true
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

## はじめに

**MCP（Model Context Protocol）** は、AIアシスタントが外部ツールやデータソースと連携するためのオープンプロトコルです。MCPサーバーを実装することで、Claude等のAIがEC-CUBEの商品データや受注情報に直接アクセスできるようになります。

本記事では、EC-CUBE 4用のMCPサーバーを実装し、AI駆動の開発・運用を効率化する方法を解説します。

:::message
この記事で紹介するMCPサーバーは、OSSとして公開しています。
**GitHub**: https://github.com/kurozumi/eccube-mcp-server
:::

## MCPサーバーで実現できること

EC-CUBE用MCPサーバーを導入すると、以下のようなことが可能になります。

- 「在庫切れの商品を教えて」→ AIが直接DBを検索して回答
- 「今日の受注一覧を取得して」→ 受注データをリアルタイムで取得
- 「商品ID:5の詳細情報を見せて」→ 商品の全情報を取得
- EC-CUBEのバージョンアップ作業をAIが補助

## 環境構築

### 必要なもの

- EC-CUBE 4.3以上
- PHP 8.1以上
- Composer
- Claude Desktop または Claude Code

### プロジェクト構成

EC-CUBEのプロジェクトルートに `mcp-server` ディレクトリを作成します。

```
ec-cube/
├── app/
├── src/
├── mcp-server/          # MCPサーバー用ディレクトリ
│   ├── composer.json
│   ├── server.php       # MCPサーバーのエントリポイント
│   └── src/
│       └── Tools/       # MCPツール定義
└── ...
```

### MCP SDKのインストール

```bash
cd /path/to/ec-cube/mcp-server
composer init --name="myshop/eccube-mcp-server" --no-interaction
composer require mcp/sdk
```

## MCPサーバーの実装

### EC-CUBEのブートストラップ

EC-CUBEのEntityManagerを使用するため、EC-CUBEのカーネルを起動します。

```php
<?php
// mcp-server/bootstrap.php

require_once __DIR__.'/../vendor/autoload.php';

use Eccube\Kernel;
use Symfony\Component\Dotenv\Dotenv;

// 環境変数の読み込み
$dotenv = new Dotenv();
$dotenv->loadEnv(__DIR__.'/../.env');

$env = $_SERVER['APP_ENV'] ?? 'prod';
$debug = (bool) ($_SERVER['APP_DEBUG'] ?? false);

// EC-CUBEカーネルの起動
$kernel = new Kernel($env, $debug);
$kernel->boot();

return $kernel->getContainer();
```

### 商品取得ツールの実装

```php
<?php
// mcp-server/src/Tools/ProductTools.php

namespace MyShop\MCP\Tools;

use Eccube\Repository\ProductRepository;
use Mcp\Attribute\McpTool;
use Mcp\Attribute\ToolParameter;

class ProductTools
{
    private ProductRepository $productRepository;

    public function __construct(ProductRepository $productRepository)
    {
        $this->productRepository = $productRepository;
    }

    /**
     * 商品IDで商品情報を取得する
     */
    #[McpTool(
        name: 'get_product',
        description: '商品IDを指定して商品の詳細情報を取得します'
    )]
    public function getProduct(
        #[ToolParameter(description: '商品ID', required: true)]
        int $productId
    ): array {
        $product = $this->productRepository->find($productId);

        if (!$product) {
            return ['error' => '商品が見つかりません'];
        }

        return [
            'id' => $product->getId(),
            'name' => $product->getName(),
            'description' => $product->getDescriptionDetail(),
            'price' => $product->getPrice02Min(),
            'stock' => $this->getStockInfo($product),
            'status' => $product->getStatus()->getName(),
            'create_date' => $product->getCreateDate()->format('Y-m-d H:i:s'),
        ];
    }

    /**
     * 商品を検索する
     */
    #[McpTool(
        name: 'search_products',
        description: '条件を指定して商品を検索します'
    )]
    public function searchProducts(
        #[ToolParameter(description: '検索キーワード（商品名）', required: false)]
        ?string $keyword = null,
        #[ToolParameter(description: '在庫切れのみ取得するか', required: false)]
        bool $outOfStock = false,
        #[ToolParameter(description: '取得件数（デフォルト10件）', required: false)]
        int $limit = 10
    ): array {
        $qb = $this->productRepository->createQueryBuilder('p')
            ->select('p')
            ->setMaxResults($limit);

        if ($keyword) {
            $qb->andWhere('p.name LIKE :keyword')
               ->setParameter('keyword', '%'.$keyword.'%');
        }

        $products = $qb->getQuery()->getResult();
        $results = [];

        foreach ($products as $product) {
            $stock = $this->getStockInfo($product);

            if ($outOfStock && $stock['total'] > 0) {
                continue;
            }

            $results[] = [
                'id' => $product->getId(),
                'name' => $product->getName(),
                'price' => $product->getPrice02Min(),
                'stock' => $stock['total'],
                'status' => $product->getStatus()->getName(),
            ];
        }

        return [
            'count' => count($results),
            'products' => $results,
        ];
    }

    private function getStockInfo($product): array
    {
        $total = 0;
        foreach ($product->getProductClasses() as $pc) {
            if ($pc->isVisible() && $pc->getStock() !== null) {
                $total += $pc->getStock();
            }
        }
        return ['total' => $total];
    }
}
```

### 受注取得ツールの実装

```php
<?php
// mcp-server/src/Tools/OrderTools.php

namespace MyShop\MCP\Tools;

use Eccube\Repository\OrderRepository;
use Mcp\Attribute\McpTool;
use Mcp\Attribute\ToolParameter;

class OrderTools
{
    private OrderRepository $orderRepository;

    public function __construct(OrderRepository $orderRepository)
    {
        $this->orderRepository = $orderRepository;
    }

    /**
     * 受注を検索する
     */
    #[McpTool(
        name: 'search_orders',
        description: '条件を指定して受注を検索します'
    )]
    public function searchOrders(
        #[ToolParameter(description: '検索開始日（YYYY-MM-DD形式）', required: false)]
        ?string $fromDate = null,
        #[ToolParameter(description: '検索終了日（YYYY-MM-DD形式）', required: false)]
        ?string $toDate = null,
        #[ToolParameter(description: '対応状況ID（1:新規受付, 3:キャンセル, 5:発送済み, 6:入金済み）', required: false)]
        ?int $statusId = null,
        #[ToolParameter(description: '取得件数（デフォルト20件）', required: false)]
        int $limit = 20
    ): array {
        $qb = $this->orderRepository->createQueryBuilder('o')
            ->select('o')
            ->orderBy('o.order_date', 'DESC')
            ->setMaxResults($limit);

        if ($fromDate) {
            $qb->andWhere('o.order_date >= :fromDate')
               ->setParameter('fromDate', new \DateTime($fromDate));
        }

        if ($toDate) {
            $qb->andWhere('o.order_date <= :toDate')
               ->setParameter('toDate', new \DateTime($toDate.' 23:59:59'));
        }

        if ($statusId) {
            $qb->andWhere('o.OrderStatus = :status')
               ->setParameter('status', $statusId);
        }

        $orders = $qb->getQuery()->getResult();
        $results = [];

        foreach ($orders as $order) {
            $results[] = [
                'id' => $order->getId(),
                'order_no' => $order->getOrderNo(),
                'customer_name' => $order->getName01().' '.$order->getName02(),
                'email' => $order->getEmail(),
                'total' => $order->getPaymentTotal(),
                'status' => $order->getOrderStatus()->getName(),
                'order_date' => $order->getOrderDate()->format('Y-m-d H:i:s'),
            ];
        }

        return [
            'count' => count($results),
            'orders' => $results,
        ];
    }

    /**
     * 今日の売上サマリーを取得する
     */
    #[McpTool(
        name: 'get_today_summary',
        description: '今日の売上サマリー（受注件数、売上合計）を取得します'
    )]
    public function getTodaySummary(): array
    {
        $today = new \DateTime('today');
        $tomorrow = new \DateTime('tomorrow');

        $qb = $this->orderRepository->createQueryBuilder('o')
            ->select('COUNT(o.id) as order_count, SUM(o.payment_total) as total_sales')
            ->where('o.order_date >= :today')
            ->andWhere('o.order_date < :tomorrow')
            ->andWhere('o.OrderStatus NOT IN (:excludeStatus)')
            ->setParameter('today', $today)
            ->setParameter('tomorrow', $tomorrow)
            ->setParameter('excludeStatus', [3, 8]); // キャンセル、購入処理中を除外

        $result = $qb->getQuery()->getSingleResult();

        return [
            'date' => $today->format('Y-m-d'),
            'order_count' => (int) $result['order_count'],
            'total_sales' => (int) ($result['total_sales'] ?? 0),
        ];
    }
}
```

### MCPサーバーのエントリポイント

```php
<?php
// mcp-server/server.php

require_once __DIR__.'/vendor/autoload.php';

use Mcp\Server\Server;
use Mcp\Transport\StdioTransport;
use MyShop\MCP\Tools\ProductTools;
use MyShop\MCP\Tools\OrderTools;

// EC-CUBEのコンテナを取得
$container = require_once __DIR__.'/bootstrap.php';

// リポジトリの取得
$productRepository = $container->get(\Eccube\Repository\ProductRepository::class);
$orderRepository = $container->get(\Eccube\Repository\OrderRepository::class);

// ツールのインスタンス化
$productTools = new ProductTools($productRepository);
$orderTools = new OrderTools($orderRepository);

// MCPサーバーの構築
$server = Server::builder()
    ->setServerInfo('EC-CUBE MCP Server', '1.0.0')
    ->registerToolsFromObject($productTools)
    ->registerToolsFromObject($orderTools)
    ->build();

// STDIOトランスポートで実行
$transport = new StdioTransport();
$server->run($transport);
```

### Composerのオートロード設定

```json
{
    "name": "myshop/eccube-mcp-server",
    "autoload": {
        "psr-4": {
            "MyShop\\MCP\\": "src/"
        }
    },
    "require": {
        "php": ">=8.1",
        "mcp/sdk": "^0.4"
    }
}
```

オートロードを更新します。

```bash
composer dump-autoload
```

## Claude Desktopでの設定

Claude Desktopの設定ファイルにMCPサーバーを登録します。

### macOSの場合

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集します。

```json
{
  "mcpServers": {
    "eccube": {
      "command": "php",
      "args": ["/path/to/ec-cube/mcp-server/server.php"],
      "env": {
        "APP_ENV": "prod",
        "APP_DEBUG": "0"
      }
    }
  }
}
```

### Windowsの場合

`%APPDATA%\Claude\claude_desktop_config.json` を編集します。

```json
{
  "mcpServers": {
    "eccube": {
      "command": "php",
      "args": ["C:\\path\\to\\ec-cube\\mcp-server\\server.php"],
      "env": {
        "APP_ENV": "prod",
        "APP_DEBUG": "0"
      }
    }
  }
}
```

設定後、Claude Desktopを再起動すると、MCPサーバーが利用可能になります。

## 使用例

Claude Desktopで以下のような質問ができるようになります。

### 商品検索

```
在庫切れの商品を教えて
```

AIが `search_products` ツールを呼び出し、在庫切れ商品の一覧を返します。

### 売上確認

```
今日の売上状況を教えて
```

AIが `get_today_summary` ツールを呼び出し、本日の受注件数と売上合計を返します。

### 受注検索

```
今週の新規受注を一覧で見せて
```

AIが `search_orders` ツールを呼び出し、条件に合った受注データを返します。

## セキュリティ上の注意

MCPサーバーはEC-CUBEのデータベースに直接アクセスするため、以下の点に注意してください。

1. **本番環境での使用は慎重に**: 開発・検証環境での使用を推奨
2. **読み取り専用のツールに限定**: 更新・削除系のツールは慎重に設計
3. **アクセス制限**: MCPサーバーは信頼できる環境でのみ実行
4. **ログ出力**: 実行ログを記録してモニタリング

## 拡張のアイデア

基本的なツールを実装したら、以下のような拡張も検討できます。

| ツール | 用途 |
|--------|------|
| `get_customer` | 会員情報の取得 |
| `get_category_tree` | カテゴリ階層の取得 |
| `get_plugin_list` | インストール済みプラグイン一覧 |
| `check_system_info` | システム情報（PHP/DBバージョン等） |
| `analyze_sales` | 売上分析（期間別、商品別） |

## まとめ

- MCPサーバーを実装することで、AIがEC-CUBEのデータに直接アクセス可能に
- 公式PHP SDKを使えば、属性ベースで簡単にツールを定義できる
- 商品検索、受注確認、売上サマリーなど、日常業務をAIが補助
- EC-CUBEのバージョンアップ作業もAIエージェントが支援可能に

MCPサーバーは、EC-CUBEの開発・運用をAIと協働で行う新しいワークフローを実現します。

## 参考リンク

- [EC-CUBE MCP Server（GitHub）](https://github.com/kurozumi/eccube-mcp-server) - 本記事で紹介したMCPサーバーのOSS
- [GitHub Issue: MCPサーバーの実装](https://github.com/EC-CUBE/ec-cube/issues/6347)
- [MCP公式PHP SDK](https://github.com/modelcontextprotocol/php-sdk)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP PHP SDK - Packagist](https://packagist.org/packages/mcp/sdk)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
