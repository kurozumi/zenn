---
title: "「在庫が少ない商品を教えて」とClaudeに話しかけてEC-CUBEを操作する"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "nodejs", "mcp"]
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

「在庫が少ない商品を教えて」——Claudeにそう話しかけるだけで、EC-CUBEの在庫一覧が返ってきます。

EC-CUBEのWeb APIプラグイン（GraphQL）と **MCP（Model Context Protocol）** を組み合わせると、Claude Desktopから自然言語でEC-CUBEの商品・在庫管理や売上分析ができるようになります。

実際の動作イメージはこちらです。

> **ユーザー:** 在庫が10個以下の商品を全部教えてください。
>
> **Claude:** 以下の商品が在庫僅少です。
> - 【オリジナルTシャツ（白/M）】規格コード: T-001-WM / 在庫: 3個
> - 【ロゴキャップ（フリーサイズ）】規格コード: CAP-001 / 在庫: 7個
>
> **ユーザー:** T-001-WMの在庫を50に更新してください。
>
> **Claude:** 商品規格コード「T-001-WM」の在庫を50個に更新しました。
>
> **ユーザー:** 先月の売れ筋商品トップ5を売上順で教えて。
>
> **Claude:** 先月（2026年4月）の売れ筋商品トップ5（売上順）です。
> 1. オリジナルTシャツ（白/M） — 売上: ¥148,500 / 販売数: 33個
> 2. ロゴキャップ（フリーサイズ） — 売上: ¥89,100 / 販売数: 27個
> ...

管理画面を開かずにチャットで完結します。EC-CUBEの公式MCP対応（[Issue #6347](https://github.com/EC-CUBE/ec-cube/issues/6347)）を待たずに、今すぐ使えます。

:::details TL;DR
- EC-CUBEのWeb APIプラグイン（GraphQL）＋ MCP Server（Node.js/TypeScript）を組み合わせる
- 実装するツール: 商品検索・在庫確認・在庫更新・売上集計・売上ランキングの5つ
- カスタムツール機能でGraphQLクエリを自由に追加できる
- 顧客・注文の個人情報は一切扱わない
:::

:::details MCPとは？
MCP（Model Context Protocol）はAnthropicが策定したオープン標準プロトコルで、ClaudeなどのAIを外部システムと接続するための仕組みです。MCPサーバーを実装することで、Claudeに「ツール」として独自の機能を追加できます。
:::

## できること・できないこと

| 操作 | 可否 |
|------|------|
| 商品検索・詳細取得 | ✅ |
| 在庫数の確認 | ✅ |
| 在庫数の更新 | ✅ |
| 売上集計（日次・月次） | ✅ |
| 売れ筋商品ランキング | ✅ |
| カスタムGraphQLクエリ | ✅ |
| 商品の新規作成 | ❌（Mutationなし） |
| 商品説明文の更新 | ❌（Mutationなし） |
| 顧客・注文情報の取得 | 🚫（個人情報保護のため意図的に除外） |

## 前提条件

- EC-CUBE 4.3 が稼働していること
- Web APIプラグイン（`Api42`）がインストール済みであること
- Node.js 18以上
- Claude Desktop または Claude Code がインストール済みであること

## Web API プラグインのセットアップ

### インストール

管理画面のオーナーズストアからインストールするか、コマンドラインで実行します。

```bash
bin/console eccube:composer:require ec-cube/Api42
bin/console eccube:plugin:enable --code=Api42
```

### アクセストークンの取得

**[Web API 個人用アクセストークン生成プラグイン](https://www.ec-cube.net/products/detail.php?product_id=3467)** を使うと、OAuthクライアントの登録手順を省略して個人用のアクセストークンをかんたんに発行できます。

OAuth管理から取得する場合は、管理画面の **設定 → API管理 → OAuth管理** からクライアントを登録してアクセストークンを取得してください。

:::message
アクセストークンは1時間で失効します。リフレッシュトークン・クライアントID・クライアントシークレットの3つを設定すると、期限切れ時に自動でトークンを更新できます。
:::

## MCPサーバーの実装

### プロジェクト構成

```
eccube-mcp-server/
├── src/
│   ├── index.ts          # エントリポイント・サーバー起動
│   ├── tools.ts          # GraphQLクライアント・ユーティリティ
│   ├── custom-tools.ts   # カスタムツール読み込み
│   └── handlers/
│       ├── search-products.ts   # 商品検索
│       ├── check-stock.ts       # 在庫確認
│       ├── update-stock.ts      # 在庫更新
│       ├── analyze-sales.ts     # 売上集計
│       └── get-sales-ranking.ts # 売上ランキング
├── setup.js              # GUIセットアップツール
├── package.json
└── tsconfig.json
```

### package.json

```json
{
  "name": "eccube-mcp-server",
  "version": "1.1.1",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch",
    "setup": "node setup.js"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.22.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}
```

### GraphQLクライアント（src/tools.ts）

EC-CUBE GraphQL APIとの通信部分です。Bearer認証とトークン自動更新に対応しています。

```typescript
export type EccubeGraphQL = (query: string, variables?: Record<string, unknown>) => Promise<unknown>;

export interface RefreshConfig {
  refreshToken: string;
  clientId: string;
  clientSecret: string;
}

export async function refreshAccessToken(
  apiUrl: string,
  config: RefreshConfig
): Promise<{ accessToken: string; refreshToken?: string }> {
  const resp = await fetch(`${apiUrl}/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "refresh_token",
      refresh_token: config.refreshToken,
      client_id: config.clientId,
      client_secret: config.clientSecret,
    }),
  });
  if (!resp.ok) {
    throw new Error(`トークンのリフレッシュに失敗しました: ${resp.status}`);
  }
  const data = (await resp.json()) as { access_token?: string; refresh_token?: string };
  if (!data.access_token) {
    throw new Error("レスポンスにアクセストークンが含まれていません");
  }
  return { accessToken: data.access_token, refreshToken: data.refresh_token };
}

