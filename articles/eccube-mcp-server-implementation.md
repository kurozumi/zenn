---
title: "EC-CUBE 4用MCPサーバーを作ってAI開発を効率化する"
emoji: "🤖"
type: "tech"
topics: ["eccube", "eccube4", "nodejs", "mcp", "ai"]
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

**MCP（Model Context Protocol）** は、AIアシスタントが外部ツールやデータソースと連携するためのオープンプロトコルです。MCPサーバーを実装することで、Claude等のAIがEC-CUBEの商品データや売上情報に直接アクセスできるようになります。

本記事では、EC-CUBE 4用のMCPサーバーをNode.jsで実装し、AI駆動の開発・運用を効率化する方法を解説します。

:::message
この記事で紹介するMCPサーバーは、OSSとして公開しています。
**GitHub**: https://github.com/kurozumi/eccube-mcp-server
:::

## アーキテクチャ

このMCPサーバーは **EC-CUBEのGraphQL API（Web APIプラグイン）経由** でデータにアクセスします。データベースに直接接続しないため、EC-CUBEのインストール環境を問わず利用できます。

```
Claude Desktop / Claude Code
        │
        │ MCP (stdio)
        ▼
EC-CUBE MCP Server（Node.js）
        │
        │ GraphQL API (HTTP)
        ▼
EC-CUBE 4（Web APIプラグイン）
        │
        ▼
     Database
```

## MCPサーバーで実現できること

EC-CUBE用MCPサーバーを導入すると、以下のようなことが可能になります。

- 「在庫切れの商品を教えて」→ AIが商品コードで検索して在庫状況を回答
- 「商品コードABC-001の在庫を50個に更新して」→ 在庫をリアルタイムで更新
- 「先月の売上を月次で集計して」→ 売上サマリーを自動集計
- 「今月の売れ筋商品トップ10を教えて」→ 販売数量・売上金額でランキング表示

## 必要なもの

- EC-CUBE 4.3以上
- Web APIプラグイン（Api42）インストール済み
- Node.js 18以上
- Claude Desktop または Claude Code

## クイックセットアップ

### GUIでセットアップ（推奨）

コマンドラインを使わずにブラウザからセットアップできます。

