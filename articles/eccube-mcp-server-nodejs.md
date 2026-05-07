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

EC-CUBEのWeb APIプラグイン（GraphQL）と **MCP（Model Context Protocol）** を組み合わせると、Claude Desktopから自然言語でEC-CUBEの商品・在庫管理ができるようになります。動くコードとともに、約1〜2時間で構築できる実装方法を解説します。

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

管理画面を開かずにチャットで完結します。EC-CUBEの公式MCP対応（[Issue #6347](https://github.com/EC-CUBE/ec-cube/issues/6347)）を待たずに、今すぐ自分で実装してしまいましょう。

:::details TL;DR
- EC-CUBEのWeb APIプラグイン（GraphQL）＋ MCP Server（Node.js）を組み合わせる
- 実装するツール: 商品検索・在庫確認・在庫更新の3つ
- 顧客・注文データは一切扱わないため個人情報リスクなし
- 所要時間: 約1〜2時間
:::

:::details MCPとは？
MCP（Model Context Protocol）はAnthropicが策定したオープン標準プロトコルで、ClaudeなどのAIを外部システムと接続するための仕組みです。MCPサーバーを実装することで、Claudeに「ツール」として独自の機能を追加できます。
:::

## できること・できないこと

現在のEC-CUBE Web APIプラグイン（v4.3.2）のMutation（書き込み）は以下のみです。

| 操作 | 可否 |
|------|------|
| 商品検索・詳細取得 | ✅ |
| 在庫数の確認 | ✅ |
| 在庫数の更新 | ✅ |
| 商品の新規作成 | ❌（Mutationなし） |
| 商品説明文の更新 | ❌（Mutationなし） |
| 顧客・注文情報の取得 | 🚫（個人情報保護のため意図的に除外） |

本記事では✅の3機能を実装します。

## 前提条件

- EC-CUBE 4.3 が稼働していること
- Web APIプラグイン（`Api42`）がインストール済みであること
- Node.js 18以上
- Claude Desktop がインストール済みであること

## Web API プラグインのセットアップ

### インストール

管理画面のオーナーズストアからインストールするか、コマンドラインで実行します。

```bash
bin/console eccube:composer:require ec-cube/Api42
bin/console eccube:plugin:enable --code=Api42
```

### OAuth2クライアントの登録

Web APIプラグインはOAuth 2.0で保護されています。管理画面の **設定 → API管理 → OAuth管理** からクライアントを登録します。

- **クライアント名**: 任意（例: `claude-mcp`）
- **スコープ**: `read` と `write` の両方にチェック
- **リダイレクトURI**: `http://localhost:8080/callback`（トークン取得用）

登録後に表示される **クライアントID** と **クライアントシークレット** を控えておきます。

### アクセストークンの取得

Authorization Code フローでアクセストークンを取得します。以下のURLにブラウザでアクセスしてください。

```
https://your-eccube-site.example.com/authorize
  ?response_type=code
  &client_id={クライアントID}
  &redirect_uri=http://localhost:8080/callback
  &scope=read+write
```

EC-CUBEの管理者アカウントでログインして認可すると、リダイレクトURLにコード（`?code=xxx`）が付与されます。このコードを使ってトークンを取得します。

```bash
curl -X POST https://your-eccube-site.example.com/token \
  -d "grant_type=authorization_code" \
  -d "code={取得したコード}" \
  -d "client_id={クライアントID}" \
  -d "client_secret={クライアントシークレット}" \
  -d "redirect_uri=http://localhost:8080/callback"
```

レスポンスに含まれる `access_token` を控えておきます（有効期限: 3600秒）。

:::message alert
**セキュリティ注意**: 上記の `curl` コマンドはシェルの実行履歴（`~/.bash_history` / `~/.zsh_history`）にクライアントシークレットが残ります。履歴に残したくない場合は、コマンド先頭にスペースを入れる（`HISTCONTROL=ignorespace` が設定されている場合）か、実行後に `history -d` で該当行を削除してください。
:::

:::message
アクセストークンは1時間で失効します。本記事では簡易実装のため環境変数にセットする方式を採用しています。長期運用する場合はリフレッシュトークンを使った自動更新の実装を検討してください。
:::

## MCPサーバーの実装

### プロジェクト構成

```
eccube-mcp/
├── package.json
├── tsconfig.json
└── src/
    └── index.ts
```

### package.json

```json
{
  "name": "eccube-mcp",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "build": "tsc",
    "dev": "tsc --watch"
  },
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "zod": "^3.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0",
    "typescript": "^5.0.0"
  }
}
```

### tsconfig.json

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "Node16",
    "moduleResolution": "Node16",
    "outDir": "./build",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  }
}
```

### src/index.ts

```typescript
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const ECCUBE_API_URL = process.env.ECCUBE_API_URL;
const ECCUBE_ACCESS_TOKEN = process.env.ECCUBE_ACCESS_TOKEN;