export function createEccubeClient(
  apiUrl: string,
  accessToken: string,
  refreshConfig?: RefreshConfig
) {
  let currentToken = accessToken;

  return async function eccubeGraphQL(
    query: string,
    variables: Record<string, unknown> = {}
  ): Promise<unknown> {
    const makeRequest = (token: string) =>
      fetch(`${apiUrl}/api`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ query, variables }),
      });

    let response = await makeRequest(currentToken);

    // 401の場合はトークンをリフレッシュして再試行
    if (response.status === 401 && refreshConfig) {
      const tokens = await refreshAccessToken(apiUrl, refreshConfig);
      currentToken = tokens.accessToken;
      if (tokens.refreshToken) {
        refreshConfig.refreshToken = tokens.refreshToken;
      }
      response = await makeRequest(currentToken);
    }

    if (!response.ok) {
      throw new Error(`EC-CUBE API エラー: ${response.status} ${response.statusText}`);
    }

    const json = (await response.json()) as { data?: unknown; errors?: unknown[] };

    if (json.errors) {
      console.error("GraphQL エラー詳細:", JSON.stringify(json.errors));
      throw new Error("GraphQL エラーが発生しました");
    }

    return json.data;
  };
}

export function clampLimit(limit: number): number {
  return Math.min(Math.max(1, limit), 50);
}

