---
title: "ShopifyはもうAI対応済み——EC-CUBEをMCPエンドポイント対応させてAIに商品を検索させる"
emoji: "🌐"
type: "tech"
topics: ["eccube", "eccube4", "php", "mcp", "nlweb"]
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

**Shopifyはすでに対応済みです。EC-CUBEはまだです。**

「防水の財布を3000円以内で探して」——ユーザーがそう言うと、AIが商品一覧ではなくピンポイントで回答する。ChatGPT・Claude・Perplexityに代表されるAIエージェントが「ショッピングの入り口」になりつつある今、検索されるECサイトの条件が変わりはじめています。

ShopifyはすでにJSON-RPC 2.0形式の `/api/mcp` エンドポイントを公開し、AIエージェントが商品カタログを自然言語で検索できる仕組みを提供しています。EC-CUBEの公式対応はIssue（[#6371](https://github.com/EC-CUBE/ec-cube/issues/6371)）として議論中ですが、**プラグインを使えば今日から対応できます**。

本記事では、3ファイル・約100行のプラグインでEC-CUBEに `/api/mcp` エンドポイントを追加し、AIエージェントから商品を自然言語で検索可能にする実装手順を解説します。

**TL;DR**
- MCP（Model Context Protocol）はAIエージェントがWebサービスを操作するためのAnthropicのオープン標準
- ShopifyはJSON-RPC 2.0の `/api/mcp` エンドポイントでMCPに対応済み
- NLWeb（Microsoft）はWebサイトに自然言語インターフェースを追加するプロトコルで、MCPエンドポイントをバックエンドとして利用できる
- EC-CUBEプラグインで同じ仕様のエンドポイントを実装することで対応できる
- 実装するのはPHP（プラグイン）のみ。NLWebサーバー側はPython環境が別途必要

## MCP・NLWebとは

### MCP（Model Context Protocol）

MCPはAnthropicが2024年にオープンソースで公開した標準プロトコルで、AIエージェントが外部ツール・データソースと連携するための仕組みです。Claude・ChatGPT・Cursorなど多くのAIクライアントがMCPをサポートしています。

MCPサーバーはJSON-RPC 2.0形式でツールを公開します。クライアントは `tools/list` でツール一覧を取得し、`tools/call` でツールを実行します。

### NLWeb（Natural Language Web）

NLWebはMicrosoftが2025年にオープンソースで公開したプロトコルです。Webサイトに自然言語インターフェースを追加するための仕組みで、「MCPにとってのHTTP」と位置づけられています。

> "NLWeb is to MCP/A2A what HTML is to HTTP"

NLWebサーバーはLLMで自然言語クエリの意図を解析し、MCPエンドポイントをバックエンドとして商品・コンテンツを検索し、LLMで自然言語の回答を生成します。**MCPエンドポイントを実装すれば、NLWebのデータソースになれます**。

### Shopifyの実装例

ShopifyはすでにJSON-RPC 2.0形式の `/api/mcp` エンドポイントを公開しており、AIエージェントがこれを使って商品カタログを検索できます。リクエストはJSON-RPC 2.0形式で、`search_shop_catalog` というツールで商品を検索します。

```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "search_shop_catalog",
    "arguments": {
      "query": "防水の財布 3000円以内",
      "limit": 10
    }
  },
  "id": 1
}
```

EC-CUBEもこれと同じ仕様のエンドポイントを実装すれば、AIエージェントやNLWebのデータソースになれます。

## アーキテクチャ

```
[ユーザー] → 自然言語クエリ
    ↓
[NLWebサーバー（Python）] → LLMで意図を解析
    ↓
[EC-CUBE /api/mcp（本記事で実装）] → 商品を検索
    ↓
[NLWebサーバー] → LLMで回答を生成
    ↓
[ユーザー] → 自然言語の回答
```

本記事では**EC-CUBE側の `/api/mcp` エンドポイント**をプラグインで実装します。NLWebサーバーの構築は別途必要です（[microsoft/NLWeb](https://github.com/microsoft/NLWeb) を参照）。

## プラグインの実装

### ディレクトリ構成

```
app/Plugin/NlwebMcp/
├── composer.json
└── Controller/
    └── McpController.php
```

### composer.json

```json
{
  "name": "your-vendor/nlweb-mcp",
  "version": "1.0.0",
  "description": "NLWeb対応MCPエンドポイントプラグイン",
  "type": "eccube-plugin",
  "require": {
    "ec-cube/plugin-installer": "~0.0.6 || ^2.0"
  },
  "extra": {
    "code": "NlwebMcp"
  }
}
```

### Controller/McpController.php

EC-CUBEのプラグインControllerは `app/Plugin/{PluginCode}/Controller/` に配置すると、Kernelが自動でルーティングを認識します。

```php
<?php

declare(strict_types=1);

namespace Plugin\NlwebMcp\Controller;

use Eccube\Controller\AbstractController;
use Eccube\Repository\ProductRepository;
use Symfony\Component\HttpFoundation\JsonResponse;
use Symfony\Component\HttpFoundation\Request;
use Symfony\Component\Routing\Annotation\Route;
use Symfony\Component\Routing\Generator\UrlGeneratorInterface;

class McpController extends AbstractController
{
    // クエリ文字列の最大長（DoS対策）
    private const MAX_QUERY_LENGTH = 200;
    // 1リクエストで返す商品数の上限
    private const MAX_LIMIT = 50;

    public function __construct(
        private readonly ProductRepository $productRepository,
    ) {}

    /**
     * MCP互換エンドポイント（Shopify仕様準拠）
     *
     * @Route("/api/mcp", name="nlweb_mcp", methods={"POST"})
     */
    public function mcp(Request $request): JsonResponse
    {
        $body = json_decode($request->getContent(), true, 16);

        if (!is_array($body) || ($body['jsonrpc'] ?? '') !== '2.0') {
            return $this->jsonRpcError(null, -32600, 'Invalid Request');
        }

        // id はstring・int・nullのみ許可（JSON-RPC 2.0仕様）
        $id = $body['id'] ?? null;
        if (!is_string($id) && !is_int($id) && !is_null($id)) {
            return $this->jsonRpcError(null, -32600, 'Invalid Request: id must be string, number, or null');
        }

        $method = $body['method'] ?? '';
        if (!is_string($method)) {
            return $this->jsonRpcError($id, -32600, 'Invalid Request: method must be a string');
        }

        $params = $body['params'] ?? [];
        if (!is_array($params)) {
            return $this->jsonRpcError($id, -32600, 'Invalid Request: params must be an object');
        }

        return match ($method) {
            'tools/list' => $this->handleToolsList($id),
            'tools/call' => $this->handleToolsCall($params, $id, $request),
            default => $this->jsonRpcError($id, -32601, 'Method not found'),
        };
    }

    private function handleToolsList(mixed $id): JsonResponse
    {
        return $this->json([
            'jsonrpc' => '2.0',
            'result' => [
                'tools' => [[
                    'name' => 'search_shop_catalog',
                    'description' => 'Search the EC-CUBE shop catalog for products',
                    'inputSchema' => [
                        'type' => 'object',
                        'properties' => [
                            'query' => [
                                'type' => 'string',
                                'description' => 'Search query in natural language',
                            ],
                            'limit' => [
                                'type' => 'integer',
                                'description' => 'Maximum number of results (default: 10, max: ' . self::MAX_LIMIT . ')',
                            ],
                        ],
                        'required' => ['query'],
                    ],
                ]],
            ],
            'id' => $id,
        ]);
    }

    private function handleToolsCall(array $params, mixed $id, Request $request): JsonResponse
    {
        if (($params['name'] ?? '') !== 'search_shop_catalog') {
            return $this->jsonRpcError($id, -32601, 'Tool not found');
        }

        $arguments = $params['arguments'] ?? [];
        if (!is_array($arguments)) {
            return $this->jsonRpcError($id, -32602, 'Invalid params: arguments must be an object');
        }

        // query の型・長さチェック
        $query = $arguments['query'] ?? '';
        if (!is_string($query)) {
            return $this->jsonRpcError($id, -32602, 'Invalid params: query must be a string');
        }
        $query = mb_substr(trim($query), 0, self::MAX_QUERY_LENGTH);
        if ($query === '') {
            return $this->jsonRpcError($id, -32602, 'Invalid params: query is required');
        }

        // limit の型・範囲チェック（負の値・上限超過を防ぐ）
        $limit = $arguments['limit'] ?? 10;
        if (!is_int($limit)) {
            return $this->jsonRpcError($id, -32602, 'Invalid params: limit must be an integer');
        }
        $limit = max(1, min($limit, self::MAX_LIMIT));

        // ProductRepositoryのフロントエンド用検索メソッドで公開商品のみ検索
        $searchData = ['name' => $query];
        $qb = $this->productRepository->getQueryBuilderBySearchData($searchData);
        $qb->setMaxResults($limit);
        $products = $qb->getQuery()->getResult();

        $baseUrl = $request->getSchemeAndHttpHost();
        $result = [];

        foreach ($products as $product) {
            $imageUrl = null;
            $productImages = $product->getProductImage();
            if (!$productImages->isEmpty()) {
                $imageUrl = $baseUrl . '/upload/save_image/' . $productImages[0]->getFileName();
            }

            // getDescriptionList() はテキスト用フィールド、getDescriptionDetail() はHTMLを含む場合がある
            // NLWebサーバーはテキストとして扱うため、HTMLタグを除去する
            $description = $product->getDescriptionList()
                ?? strip_tags($product->getDescriptionDetail() ?? '');

            $result[] = [
                'url' => $this->generateUrl(
                    'product_detail',
                    ['id' => $product->getId()],
                    UrlGeneratorInterface::ABSOLUTE_URL
                ),
                'title' => $product->getName(),
                'description' => $description,
                'price_range' => [
                    'min' => (int)$product->getPrice02IncTaxMin(),
                    'max' => (int)$product->getPrice02IncTaxMax(),
                ],
                'image_url' => $imageUrl,
                'availability' => $product->getStockFind() ? 'InStock' : 'OutOfStock',
            ];
        }

        return $this->json([
            'jsonrpc' => '2.0',
            'result' => [
                'content' => [[
                    'type' => 'text',
                    'text' => json_encode(
                        ['products' => $result],
                        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
                    ),
                ]],
            ],
            'id' => $id,
        ]);
    }

    private function jsonRpcError(mixed $id, int $code, string $message): JsonResponse
    {
        // JSON-RPCのエラーレスポンスはHTTPステータス200で返す（JSON-RPC仕様）
        return $this->json([
            'jsonrpc' => '2.0',
            'error' => ['code' => $code, 'message' => $message],
            'id' => $id,
        ]);
    }
}
```

`getQueryBuilderBySearchData()` は公開ステータス（`Status = 1`）かつ `visible = true` の商品のみを返すため、非公開商品が漏洩する心配はありません。

## 動作確認

プラグインを有効化したあと、curlでエンドポイントの動作を確認します。

### ツール一覧の取得

```bash
curl -X POST https://your-eccube-site.example.com/api/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

レスポンス:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "tools": [{
      "name": "search_shop_catalog",
      "description": "Search the EC-CUBE shop catalog for products",
      "inputSchema": { ... }
    }]
  },
  "id": 1
}
```

### 商品検索

```bash
curl -X POST https://your-eccube-site.example.com/api/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search_shop_catalog",
      "arguments": {"query": "Tシャツ", "limit": 5}
    },
    "id": 1
  }'
```

レスポンス:

```json
{
  "jsonrpc": "2.0",
  "result": {
    "content": [{
      "type": "text",
      "text": "{\"products\":[{\"url\":\"https://...\",\"title\":\"オリジナルTシャツ\",\"price_range\":{\"min\":2750,\"max\":3300},\"availability\":\"InStock\"}]}"
    }]
  },
  "id": 1
}
```

## NLWebサーバーへの接続

EC-CUBEのMCPエンドポイントができたら、NLWebサーバーをEC-CUBEに接続します。

NLWebをセットアップ（[公式README](https://github.com/microsoft/NLWeb) 参照）したあと、カスタムretrieval providerとしてEC-CUBEを登録します。以下はEC-CUBE用のProviderの実装例です。

```python
# retrieval_providers/eccube_mcp.py
import httpx
import json
from urllib.parse import urlparse

def _validate_site_url(site_url: str) -> None:
    """SSRFを防ぐため、httpsスキームかつパブリックホストのみ許可する"""
    parsed = urlparse(site_url)
    if parsed.scheme != "https":
        raise ValueError(f"site_url must use https: {site_url}")
    host = parsed.hostname or ""
    # ループバック・プライベートアドレスを拒否
    if host in ("localhost", "127.0.0.1", "::1") or host.startswith("192.168.") \
            or host.startswith("10.") or host.startswith("172."):
        raise ValueError(f"site_url points to a private address: {site_url}")

async def search_eccube(site_url: str, query: str, limit: int = 10) -> list[dict]:
    """EC-CUBEのMCPエンドポイントから商品を検索する"""
    _validate_site_url(site_url)

    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": "search_shop_catalog",
            "arguments": {"query": query, "limit": limit}
        },
        "id": 1
    }

    # connect_timeoutとread_timeoutを個別に設定
    timeout = httpx.Timeout(connect=5.0, read=10.0, write=5.0, pool=5.0)

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{site_url}/api/mcp",
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()  # HTTPエラー時に例外を発生させる
        data = response.json()

    content_list = data.get("result", {}).get("content", [])
    if not content_list:
        return []

    try:
        content = json.loads(content_list[0].get("text", "{}"))
    except (json.JSONDecodeError, KeyError):
        return []

    return content.get("products", [])
```

NLWebはレスポンスの商品データをSchema.org `Product` 型に変換し、LLMが自然言語で回答を生成します。

## 注意点

### エンドポイントは公開アクセス可能（本番運用前に必ず対策を）

`/api/mcp` は認証なしで公開されます。検索できるのは公開商品のみですが、以下のリスクがあります：

- **商品カタログのスクレイピング**: 競合他社が全商品の名前・価格・在庫状況を自動収集できます
- **DoS攻撃**: 大量リクエストでDBやサーバーに過剰な負荷をかけられます

本番環境では、**必ずレートリミットを実装してください**。Nginxやリバースプロキシで制限する方法が最も手軽です。

```nginx
# Nginxでのレートリミット設定例（nginx.conf）
limit_req_zone $binary_remote_addr zone=mcp_api:10m rate=10r/m;

location /api/mcp {
    limit_req zone=mcp_api burst=5 nodelay;
    # ... プロキシ設定
}
```

また、NLWebサーバーのIPアドレスが固定の場合は、アクセスをそのIPに限定することでスクレイピングリスクを大幅に低減できます。

```nginx
location /api/mcp {
    allow 203.0.113.1;  # NLWebサーバーのIPアドレス
    deny all;
    # ... プロキシ設定
}
```

### NLWebサーバーにはLLM APIキーが必要

NLWebサーバーはOpenAI・Anthropic・Azure OpenAI等のLLM APIを使って自然言語処理を行います。APIキーとコストが別途必要です。

### 商品検索は`name`フィールドのキーワードマッチ

`getQueryBuilderBySearchData()` の `name` パラメータは商品名・`search_word`フィールド・商品コードのキーワード検索です。意味的な検索（セマンティック検索）ではないため、「防水財布」→「防水の財布」のような表記ゆれには対応できません。セマンティック検索が必要な場合はベクトルDB連携が別途必要です。

### 商品説明のHTMLタグについて

EC-CUBEの商品詳細説明（`getDescriptionDetail()`）にはHTMLタグが含まれる場合があります。コード例では `strip_tags()` でHTMLを除去していますが、管理画面で商品説明に内部的なメモ等を入力しないよう運用ルールを整備してください。

## まとめ

EC-CUBEプラグインにJSON-RPC 2.0準拠のMCPエンドポイント（`/api/mcp`）を実装することで、AIエージェントやNLWebのデータソースとして機能させることができます。

- ShopifyのMCP対応と同じ仕様でエンドポイントを実装
- `ProductRepository::getQueryBuilderBySearchData()` で公開商品のみ安全に検索
- EC-CUBE公式の対応（Issue #6371）を待ちながら、今すぐ先取りで対応可能

MCPとNLWebはまだ普及途上のプロトコルですが、「AIエージェントがWebを自然言語で読む」という方向性は確実な潮流です。ECサイトとしての競争力を早めに準備しておく価値があります。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
