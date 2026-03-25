---
title: EC-CUBE 4でAIエージェント対応を実現する - Universal Commerce Protocol（UCP）入門
tags:
  - PHP
  - EC-CUBE
  - AI
  - Ecommerce
private: false
updated_at: '2026-03-25T15:45:34+09:00'
id: 60a083e71b265fa4bd88
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4でAIエージェント対応を実現する - Universal Commerce Protocol（UCP）入門](https://zenn.dev/kurozumi/articles/eccube-ucp-ai-commerce)**

---

## はじめに：AIがショッピングを変える時代

「AIに頼んで買い物してもらう」

そんな未来が、もう目の前に来ています。

Google の AI Mode in Search や Gemini アプリでは、ユーザーが「〇〇を買いたい」と話しかけるだけで、AIエージェントが商品を探し、比較し、購入まで完了してくれる世界が実現しつつあります。

この「AIエージェントによるショッピング」を可能にするのが、**Universal Commerce Protocol（UCP）** です。

## UCPとは何か？

**UCP（Universal Commerce Protocol）** は、Google と Shopify が中心となり、Etsy、Walmart、Target、Wayfair などの業界大手と共同開発した**オープンソースのプロトコル**です。

https://ucp.dev/

### 支持・参加企業

UCP には以下のような企業が参加・支持しています：

- **共同開発**: Google、Shopify、Etsy、Wayfair、Target、Walmart
- **決済プロバイダー**: Stripe、Adyen、PayPal、Mastercard、Visa、American Express、Klarna、Affirm
- **小売企業**: Best Buy、The Home Depot、Gap、Macy's、Zalando、Flipkart

40社以上がこのプロトコルを支持しており、**事実上の業界標準**になりつつあります。

### UCPが解決する問題

従来、AIエージェントが EC サイトで買い物をするには、サイトごとに個別の連携が必要でした。これは N × N の複雑性を生み出します。

UCPは「共通言語」を定義することで、**一度の実装で、あらゆるAIエージェントと連携**できるようになります。

```
従来: AIエージェントA × ECサイト1 + AIエージェントA × ECサイト2 + ...
UCP: AIエージェント ← UCP → ECサイト（共通インターフェース）
```

### UCPの技術的特徴

- **REST / JSON-RPC** によるシンプルな API
- **OAuth 2.0** による認証
- **Agent Payments Protocol (AP2)** による安全な決済
- **Agent2Agent (A2A)** / **Model Context Protocol (MCP)** との互換性
- **`/.well-known/ucp`** マニフェストによる機能の自動検出

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4でAIエージェント対応を実現する - Universal Commerce Protocol（UCP）入門](https://zenn.dev/kurozumi/articles/eccube-ucp-ai-commerce)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