export function formatStockInfo(stock: number | null, unlimited: boolean): string {
  return unlimited ? "在庫無制限" : `在庫: ${stock ?? 0}個`;
}
```

### エントリポイント（src/index.ts）

各ハンドラーを登録してサーバーを起動します。

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createEccubeClient, RefreshConfig } from "./tools.js";
import { registerSearchProducts } from "./handlers/search-products.js";
import { registerCheckStock } from "./handlers/check-stock.js";
import { registerUpdateStock } from "./handlers/update-stock.js";
import { registerAnalyzeSales } from "./handlers/analyze-sales.js";
import { registerGetSalesRanking } from "./handlers/get-sales-ranking.js";

const ECCUBE_API_URL = process.env.ECCUBE_API_URL;
const ECCUBE_ACCESS_TOKEN = process.env.ECCUBE_ACCESS_TOKEN;
const ECCUBE_REFRESH_TOKEN = process.env.ECCUBE_REFRESH_TOKEN;
const ECCUBE_CLIENT_ID = process.env.ECCUBE_CLIENT_ID;
const ECCUBE_CLIENT_SECRET = process.env.ECCUBE_CLIENT_SECRET;

if (!ECCUBE_API_URL || !ECCUBE_ACCESS_TOKEN) {
  console.error("ECCUBE_API_URL と ECCUBE_ACCESS_TOKEN を環境変数に設定してください");
  process.exit(1);
}

let refreshConfig: RefreshConfig | undefined;
if (ECCUBE_REFRESH_TOKEN && ECCUBE_CLIENT_ID && ECCUBE_CLIENT_SECRET) {
  refreshConfig = {
    refreshToken: ECCUBE_REFRESH_TOKEN,
    clientId: ECCUBE_CLIENT_ID,
    clientSecret: ECCUBE_CLIENT_SECRET,
  };
}

const eccubeGraphQL = createEccubeClient(ECCUBE_API_URL, ECCUBE_ACCESS_TOKEN, refreshConfig);

const server = new McpServer({
  name: "eccube-product-mcp",
  version: "1.0.0",
});

registerSearchProducts(server, eccubeGraphQL);
registerCheckStock(server, eccubeGraphQL);
registerUpdateStock(server, eccubeGraphQL);
registerAnalyzeSales(server, eccubeGraphQL);
registerGetSalesRanking(server, eccubeGraphQL);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  // stdioサーバーでは console.log() は使用禁止（JSON-RPCメッセージを壊す）
  console.error("EC-CUBE MCP Server が起動しました");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
```

### ツール1: 商品検索（src/handlers/search-products.ts）

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { clampLimit, EccubeGraphQL } from "../tools.js";

export function registerSearchProducts(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
  server.registerTool(
    "search_products",
    {
      description: "EC-CUBEの商品を商品名・商品コードで検索します。在庫数や価格も確認できます。",
      inputSchema: {
        keyword: z.string().describe("検索キーワード（商品名または商品コード）"),
        limit: z.number().optional().describe("取得件数（デフォルト: 10、最大: 50）"),
      },
    },
    async ({ keyword, limit = 10 }) => {
      try {
        const safeLimit = clampLimit(limit);
        const query = `
          query SearchProducts($id: String, $limit: Int) {
            products(id: $id, limit: $limit) {
              edges {
                node {
                  id
                  name
                  description_list
                  ProductClasses {
                    id
                    code
                    stock
                    stock_unlimited
                    price02
                  }
                }
              }
            }
          }
        `;

        const data = (await eccubeGraphQL(query, { id: keyword, limit: safeLimit })) as {
          products: { edges: { node: unknown }[] };
        };

        const products = data.products.edges.map((e) => e.node);

        if (products.length === 0) {
          return { content: [{ type: "text" as const, text: "該当する商品が見つかりませんでした。" }] };
        }

        return { content: [{ type: "text" as const, text: JSON.stringify(products, null, 2) }] };
      } catch (err) {
        const message = err instanceof Error ? err.message : "不明なエラーが発生しました";
        return { content: [{ type: "text" as const, text: message }], isError: true };
      }
    }
  );
}
```

### ツール2: 在庫確認（src/handlers/check-stock.ts）

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { formatStockInfo, EccubeGraphQL } from "../tools.js";

export function registerCheckStock(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
  server.registerTool(
    "check_stock",
    {
      description: "商品コードを指定して在庫数を確認します。在庫切れや在庫僅少の商品を調べるのに使います。",
      inputSchema: {
        keyword: z.string().describe("商品名または商品コード"),
      },
    },
    async ({ keyword }) => {
      try {
        const query = `
          query CheckStock($id: String) {
            products(id: $id, limit: 50) {
              edges {
                node {
                  name
                  ProductClasses {
                    code
                    stock
                    stock_unlimited
                  }
                }
              }
            }
          }
        `;

        const data = (await eccubeGraphQL(query, { id: keyword })) as {
          products: {
            edges: {
              node: {
                name: string;
                ProductClasses: { code: string; stock: number | null; stock_unlimited: boolean }[];
              };
            }[];
          };
        };

        const lines: string[] = [];
        for (const edge of data.products.edges) {
          const product = edge.node;
          for (const pc of product.ProductClasses) {
            lines.push(`【${product.name}】規格コード: ${pc.code} / ${formatStockInfo(pc.stock, pc.stock_unlimited)}`);
          }
        }

        if (lines.length === 0) {
          return { content: [{ type: "text" as const, text: "該当する商品が見つかりませんでした。" }] };
        }

        return { content: [{ type: "text" as const, text: lines.join("\n") }] };
      } catch (err) {
        const message = err instanceof Error ? err.message : "不明なエラーが発生しました";
        return { content: [{ type: "text" as const, text: message }], isError: true };
      }
    }
  );
}
```

