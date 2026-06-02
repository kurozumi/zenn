---
title: "EC-CUBEの顧客グループ別価格、Shopifyで実現しようとしたら月額¥368,000だった"
emoji: "💰"
type: "tech"
topics: ["eccube", "eccube4", "shopify", "php", "btob"]
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

## はじめに

「ShopifyはBtoB対応していますか？」——この質問、毎月のように受けます。

結論から言います。**Shopifyの標準プランでは顧客グループ別価格は使えません。使えるのはShopify Plusのみ、月額¥368,000〜（年間¥4,416,000〜）です。**

一方、EC-CUBEなら[CustomerGroupPriceプラグイン](https://github.com/kurozumi/eccube-plugin-customer-group-price)で低コストに実現できます。この記事では両プラットフォームの実装を技術・コストの両面で徹底比較します。

## 結論（TL;DR）

| | EC-CUBE | Shopify（標準プラン） | Shopify Plus |
|---|---|---|---|
| 顧客グループ別価格 | ✅ プラグインで実現可能 | ❌ 非対応 | ✅ ネイティブ対応 |
| 実装コスト | 低〜中 | - | 非常に高い |
| 月額費用（目安） | サーバー代のみ | ¥3,650〜 | ¥368,000〜 |
| カスタマイズ性 | 高い | 低い | 中程度 |

**Shopifyで顧客グループ別価格を実現するには、Shopify Plusが必要です（月額¥368,000〜、年間¥4,416,000〜）**。標準プランでは非対応のため、BtoB機能を重視するならEC-CUBEの方がコスト効率が高くなります。

## EC-CUBEのCustomerGroupPriceプラグイン

### 概要

[CustomerGroupPriceプラグイン](https://github.com/kurozumi/eccube-plugin-customer-group-price)は、EC-CUBE 4.2/4.3に対応した顧客グループ別価格プラグインです。

- **プラグインコード**: `CustomerGroupPrice42`
- **バージョン**: 4.3.2
- **前提プラグイン**: `CustomerGroup42`（会員グループ管理プラグイン）が有効であること

3つの価格設定方式を提供し、ログイン中の会員グループに応じて商品価格を自動的に切り替えます。

### データモデル

プラグインは `plg_customer_group_price` テーブルに、商品規格とグループの組み合わせごとの価格（DECIMAL 12,2）を保存します。`group_id` と `product_class_id` の組み合わせにユニーク制約が設けられており、同一グループ×商品規格の価格は1件のみ登録できます。

既存エンティティはTraitで拡張します。

| Trait | 対象エンティティ | 追加される項目 |
|---|---|---|
| `ProductClassTrait` | `ProductClass` | `groupPrices`（OneToMany） |
| `GroupTrait` | `Group` | `discountRate`（割引率）・`wholesaleRate`（掛け率）・`groupPrices` |
| `ConfigTrait` | `Config` | `roundingType`（端数処理方式） |

### 3種類の価格計算ストラテジー

プラグインはStrategyパターンを採用しており、3つの価格計算クラスが優先順位付きでDIコンテナに登録されています。

| クラス | 優先度 | 計算式 | 適用条件 |
|---|---|---|---|
| `WholesalePrice` | 100（最高） | `price02 × (wholesaleRate / 100)` | グループに割引率が設定されておらず、掛け率が設定されている |
| `DiscountPrice` | 50 | `price02 × ((100 - discountRate) / 100)` | グループに割引率が設定されている |
| `GroupPrice` | -100（最低） | DBに登録された固定価格 | 商品規格×グループの価格レコードが存在する |

`Context::getPrice()` は登録された全ストラテジーを順番に評価し、最後に `supports()` が `true` を返したものの価格を採用します。

### 価格が切り替わる仕組み

価格の切り替えはDoctrineの `postLoad` イベントで実現されています。商品規格（ProductClass）がDBから読み込まれた直後に会員グループを確認し、対応するグループ価格を計算して `price02` と `price02IncTax` を上書きします。これにより商品一覧・詳細・カートで自動的にグループ価格が表示されます。

また、EC-CUBE標準の `PriceChangeValidator`（カート内の価格変更チェック）を空実装で置き換えることで、グループ価格適用時にバリデーションエラーが発生しないよう対策されています（`PurchaseFlowPass`）。

### 管理機能

- 商品規格編集画面にグループ別価格入力欄を追加
- CSV一括インポート/エクスポート対応（`product_class_id`・`group_id`・`group_price` を指定）
- JPY通貨時のみ割引率・掛け率のUI表示
- 端数処理方式（四捨五入/切り捨て/切り上げ）をグループ設定画面で選択可能

## Shopifyでの顧客グループ別価格

### 標準プランでは非対応

**Shopifyの標準プラン（Basic/Grow/Advanced）では、顧客グループ別価格機能はネイティブサポートされていません。**

B2B向けのネイティブAPI（Company、CompanyLocation、Catalog、PriceList）は、Shopify Plusストアでのみ利用可能です。

| プラン | 月額（年払い） | 顧客グループ別価格 |
|---|---|---|
| Basic | ¥3,650 | ❌ |
| Grow | ¥10,100 | ❌ |
| Advanced | ¥44,000 | ❌ |
| Plus | ¥368,000〜 | ✅ |

標準プランで顧客グループ別価格を実現するには、サードパーティアプリを導入する必要があります。

### Shopify PlusのネイティブB2B機能

Shopify PlusはB2B機能を内蔵したエンタープライズ向けプランです。

**主なB2B機能**:
- 1ストアでB2C（D2C）とB2B販売を併用可能
- カタログ（Catalog）機能による顧客グループ別価格
- 法人顧客（Company/CompanyLocation）管理
- 数量ルール（最小・最大購入数、ロット単位）
- ボリュームディスカウント（量ベース価格）
- 下書き注文（Draft Order）・Shopify Flowとの連携

### カタログ（Catalog）とPriceListの仕組み

Shopify PlusのB2B価格管理は、**カタログ（Catalog）** と **価格リスト（PriceList）** の2つの概念で構成されます。

**エンティティ構造**: 法人顧客（Company）は複数の拠点（CompanyLocation）を持ちます。カタログは拠点単位で割り当て（1拠点最大25カタログ）、各カタログにPriceListが紐付く形です。

**PriceListの価格設定方式**:
1. **固定価格（Fixed Price）**: バリアントごとに価格を直接指定
2. **パーセンテージ調整（Percentage Adjustment）**: 元の価格に対して割合で増減

Admin APIのGraphQL mutationで価格リストの作成・更新・バリアント単位の固定価格設定が可能です（`write_products` スコープが必要）。

### CompanyとCompanyLocationの構造

Shopify PlusのB2Bは **Company（法人）→ CompanyLocation（拠点）→ CompanyContact（担当者）** の3層構造で管理します。CompanyContactは個人の顧客レコードと紐付き、CompanyLocationには独自の住所・税務番号・免税設定・決済条件（Net 30等）・カタログを設定できます。

価格はCompanyLocationレベルで割り当てるため、同じ会社でも拠点ごとに異なる価格体系を適用できます。

## EC-CUBE vs Shopify 技術比較

### 実装方法の比較

| 観点 | EC-CUBE（CustomerGroupPrice42） | Shopify Plus（B2B） |
|---|---|---|
| 価格管理単位 | 会員グループ × 商品規格 | CompanyLocation × カタログ |
| 価格設定方式 | 固定価格・割引率・掛け率（3種類） | 固定価格・パーセンテージ調整（2種類） |
| 価格切り替えタイミング | Doctrine postLoad（サーバーサイド） | APIレベルで制御 |
| カスタマイズ性 | ソースコード変更で自由に拡張可能 | GraphQL APIの範囲内 |
| CSV一括登録 | 対応（標準機能） | 未確認 |
| 端数処理設定 | 対応（四捨五入/切り捨て/切り上げ） | 未確認 |

### コスト比較

| 費用項目 | EC-CUBE | Shopify（標準） | Shopify Plus |
|---|---|---|---|
| プラットフォーム | 無料（OSS） | ¥3,650〜/月 | ¥368,000〜/月 |
| グループ別価格機能 | プラグイン費用（別途） | サードパーティアプリ | 標準機能で追加費用なし |
| サーバー費用 | 別途必要 | 不要 | 不要 |
| カスタマイズ費用 | 開発工数による | 限定的 | 限定的 |

### 柔軟性の比較

**EC-CUBEの強み**:
- 3種類の価格計算方式（固定価格・割引率・掛け率）をStrategyパターンで管理
- Doctrine EventListenerで価格ロジックをサーバーサイドで完全制御
- ソースコードが公開されているため、独自の価格計算ロジックの追加が可能
- 端数処理方式をグループごとに設定可能

**Shopify Plusの強み**:
- ノーコードで法人顧客管理ができる
- CompanyLocationレベルで異なる価格を管理（拠点別価格）
- 数量ルール（最小購入数・ロット単位）が組み込まれている
- インフラ管理が不要
- ボリュームディスカウントを標準サポート

## どちらを選ぶべきか

### EC-CUBEを選ぶべきケース

- **予算が限られている**: Shopify Plusは月額¥368,000〜と高額。EC-CUBEはプラグイン費用＋サーバー代のみで構築可能
- **価格計算ロジックが複雑**: 掛け率・割引率・固定価格を柔軟に使い分けたい
- **既存EC-CUBEサイトを運用中**: 現行システムをEC-CUBEで運用している場合
- **高いカスタマイズ性が必要**: ソースコードレベルで機能を拡張したい
- **国内BtoB市場向け**: 日本語サポート・日本の商習慣（端数処理等）への対応が充実

### Shopify Plusを選ぶべきケース

- **グローバル展開を視野に入れている**: 多通貨・多言語・国際物流に強い
- **ノーコードで管理したい**: 技術者なしで法人顧客・価格管理をしたい
- **D2C（BtoC）とBtoBを1ストアで運営したい**: Shopify PlusはBtoC/BtoB併用が可能
- **大規模なトラフィックに対応が必要**: Shopifyのインフラをそのまま活用したい
- **拠点単位で価格を管理したい**: 同一法人でも拠点ごとに異なる価格を設定したい

### 注意点

- Shopify標準プランでは顧客グループ別価格はネイティブ非対応です。サードパーティアプリが必要になります
- Shopify Plusへの移行コストは月額費用だけでなく、既存システムからのデータ移行費用も考慮してください
- EC-CUBEの場合、プラグインの保守・セキュリティアップデートへの対応も必要です
- Shopify Plusのサブスクリプション・プリオーダー機能はB2Bでは非対応です

## まとめ

顧客グループ別価格の実現という観点での比較：

- **EC-CUBE**: `CustomerGroupPriceプラグイン`を使えば低コストで実現可能。Strategyパターンによる柔軟な価格計算（固定価格・割引率・掛け率）が強み
- **Shopify**: 標準プランでは非対応。Shopify Plusならカタログ/PriceList機能で豊富なB2B機能が使えるが、月額¥368,000〜の費用が必要

BtoBのEC構築コストを抑えたい場合、EC-CUBEはShopifyの有力な代替となります。一方、グローバル展開や大規模インフラが必要な場合はShopify Plusも選択肢に入ります。

どちらが正解かはビジネス規模・予算・技術リソースによって異なります。まずは自社の要件を整理した上で、プラットフォームを選定することをおすすめします。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