1. **[最新リリース](https://github.com/kurozumi/eccube-mcp-server/releases/latest)** からランチャーをダウンロード
   - **Mac**: `launcher-mac.zip` を展開して `eccube-mcp-setup.command` をダブルクリック
   - **Windows**: `launcher-windows.zip` を展開して `eccube-mcp-setup.bat` をダブルクリック
2. ブラウザが自動で開きます。EC-CUBEのURLとアクセストークンを入力して「Claudeに登録する」ボタンを押すだけです
3. Claudeを再起動すると利用できるようになります

> **Macの注意**: 初回起動時にセキュリティ警告が出る場合は、右クリック→「開く」を選択してください。

### コマンドラインからセットアップ

```bash
git clone https://github.com/kurozumi/eccube-mcp-server.git
cd eccube-mcp-server
npm install
npm run setup
```

セットアップコマンドを実行するとブラウザが開き、GUIでEC-CUBEのURLとアクセストークンを入力できます。

## アクセストークンの取得

EC-CUBE管理画面の **設定 → API管理 → OAuth管理** からOAuthクライアントを登録し、アクセストークンを取得してください。

アクセストークンの有効期限は1時間です。**リフレッシュトークン**・**クライアントID**・**クライアントシークレット**の3つを合わせて設定すると、期限切れ時に自動でトークンを更新します。

## 実装の詳細

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

### GraphQLクライアント

EC-CUBE GraphQL APIとの通信部分です。Bearer認証とトークン自動更新に対応しています。

```typescript
// src/tools.ts

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
      response = await makeRequest(currentToken);
    }

    const json = (await response.json()) as {
      data?: unknown;
      errors?: unknown[];
    };

    if (json.errors) {
      throw new Error("GraphQL エラーが発生しました");
    }

    return json.data;
  };
}
```

### 商品検索ツール

```typescript
// src/handlers/search-products.ts

export function registerSearchProducts(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
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

      const data = await eccubeGraphQL(query, { id: keyword, limit: safeLimit });
      // ... レスポンス処理
    }
  );
}
```

### 在庫更新ツール

```typescript
// src/handlers/update-stock.ts

export function registerUpdateStock(server: McpServer, eccubeGraphQL: EccubeGraphQL): void {
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
      const mutation = `
        mutation UpdateStock($code: String!, $stock: Int, $stock_unlimited: Boolean!) {
          updateProductStock(code: $code, stock: $stock, stock_unlimited: $stock_unlimited) {
            id
            stock
            stock_unlimited
          }
        }
      `;
      // ... Mutation実行
    }
  );
}
```

## 利用可能なツール一覧

| ツール | 説明 |
|--------|------|
| `search_products` | キーワード（商品名・商品コード）で商品を検索。価格・在庫情報も取得 |
| `check_stock` | 商品名または商品コードを指定して在庫数を確認 |
| `update_stock` | 商品規格コードを指定して在庫数を更新。在庫無制限の設定も可能 |
| `analyze_sales` | 指定期間の売上を日次・月次で集計。注文件数・売上合計・平均注文金額を取得 |
| `get_sales_ranking` | 指定期間の売れ筋商品を販売数量・売上金額でランキング表示 |

## カスタムツール

`~/.eccube-mcp/custom-tools.json` にツール定義を記述するだけで、独自のGraphQLクエリをMCPツールとして追加できます。

```json
{
  "tools": [
    {
      "name": "get_monthly_revenue",
      "description": "月別売上を集計",
      "query": "{ orders { id totalPrice } }",
      "inputSchema": {
        "type": "object",
        "properties": {
          "from": { "type": "string", "description": "開始日(YYYY-MM-DD)" },
          "to": { "type": "string", "description": "終了日(YYYY-MM-DD)" }
        },
        "required": ["from", "to"]
      }
    }
  ]
}
```

ファイルが存在しない場合はエラーなく通常起動します。

## 手動設定

GUIセットアップを使わず手動で設定することもできます。

### Claude Code

`~/.claude.json` を編集します。

```json
{
  "mcpServers": {
    "eccube": {
      "type": "stdio",
      "command": "node",
      "args": ["/path/to/eccube-mcp-server/build/index.js"],
      "env": {
        "ECCUBE_API_URL": "https://your-eccube-site.com",
        "ECCUBE_ACCESS_TOKEN": "your-access-token",
        "ECCUBE_REFRESH_TOKEN": "your-refresh-token",
        "ECCUBE_CLIENT_ID": "your-client-id",
        "ECCUBE_CLIENT_SECRET": "your-client-secret"
      }
    }
  }
}
```

### Claude Desktop（macOS）

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集します。

```json
{
  "mcpServers": {
    "eccube": {
      "command": "node",
      "args": ["/path/to/eccube-mcp-server/build/index.js"],
      "env": {
        "ECCUBE_API_URL": "https://your-eccube-site.com",
        "ECCUBE_ACCESS_TOKEN": "your-access-token"
      }
    }
  }
}
```

リフレッシュトークンを使わない場合は `ECCUBE_REFRESH_TOKEN`・`ECCUBE_CLIENT_ID`・`ECCUBE_CLIENT_SECRET` の3行を省略できます。

## 複数のEC-CUBEを使い分ける

本番環境とステージング環境など、複数のEC-CUBEを登録して使い分けることができます。セットアップ画面の「サーバー名」に区別できる名前を入力して、それぞれ登録します。

| サーバー名 | 用途 |
|-----------|------|
| `eccube-production` | 本番環境 |
| `eccube-staging` | ステージング環境 |

Claudeへはサーバー名を含めて話しかけると迷わず操作してもらえます。

```
「eccube で在庫が10個以下の商品を教えて」
「eccube の商品コードABC-001の在庫を50個に更新して」
「eccube で先月の売上を月次で集計して」
「eccube-staging の在庫を確認して」
```

## 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `ECCUBE_API_URL` | Yes | EC-CUBEサイトのURL（例: `https://your-eccube-site.com`） |
| `ECCUBE_ACCESS_TOKEN` | Yes | Web APIプラグインで発行したアクセストークン |
| `ECCUBE_REFRESH_TOKEN` | No | アクセストークン自動更新用のリフレッシュトークン |
| `ECCUBE_CLIENT_ID` | No | OAuth クライアントID |
| `ECCUBE_CLIENT_SECRET` | No | OAuth クライアントシークレット |

## セキュリティ上の注意

1. **在庫更新は取り消せません**: `update_stock` ツールは即座にDBへ反映されます。実行前にClaudeが確認を求める設計になっています
2. **個人情報保護**: 顧客・受注の個人情報へのアクセスは実装していません
3. **アクセストークンの管理**: トークンは設定ファイルに平文で保存されます。ファイルのアクセス権限に注意してください
4. **HTTPS推奨**: 本番環境では必ずHTTPSで通信してください

## まとめ

- Node.js + TypeScript + MCP TypeScript SDK でEC-CUBE用MCPサーバーを実装
- GraphQL API経由でアクセスするため、EC-CUBEの環境を問わず導入可能
- GUIセットアップツール付きで、コマンドライン不要でも設定できる
- 商品検索・在庫確認・在庫更新・売上集計・売上ランキングの5ツールを標準搭載
- カスタムツール機能でGraphQLクエリを追加定義可能

## 参考リンク

- [EC-CUBE MCP Server（GitHub）](https://github.com/kurozumi/eccube-mcp-server) - 本記事で紹介したMCPサーバーのOSS
- [EC-CUBEとClaudeを連携させるMCPサーバーをNode.jsで作った](https://zenn.dev/kurozumi/articles/eccube-mcp-server-nodejs)
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
