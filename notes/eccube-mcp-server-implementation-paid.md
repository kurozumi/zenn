## 環境構築

### 必要なもの

- EC-CUBE 4.3以上
- PHP 8.1以上
- Composer
- Claude Desktop または Claude Code

### プロジェクト構成

EC-CUBEのプロジェクトルートに `mcp-server` ディレクトリを作成します。


### MCP SDKのインストール


## MCPサーバーの実装

### EC-CUBEのブートストラップ

EC-CUBEのEntityManagerを使用するため、EC-CUBEのカーネルを起動します。


### 商品取得ツールの実装


### 受注取得ツールの実装


### MCPサーバーのエントリポイント


### Composerのオートロード設定


オートロードを更新します。


## Claude Desktopでの設定

Claude Desktopの設定ファイルにMCPサーバーを登録します。

### macOSの場合

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集します。


### Windowsの場合

`%APPDATA%\Claude\claude_desktop_config.json` を編集します。


設定後、Claude Desktopを再起動すると、MCPサーバーが利用可能になります。

## 使用例

Claude Desktopで以下のような質問ができるようになります。

### 商品検索


AIが `search_products` ツールを呼び出し、在庫切れ商品の一覧を返します。

### 売上確認


AIが `get_today_summary` ツールを呼び出し、本日の受注件数と売上合計を返します。

### 受注検索


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
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---