if (!ECCUBE_API_URL || !ECCUBE_ACCESS_TOKEN) {
  console.error("ECCUBE_API_URL と ECCUBE_ACCESS_TOKEN を環境変数に設定してください");
  process.exit(1);
}

async function eccubeGraphQL(
  query: string,
  variables: Record<string, unknown> = {}
): Promise<unknown> {
  const response = await fetch(`${ECCUBE_API_URL}/api`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${ECCUBE_ACCESS_TOKEN}`,
    },
    body: JSON.stringify({ query, variables }),
  });

  if (!response.ok) {
    throw new Error(`EC-CUBE API エラー: ${response.status} ${response.statusText}`);
  }

  const json = (await response.json()) as { data?: unknown; errors?: unknown[] };

  if (json.errors) {
    throw new Error(`GraphQL エラー: ${JSON.stringify(json.errors)}`);
  }

  return json.data;
}

const server = new McpServer({
  name: "eccube-product-mcp",
  version: "1.0.0",
});

// ツール1: 商品検索
server.registerTool(
  "search_products",
  {
    description:
      "EC-CUBEの商品を商品名・商品コードで検索します。在庫数や価格も確認できます。",
    inputSchema: {
      keyword: z.string().describe("検索キーワード（商品名または商品コード）"),
      limit: z.number().optional().describe("取得件数（デフォルト: 10、最大: 50）"),
    },
  },
  async ({ keyword, limit = 10 }) => {
    // AIが大きな値を渡しても上限を超えないよう制限する
    const safeLimit = Math.min(Math.max(1, limit), 50);
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

    const data = (await eccubeGraphQL(query, { id: keyword, limit })) as {
      products: { edges: { node: unknown }[] };
    };

    const products = data.products.edges.map((e) => e.node);

    if (products.length === 0) {
      return {
        content: [{ type: "text" as const, text: "該当する商品が見つかりませんでした。" }],
      };
    }

    return {
      content: [{ type: "text" as const, text: JSON.stringify(products, null, 2) }],
    };
  }
);

// ツール2: 在庫確認
server.registerTool(
  "check_stock",
  {
    description:
      "商品コードを指定して在庫数を確認します。在庫切れや在庫僅少の商品を調べるのに使います。",
    inputSchema: {
      keyword: z.string().describe("商品名または商品コード"),
    },
  },
  async ({ keyword }) => {
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
        const stockInfo = pc.stock_unlimited
          ? "在庫無制限"
          : `在庫: ${pc.stock ?? 0}個`;
        lines.push(`【${product.name}】規格コード: ${pc.code} / ${stockInfo}`);
      }
    }

    if (lines.length === 0) {
      return {
        content: [{ type: "text" as const, text: "該当する商品が見つかりませんでした。" }],
      };
    }

    return {
      content: [{ type: "text" as const, text: lines.join("\n") }],
    };
  }
);

// ツール3: 在庫更新
server.registerTool(
  "update_stock",
  {
    description:
      "商品規格コードを指定して在庫数を更新します。在庫無制限にすることもできます。【重要】この操作は即座にデータベースに反映され取り消せません。実行前に必ずユーザーに内容を確認してください。",
    inputSchema: {
      code: z.string().describe("商品規格コード"),
      stock: z.number().optional().describe("新しい在庫数（stock_unlimited が false の場合は必須）"),
      stock_unlimited: z
        .boolean()
        .optional()
        .describe("在庫無制限にする場合は true（デフォルト: false）"),
    },
  },
  async ({ code, stock, stock_unlimited = false }) => {
    if (!stock_unlimited && stock === undefined) {
      return {
        content: [
          {
            type: "text" as const,
            text: "在庫無制限でない場合は stock（在庫数）を指定してください。",
          },
        ],
      };
    }

    const mutation = `
      mutation UpdateStock($code: String!, $stock: Int, $stock_unlimited: Boolean!) {
        updateProductStock(code: $code, stock: $stock, stock_unlimited: $stock_unlimited) {
          id
          stock
          stock_unlimited
        }
      }
    `;

    await eccubeGraphQL(mutation, { code, stock, stock_unlimited });

    const message = stock_unlimited
      ? `商品規格コード「${code}」の在庫を無制限に更新しました。`
      : `商品規格コード「${code}」の在庫を ${stock} 個に更新しました。`;

    return {
      content: [{ type: "text" as const, text: message }],
    };
  }
);

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

### ビルド

```bash
npm install
npm run build
```

`build/index.js` が生成されます。

## Claude Desktop への設定

Claude Desktop の設定ファイルを編集します。

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%AppData%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "eccube": {
      "command": "node",
      "args": ["/絶対パス/eccube-mcp/build/index.js"],
      "env": {
        "ECCUBE_API_URL": "https://your-eccube-site.example.com",
        "ECCUBE_ACCESS_TOKEN": "取得したアクセストークン"
      }
    }
  }
}
```

:::message alert
**セキュリティ注意**: `claude_desktop_config.json` にはアクセストークンがプレーンテキストで記録されます。このファイルをGitなどのバージョン管理システムに含めないようにしてください。また、`ECCUBE_API_URL` には必ず `https://` から始まるURLを指定してください。`http://` の場合、アクセストークンが平文でネットワークに流れます。
:::

設定後、Claude Desktopを再起動します。

## 動作確認

Claude Desktopを起動してMCPツールが認識されているか確認します。チャット画面の左下にツールアイコンが表示されていればOKです。

以下のようなプロンプトで動作を確認します。

**商品検索:**
```
「Tシャツ」という商品を検索して、在庫数と価格を教えてください。
```

**在庫確認:**
```
在庫が10個以下の商品を全部教えてください。
```

**在庫更新:**
```
商品コード「T-001」の在庫を100に更新してください。
```

## 注意点

### アクセストークンの有効期限

取得したアクセストークンは **1時間で失効** します。失効した場合はリフレッシュトークンを使って再取得し、設定ファイルを更新してClaude Desktopを再起動してください。継続的に運用する場合は、リフレッシュトークンを使った自動更新の仕組みを別途実装することを推奨します。

### 個人情報は扱わない

本実装では顧客情報・注文情報のツールを意図的に実装していません。EC-CUBEのWeb APIには顧客・注文取得のQueryも存在しますが、個人情報をAI（外部サーバー）に送信することは個人情報保護法上のリスクがあるため除外しています。

### 在庫更新は取り消せない

`update_stock` ツールはMutationを実行するため、誤った値を送信すると即座にDBに反映されます。Claude に在庫更新を依頼する際は必ず内容を確認してから実行するようにしてください。

## まとめ

EC-CUBEのWeb APIプラグイン（GraphQL）とMCP Server（Node.js）を組み合わせることで、Claudeから自然言語でEC-CUBEの商品・在庫管理ができるようになります。

- 商品検索・在庫確認・在庫更新の3ツールを実装
- 個人情報（顧客・注文）は扱わず法的リスクを回避
- Web APIプラグインのMutationが増えれば機能拡張が容易

現時点では商品説明文の更新・商品新規作成のMutationが存在しないため、EC-CUBE本体側のAPI拡張に期待したいところです。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