### ツール3: 在庫更新（src/handlers/update-stock.ts）

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { EccubeGraphQL } from "../tools.js";

export function registerUpdateStock(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
  server.registerTool(
    "update_stock",
    {
      description:
        "商品規格コードを指定して在庫数を更新します。在庫無制限にすることもできます。【重要】この操作は即座にデータベースに反映され取り消せません。実行前に必ずユーザーに内容を確認してください。",
      inputSchema: {
        code: z.string().describe("商品規格コード"),
        stock: z.number().optional().describe("新しい在庫数（stock_unlimited が false の場合は必須）"),
        stock_unlimited: z.boolean().optional().describe("在庫無制限にする場合は true（デフォルト: false）"),
      },
    },
    async ({ code, stock, stock_unlimited = false }) => {
      if (!stock_unlimited && stock === undefined) {
        return {
          content: [{ type: "text" as const, text: "在庫無制限でない場合は stock（在庫数）を指定してください。" }],
          isError: true,
        };
      }

      try {
        const mutation = `
          mutation UpdateStock($code: String!, $stock: Int, $stock_unlimited: Boolean!) {
            updateProductStock(code: $code, stock: $stock, stock_unlimited: $stock_unlimited) {
              id
              stock
              stock_unlimited
            }
          }
        `;

        const result = (await eccubeGraphQL(mutation, { code, stock, stock_unlimited })) as {
          updateProductStock: { id: number; stock: number | null; stock_unlimited: boolean } | null;
        };

        if (!result.updateProductStock) {
          return {
            content: [{ type: "text" as const, text: `商品規格コード「${code}」が見つかりませんでした。` }],
            isError: true,
          };
        }

        const updated = result.updateProductStock;
        const message = updated.stock_unlimited
          ? `商品規格コード「${code}」の在庫を無制限に更新しました。`
          : `商品規格コード「${code}」の在庫を ${updated.stock} 個に更新しました。`;

        return { content: [{ type: "text" as const, text: message }] };
      } catch (err) {
        const message = err instanceof Error ? err.message : "不明なエラーが発生しました";
        return { content: [{ type: "text" as const, text: message }], isError: true };
      }
    }
  );
}
```

### ツール4: 売上集計（src/handlers/analyze-sales.ts）

指定期間の売上を日次・月次でグルーピングして集計します。

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { EccubeGraphQL } from "../tools.js";

export function registerAnalyzeSales(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
  server.registerTool(
    "analyze_sales",
    {
      description: "指定期間の売上を集計します。個人情報は含みません。",
      inputSchema: {
        from: z.string().describe("集計開始日（YYYY-MM-DD形式）"),
        to: z.string().describe("集計終了日（YYYY-MM-DD形式）"),
        group_by: z.enum(["day", "month"]).optional().describe("期間グルーピング（デフォルト: month）"),
      },
    },
    async ({ from, to, group_by = "month" }) => {
      try {
        const fromDatetime = `${from}T00:00:00+09:00`;
        const toDatetime = `${to}T23:59:59+09:00`;

        const query = `
          query GetOrders($from: DateTime, $to: DateTime, $limit: Int) {
            orders(
              order_datetime_start: $from
              order_datetime_end: $to
              limit: $limit
            ) {
              edges {
                node {
                  id
                  order_date
                  payment_total
                  OrderStatus { id name }
                  OrderItems { product_name price quantity }
                }
              }
            }
          }
        `;

        const data = (await eccubeGraphQL(query, { from: fromDatetime, to: toDatetime, limit: 100 })) as {
          orders: { edges: { node: { id: number; order_date: string; payment_total: number; OrderStatus: { id: number; name: string }; OrderItems: { product_name: string; price: number; quantity: number }[] } }[] };
        };

        const orders = data.orders.edges.map((e) => e.node);
        if (orders.length === 0) {
          return { content: [{ type: "text" as const, text: "指定期間の注文データが見つかりませんでした。" }] };
        }

        // group_by に応じてキーを生成する
        const periodKey = (dateStr: string): string => {
          const date = new Date(dateStr);
          if (group_by === "day") return date.toISOString().slice(0, 10);
          const y = date.getFullYear();
          const m = String(date.getMonth() + 1).padStart(2, "0");
          return `${y}-${m}`;
        };

        const groups = new Map<string, typeof orders>();
        for (const order of orders) {
          const key = periodKey(order.order_date);
          const list = groups.get(key) ?? [];
          list.push(order);
          groups.set(key, list);
        }

        const periods = Array.from(groups.entries())
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([period, groupOrders]) => {
            const order_count = groupOrders.length;
            const total_revenue = groupOrders.reduce((sum, o) => sum + o.payment_total, 0);
            return {
              period,
              order_count,
              total_revenue,
              average_order_value: Math.round(total_revenue / order_count),
              statuses: [...new Set(groupOrders.map((o) => `${o.OrderStatus.name}(id:${o.OrderStatus.id})`))],
            };
          });

        const overall_total = orders.reduce((sum, o) => sum + o.payment_total, 0);
        const result = {
          summary: { from, to, group_by, overall_order_count: orders.length, overall_total_revenue: overall_total, overall_average_order_value: Math.round(overall_total / orders.length) },
          periods,
        };

        return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
      } catch (err) {
        const message = err instanceof Error ? err.message : "不明なエラーが発生しました";
        return { content: [{ type: "text" as const, text: message }], isError: true };
      }
    }
  );
}
```

