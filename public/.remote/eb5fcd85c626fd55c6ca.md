---
title: EC-CUBEプラグイン開発をAIで効率化してみた
tags:
  - PHP
  - Symfony
  - EC-CUBE
  - AI
private: false
updated_at: '2026-03-25T20:03:27+09:00'
id: eb5fcd85c626fd55c6ca
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBEプラグイン開発をAIで効率化してみた](https://zenn.dev/kurozumi/articles/eccube-plugin-dev-with-ai)**

---

EC-CUBE 4 系プラグイン開発において、AI（Claude Code）を活用して効率化を試みた事例を紹介します。設計フェーズとレビューフェーズで特に役立ったので、具体的な活用方法を共有します。

## 背景と課題

EC-CUBE 4 は Symfony ベースのため、プラグイン開発では以下の知識が求められます。

- Symfony のアーキテクチャ（DI、Form、Validator など）
- EC-CUBE 固有の拡張ポイント（Event、FormExtension など）
- PSR 準拠のコーディング規約

特に**設計フェーズ**と**コードレビュー対応**で時間がかかっていました。

| フェーズ | 従来の課題 |
|---------|-----------|
| 設計 | サービス分割の判断に迷う、責務が曖昧になりがち |
| 実装 | 既存コードとの整合性確認に時間がかかる |
| レビュー | 指摘への対応で手戻りが多い |

## 今回やったこと

### 対象

管理画面への機能追加プラグインを開発しました。

```
Plugin/
└── YourPlugin/
    ├── Controller/Admin/
    │   └── SampleController.php
    ├── Entity/
    │   └── Sample.php
    ├── Form/Type/Admin/
    │   └── SampleType.php
    ├── Repository/
    │   └── SampleRepository.php
    └── Service/
        └── SampleService.php
```

### 条件

- PHP 8.2
- PSR-12 準拠
- 既存の EC-CUBE プラグイン構造に合わせる

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBEプラグイン開発をAIで効率化してみた](https://zenn.dev/kurozumi/articles/eccube-plugin-dev-with-ai)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
