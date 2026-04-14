---
title: "Symfony 8.1 の #[RateLimit] とは？EC-CUBE のレート制限設計を整理する"
emoji: "🚦"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
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

Symfony のプルリクエスト [#63907](https://github.com/symfony/symfony/pull/63907) で、コントローラに PHP アトリビュートを付けるだけでレート制限を宣言できる `#[RateLimit]` が提案されています。「EC-CUBE でも使えるようになるの？」と気になった方も多いのではないでしょうか。

結論を先に言うと、**EC-CUBE 4.3（Symfony 6.4 ベース）では現時点で使えません**。しかし EC-CUBE はすでに `symfony/rate-limiter` を導入しており、独自のレート制限設計も持っています。本記事では PR #63907 の内容を紹介しつつ、EC-CUBE 4.3 の現在のレート制限実装を整理します。

## こんな方に読んでほしい

- Symfony の最新動向を EC-CUBE 目線で把握したい開発者
- EC-CUBE のログイン保護・スロットリング設定を理解したい方
- 将来の EC-CUBE バージョンアップに備えたい方

---

## PR #63907 「#[RateLimit]」とは

### 概要

Symfony PR #63907 は、**コントローラへのアトリビュート付与だけでレート制限を宣言できる機能**です。`RateLimiter` コンポーネント自体は Symfony 5.2 から存在しますが、従来はコントローラ内で手動でリミッターを取得・消費する命令型のコードが必要でした。PR #63907 はこれを宣言型に変えます。

### 現在のステータス

| 項目 | 内容 |
|------|------|
| ターゲットバージョン | Symfony **8.1**（2026年5月31日マイルストーン） |
| PR ステータス | **OPEN（未マージ）**、コアメンバーに Approved 済み |
| EC-CUBE 4.3 での利用 | **不可**（Symfony ^6.4 依存のため） |
| 6.4 へのバックポート | 現時点で予定なし |

### `#[RateLimit]` の仕組み

アトリビュートは `HttpKernel` コンポーネントに追加され（`HttpKernel/Attribute/RateLimit.php`）、`KernelEvents::CONTROLLER_ARGUMENTS` イベントをフックする `RateLimitAttributeListener` が処理を担います。

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `$limiter` | string（必須） | `framework.rate_limiter` で設定したリミッター名 |
| `$key` | string / Expression / Closure | バケットキー（省略時は IP + メソッド + パスを自動使用） |
| `$tokens` | int（デフォルト: 1） | 1リクエストで消費するトークン数 |
| `$methods` | array / string | 対象 HTTP メソッド（省略時は全メソッド） |

制限超過時は自動的に **HTTP 429 Too Many Requests** と `Retry-After` ヘッダーが返されます。

### 既存の命令型との対比

`#[RateLimit]` が実現するのは、**YAML で設定したリミッターへの参照を宣言的に書ける**という点です。リミッターの設定自体（ポリシー・上限回数・時間窓）は引き続き `framework.rate_limiter` で YAML 定義します。つまり `#[RateLimit]` はリミッターの「設定」ではなく「適用箇所の宣言」を簡潔にする機能です。

---

## EC-CUBE 4.3 の現在のレート制限設計

EC-CUBE 4.3 は `symfony/rate-limiter: ^6.4` を本体に含んでおり、いくつかのレート制限が標準で組み込まれています。

### ログインの保護（login_throttling）

EC-CUBE の管理画面・フロント両方のファイアウォールに Symfony の `login_throttling` 機能が設定されています。デフォルト値は以下の通りです。

| 設定項目 | デフォルト値 |
|---------|------------|
| 最大試行回数 | **5回** |
| 制限時間 | **30分** |

`login_throttling` は内部で2つのリミッターを使って制御します。

| リミッター | キー | 上限 |
|-----------|------|------|
| グローバル | **IP のみ** | max_attempts × 5（= 25回） |
| ローカル | **IP + ユーザー名** | max_attempts（= 5回） |

どちらかの上限に達した時点でスロットリングが発動します。制限超過時は「ログイン試行回数が多すぎます。〇〇分後に再度お試しください。」というメッセージが表示されます。完全なアカウントロックアウトではありません。

:::message
**スロットリングの限界について**

グローバルリミッターが IP 単独での制限のため、異なる IP を使い回す分散型ブルートフォースには対応しきれません。追加の対策として、二要素認証（2FA）の有効化や、Fail2ban などの IP レベルのブロック手段との併用を検討してください。
:::

ログイン失敗の履歴は `LoginHistoryListener` が Symfony 標準の `LoginFailureEvent` を購読して `LoginHistory` エンティティとして記録します（管理画面ファイアウォールのみ対象）。

### 各エンドポイントの保護（eccube_rate_limiter.yaml）

EC-CUBE には独自の `eccube_rate_limiter.yaml` があります。ベース設定（`packages/eccube_rate_limiter.yaml`）には上限 1024回 の初期値が記述されていますが、これは `route: ~`（未割り当て）のため直接は機能しません。実際に本番環境（`packages/prod/eccube_rate_limiter.yaml`）で適用される主な設定は以下の通りです。

| エンドポイント | キー | 上限 | 時間窓 |
|-------------|------|------|-------|
| パスワードリセット（`forgot`） | IP | 5回 | 30分 |
| 会員登録（`entry`） | IP | 25回 | 30分 |
| 問い合わせ完了（`contact`） | IP | 5回 | 30分 |
| 注文確認（`shopping_confirm`） | IP | 25回 | 30分 |
| 注文確認（`shopping_confirm`） | ユーザー | 10回 | 30分 |
| 注文完了（`shopping_checkout`） | IP | 25回 | 30分 |
| 注文完了（`shopping_checkout`） | ユーザー | 10回 | 30分 |

:::message alert
**ステージング環境での注意**

本番用の制限値は `packages/prod/` ディレクトリに分離されているため、ステージング環境でも `APP_ENV=prod` に設定しないと本番と同じレート制限が機能しません。動作確認は `APP_ENV=prod` 環境で行ってください。
:::

:::message
**IPベースのレート制限とプロキシ環境について**

IP アドレスをキーにレート制限をかけている場合、EC-CUBE をロードバランサーや Cloudflare などのリバースプロキシ配下に置くと問題が生じる可能性があります。Symfony の `trusted_proxies` 設定が正しく構成されていないと、すべてのリクエストがプロキシの IP として扱われレート制限が機能しなくなります。また、`X-Forwarded-For` ヘッダーを適切に検証しない構成では、攻撃者がヘッダーを偽装して IP ベースの制限を回避できる恐れがあります。本番環境では `framework.trusted_proxies` と `trusted_headers` を適切に設定してください。
:::

### Symfony 6.4 でのレート制限の追加方法

プラグインから独自のエンドポイントにレート制限を追加したい場合は、`framework.rate_limiter` セクションでリミッターを定義し、コントローラに `RateLimiterFactory` をインジェクトして手動で `consume()` を呼び出す必要があります。

`#[RateLimit]` のような宣言型の書き方は Symfony 6.4 では使えないため、現時点ではこの命令型アプローチが唯一の手段です。

---

## `#[RateLimit]` が EC-CUBE で使えるようになるには

EC-CUBE が Symfony 8.1 に対応するバージョンがリリースされた際に、`#[RateLimit]` を利用できるようになります。

現時点では EC-CUBE 4.3 が `symfony: ^6.4` 依存であるため、プラグイン開発者が独自に `#[RateLimit]` を使うことはできません。Symfony 8.1 対応の EC-CUBE バージョンが出るまでは、従来の命令型アプローチか EC-CUBE 標準の `eccube_rate_limiter.yaml` の設定を活用することになります。

---

## まとめ

| 項目 | EC-CUBE 4.3 での現状 |
|------|-------------------|
| `symfony/rate-limiter` | **標準で含まれている** |
| 管理画面ログイン保護 | `login_throttling`（5回/30分）で実装済み |
| エンドポイント保護 | `eccube_rate_limiter.yaml`（prod）で forgot/entry/contact/shopping 等に設定済み |
| `#[RateLimit]` アトリビュート | **Symfony 8.1 向けのため現時点では利用不可** |
| プラグインでの追加 | `RateLimiterFactory` を手動 DI して `consume()` を呼ぶ |

EC-CUBE 4.3 は `symfony/rate-limiter` を土台として、ログインスロットリングと主要エンドポイントへの保護をすでに実装しています。プラグインで独自にレート制限を追加したい場合は、`framework.rate_limiter` にリミッターを定義し、コントローラで `RateLimiterFactory` を DI するアプローチが最短経路です。

`#[RateLimit]` は EC-CUBE が Symfony 8.1 に対応する将来のバージョンで恩恵を受けられる機能です。今のうちに仕組みを理解しておくことで、バージョンアップ時の対応がスムーズになるでしょう。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