### ツール5: 売上ランキング（src/handlers/get-sales-ranking.ts）

指定期間の売れ筋商品を販売数量・売上金額でランキング表示します。

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { EccubeGraphQL } from "../tools.js";

export function registerGetSalesRanking(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
  server.registerTool(
    "get_sales_ranking",
    {
      description: "指定期間の売れ筋商品を販売数量・売上金額でランキング表示します。",
      inputSchema: {
        from: z.string().describe("集計開始日（YYYY-MM-DD形式）"),
        to: z.string().describe("集計終了日（YYYY-MM-DD形式）"),
        limit: z.number().optional().describe("表示件数（デフォルト: 10、最大: 50）"),
        sort_by: z.enum(["quantity", "revenue"]).optional().describe("ソート基準（デフォルト: quantity）"),
      },
    },
    async ({ from, to, limit = 10, sort_by = "quantity" }) => {
      try {
        const safeLimit = Math.min(Math.max(1, limit), 50);
        const query = `
          query GetOrders($from: DateTime, $to: DateTime, $limit: Int) {
            orders(order_datetime_start: $from, order_datetime_end: $to, limit: $limit) {
              edges {
                node {
                  OrderItems { product_name price quantity }
                }
              }
            }
          }
        `;

        const data = (await eccubeGraphQL(query, {
          from: `${from}T00:00:00+09:00`,
          to: `${to}T23:59:59+09:00`,
          limit: 100,
        })) as { orders: { edges: { node: { OrderItems: { product_name: string; price: number; quantity: number }[] } }[] } };

        const orders = data.orders.edges.map((e) => e.node);
        if (orders.length === 0) {
          return { content: [{ type: "text" as const, text: "指定期間の注文データが見つかりませんでした。" }] };
        }

        const productMap = new Map<string, { total_quantity: number; total_revenue: number; price_sum: number; price_count: number }>();
        for (const order of orders) {
          for (const item of order.OrderItems) {
            const existing = productMap.get(item.product_name) ?? { total_quantity: 0, total_revenue: 0, price_sum: 0, price_count: 0 };
            existing.total_quantity += item.quantity;
            existing.total_revenue += item.price * item.quantity;
            existing.price_sum += item.price;
            existing.price_count += 1;
            productMap.set(item.product_name, existing);
          }
        }

        const ranking = Array.from(productMap.entries())
          .sort(([, a], [, b]) => sort_by === "revenue" ? b.total_revenue - a.total_revenue : b.total_quantity - a.total_quantity)
          .slice(0, safeLimit)
          .map(([product_name, stats], index) => ({
            rank: index + 1,
            product_name,
            total_quantity: stats.total_quantity,
            total_revenue: stats.total_revenue,
            average_price: Math.round(stats.price_sum / stats.price_count),
          }));

        return { content: [{ type: "text" as const, text: JSON.stringify({ summary: { from, to, sort_by, displayed: ranking.length }, ranking }, null, 2) }] };
      } catch (err) {
        const message = err instanceof Error ? err.message : "不明なエラーが発生しました";
        return { content: [{ type: "text" as const, text: message }], isError: true };
      }
    }
  );
}
```

### ビルド

```bash
npm install
npm run build
```

`build/index.js` が生成されます。

## Claudeへの設定

### GUIでセットアップ（推奨）

```bash
npm run setup
```

実行するとブラウザが開き、EC-CUBEのURLとアクセストークンを入力するだけで Claude Desktop・Claude Code の両方に自動登録されます。

### 手動設定（Claude Code）

`~/.claude.json` を編集します。

```json
{
  "mcpServers": {
    "eccube": {
      "type": "stdio",
      "command": "node",
      "args": ["/絶対パス/eccube-mcp-server/build/index.js"],
      "env": {
        "ECCUBE_API_URL": "https://your-eccube-site.example.com",
        "ECCUBE_ACCESS_TOKEN": "取得したアクセストークン",
        "ECCUBE_REFRESH_TOKEN": "リフレッシュトークン（省略可）",
        "ECCUBE_CLIENT_ID": "クライアントID（省略可）",
        "ECCUBE_CLIENT_SECRET": "クライアントシークレット（省略可）"
      }
    }
  }
}
```

### 手動設定（Claude Desktop）

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%AppData%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "eccube": {
      "command": "node",
      "args": ["/絶対パス/eccube-mcp-server/build/index.js"],
      "env": {
        "ECCUBE_API_URL": "https://your-eccube-site.example.com",
        "ECCUBE_ACCESS_TOKEN": "取得したアクセストークン"
      }
    }
  }
}
```

:::message alert
`claude_desktop_config.json` にはアクセストークンがプレーンテキストで記録されます。このファイルをGitなどのバージョン管理システムに含めないようにしてください。
:::

設定後、Claudeを再起動するとEC-CUBEが利用できるようになります。

## カスタムツール

`~/.eccube-mcp/custom-tools.json` にツール定義を記述するだけで、独自のGraphQLクエリをMCPツールとして追加できます。

```json
{
  "tools": [
    {
      "name": "get_new_arrivals",
      "description": "新着商品を取得します",
      "query": "query { products(limit: 5) { edges { node { id name } } } }"
    }
  ]
}
```

ファイルが存在しない場合はエラーなく通常起動します。

## 動作確認

Claudeに以下のような指示ができます。サーバー名（デフォルト: `eccube`）を先頭に付けると、どのシステムへの操作か明確になります。

```
eccube で在庫が10個以下の商品を教えて
eccube の商品コードABC-001の在庫を50個に更新して
eccube で先月の売上を月次で集計して
eccube で今月の売れ筋商品トップ10を売上順で教えて
```

## 注意点

### 在庫更新は取り消せない

`update_stock` ツールはMutationを実行するため、誤った値を送信すると即座にDBに反映されます。ツールの description に「実行前に必ずユーザーに確認」と明記しているため、Claudeは実行前に確認を求めます。

### 個人情報は扱わない

顧客情報・注文情報のツールを意図的に実装していません。EC-CUBEのWeb APIには顧客・注文取得のQueryも存在しますが、個人情報をAIに送信することは個人情報保護法上のリスクがあるため除外しています。

## まとめ

- Node.js + TypeScript + MCP TypeScript SDK でEC-CUBE用MCPサーバーを実装
- GraphQL API経由でアクセスするため、EC-CUBEの環境を問わず導入可能
- 商品検索・在庫確認・在庫更新・売上集計・売上ランキングの5ツールを標準搭載
- トークン自動更新・カスタムツール・GUIセットアップに対応

現時点では商品説明文の更新・商品新規作成のMutationが存在しないため、EC-CUBE本体側のAPI拡張に期待したいところです。

## 参考リンク

- [EC-CUBE MCP Server（GitHub）](https://github.com/kurozumi/eccube-mcp-server)
- [GitHub Issue: MCPサーバーの実装](https://github.com/EC-CUBE/ec-cube/issues/6347)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)
- [Model Context Protocol](https://modelcontextprotocol.io/)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
