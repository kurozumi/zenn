---
title: "EC-CUBE 4.4にCookie同意バナーが標準搭載。CDN配下でも壊れない設計を読む"
emoji: "🍪"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "gdpr"]
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

## 結論: Cookie同意バナーがコアに入りました。ただし既定はOFFです

EC-CUBE 4.4 に、Cookie 利用のオプトイン同意を取得する機能が **本体（`src/Eccube`）** として追加されました（[PR #6844](https://github.com/EC-CUBE/ec-cube/pull/6844)、`4.4` ブランチに 2026年7月13日マージ済み、+2,651行・29ファイル）。

同意バナー、クッキー設定ページ、クッキーポリシーページ、そして Google Analytics との連動まで一式です。これまでプラグインや外部 CMP を入れて対応していた部分が、本体でまかなえるようになります。

ただし、この実装で一番おもしろいのは機能そのものより設計判断のほうです。EC サイトはフルページキャッシュや CDN の配下に置かれることが多く、「同意したかどうかで HTML を出し分ける」という素直な実装をやると、**他人の同意状態がキャッシュされて配られる**という最悪の事故が起きます。#6844 の実装は、そこを真正面から避けています。

**TL;DR**

- Cookie 同意バナー・設定ページ・ポリシーページが本体に入る（[PR #6844](https://github.com/EC-CUBE/ec-cube/pull/6844)）
- 同意状態の真実は Cookie に一元化。**DB テーブルは追加なし**。サーバは Cookie の読み書きと操作ログのみ
- バナーの HTML は常にレンダリングし、表示/非表示は JS が Cookie を読んで判定（キャッシュ／CDN 安全）
- 管理画面「店舗基本情報」の `option_cookie_consent` で ON/OFF。**既定は OFF**（＝従来どおりの挙動）
- GA ブロックが同意連動化。ON かつ同意済みのときだけ gtag をロード（判定はクライアント側）
- 拡張ポイント: Twig の `is_cookie_consent_accepted()`、JS の `window.ECCUBE.cookieConsent.getStatus()`、DOM イベント `eccube:cookie-consent:changed`
- 操作記録は Monolog 専用チャンネル `cookie_consent` に 365 日分ローテーション保存

## キャッシュ安全のために「サーバで出し分けない」

まず設計の中心にあるのがこれです。バナーのテンプレートを見てください。

```twig
{#
クッキー同意バナー。

キャッシュ／CDN 安全性のため、HTML は常にレンダリングし、表示/非表示は JS が同意 Cookie を読んで制御する
（cookie_consent.js）。初期状態は非表示とし、同意状態が未設定のときだけ JS が表示する。
#}
<div class="ec-cookieConsentBanner" id="cookie-consent-banner" style="display: none;">
```

`{% if not is_cookie_consent_given() %}` でくくって出し分ける、という書き方を**あえてしていません**。HTML は誰に対しても同じものを返し、`style="display: none;"` の初期状態から JS が Cookie を読んで表示を決めます。

なぜかというと、サーバ側で出し分けた瞬間にバナーあり HTML とバナーなし HTML の2種類が生まれ、フルページキャッシュがどちらか一方を全員に配ってしまうからです。同意済みの人にバナーが出続ける（うっとうしいだけ）ならまだしも、**未同意の人にバナーが出ない**（＝同意を取らずに GA が動く）方向に転ぶと、同意取得の仕組みとして機能しません。

Twig 拡張の DocBlock にも、この制約がはっきり書かれています。

```php
/**
 * クッキー同意機能のTwig拡張。
 *
 * 設定ページ等のキャッシュ対象外ページや、利用側が任意に同意状態を参照する用途で利用する。
 * フルページキャッシュ／CDN 配下のページでは、利用者ごとの同意状態に依存する出し分けに使わないこと。
 */
class CookieConsentExtension extends AbstractExtension
```

Twig 関数は用意されているけれど、キャッシュ対象ページで使うなという注意書き付き。便利な関数を生やしたうえで、使いどころを間違えると壊れることまで実装者自身が書き残している。拡張する側としてはありがたい話です。

なお、このバナーは `default_frame.twig` 側で `{% if BaseInfo.optionCookieConsent %}` によって include されます。「常にレンダリング」というのは、機能を ON にしている限り**同意状態によらず常に**という意味です。

## Cookie の中身と属性

`CookieConsentService` が Cookie の読み書きを一手に引き受けます。

```php
class CookieConsentService
{
    public const COOKIE_NAME = 'eccube_cookie_consent';

    public const STATUS_ACCEPTED = 'accepted';
    public const STATUS_REJECTED = 'rejected';

    public const SOURCE_POPUP = 'popup';
    public const SOURCE_SETTINGS_PAGE = 'settings_page';

    private const COOKIE_LIFETIME_DAYS = 365;
```

保存処理は次のとおりです。

```php
public function saveConsentStatus(Response $response, string $status, Request $request): void
{
    $expireTime = time() + (self::COOKIE_LIFETIME_DAYS * self::SECONDS_PER_DAY);

    $cookie = Cookie::create(
        self::COOKIE_NAME,
        $status,
        $expireTime,
        '/',
        null,
        $request->isSecure(), // HTTPS 環境でのみ Secure=true
        false, // HttpOnly=false（JavaScript から参照するため）
        false,
        Cookie::SAMESITE_LAX
    );

    $response->headers->setCookie($cookie);
}
```

`HttpOnly=false` にしている点に「おや」と思うかもしれませんが、これは意図的です。バナーの表示判定と GA ローダーのゲートをクライアント側で行う設計なので、JS から読めないと成立しません。

成立している理由は、この Cookie が認証情報ではないからです。中身は `accepted` か `rejected` の2値だけで、改ざんされても同意バナーが出るか出ないかが変わるだけ。セッション ID のような機密を `HttpOnly=false` にするのとは、リスクの質がまったく違います。

:::message alert
**この設計をそのまま真似しないでください。**

`HttpOnly=false` が許容されるのは、この Cookie が「accepted / rejected の2値だけを持ち、改ざんされても表示制御しか変わらない値」だからです。セッション ID・認証トークン・会員 ID など、漏洩や改ざんが被害に直結する値は必ず `HttpOnly=true` にしてください。
:::

Secure 属性が `$request->isSecure()` に統一されているのも実務的なポイントです。固定で `true` にすると HTTP のローカル開発環境で Cookie が保存されず、固定で `false` にすると本番で Secure が付かない。リクエストから引くのが素直です。

ただし前提が1つあります。CDN やロードバランサで TLS を終端している構成では、Symfony の trusted proxies 設定（`framework.trusted_proxies` / `TRUSTED_PROXIES` 環境変数）が正しく効いていないと、`$request->isSecure()` は `false` を返します。本番が HTTPS なのに Secure 属性の付かない Cookie が発行されていないか、CDN 配下に置く構成では実際のレスポンスヘッダで確認してください。

## 不正な Cookie 値は allowlist で潰す

Cookie はユーザーが自由に書き換えられます。`getConsentStatus()` はそれを前提にした実装になっています。

```php
public function getConsentStatus(Request $request): ?string
{
    $status = $request->cookies->get(self::COOKIE_NAME);

    // 外部から注入された不正な Cookie 値を画面・判定へ素通しさせない。
    // 許可値（accepted/rejected）以外はすべて未設定（null）に正規化する（JS 側 getStatus() と挙動を揃える）。
    return \in_array($status, [self::STATUS_ACCEPTED, self::STATUS_REJECTED], true) ? $status : null;
}
```

`in_array()` の第3引数 `true`（厳密比較）が入っているところまで含めて、allowlist 方式の教科書どおりです。この値はログにも記録されるので、任意文字列を素通しするとログインジェクションの入口になります。

## 更新 API のバリデーション実装

同意状態の更新は `POST /cookie-consent/update` という Ajax API 1本です。ここのバリデーション実装が、Symfony を書く人にとっては地味に勉強になります。

```php
#[Route(path: '/cookie-consent/update', name: 'cookie_consent_update', methods: ['POST'])]
public function update(Request $request): JsonResponse
{
    // 機能 OFF のときは API も無効（index() がトップへリダイレクトするのと挙動を揃える）
    if (!$this->baseInfoRepository->get()->isOptionCookieConsent()) {
        throw $this->createNotFoundException();
    }

    // CSRFトークン検証（失敗時は isTokenValid() が AccessDeniedHttpException を投げ 403 を返す）
    $this->isTokenValid();

    // パラメータ取得
    // InputBag::get()/getString() は配列など非スカラー入力で BadRequestException を投げ、
    // 下の allowlist 検証（クリーンな 400 JSON）へ到達できない。all() で生値を受け取り、
    // 想定外の型・値は後続の検証／正規化で弾く。
    $params = $request->request->all();
    $consentStatus = $params['consent_status'] ?? null;
```

注目すべきはコメントで説明されている `$request->request->all()` の理由です。Symfony の `InputBag::get()` は、配列など非スカラー（かつ `Stringable` でない）入力を受け取ると `BadRequestException` を投げます。これ自体は安全側の挙動なのですが、`consent_status[]=foo` のような入力を投げられると Symfony 側の汎用 400 エラーが返り、自前のクリーンな 400 JSON に到達しません。Ajax API としては行儀が悪い。

そこで `all()` で生の配列を受け取り、`in_array($consentStatus, [...], true)` の allowlist で弾く形にしています。非スカラー値は `in_array` の厳密比較で自然に `false` になるので、型チェックを別途書く必要もありません。

`source` と `previous_status` も同じ allowlist 方式で正規化されます。

```php
// source / previous_status を許可値へ正規化（getConsentStatus() と同じ allowlist 方式）。
// 任意文字列や非スカラーがログ context へ素通しされるのを防ぐ。
$source = in_array($source, [CookieConsentService::SOURCE_POPUP, CookieConsentService::SOURCE_SETTINGS_PAGE], true)
    ? $source
    : CookieConsentService::SOURCE_POPUP;
```

ログに書く値まで allowlist で正規化しておくのは、自前 API を書くときにも真似したい作法です。

そしてもう1つ、機能 OFF のときに `createNotFoundException()` で 404 を返している点。画面（`index()`）はトップへリダイレクトするのに API は 404、と挙動が違いますが、こちらのほうが素直です。機能を切っている店舗で API だけが応答すると、無効なはずの機能に副作用のある経路が残ります。攻撃面を減らす意味でも、OFF なら経路ごと閉じるのが正解です。

## Google Analytics との連動

コア標準の GA ブロックが同意連動化されました。機能 OFF のときは従来どおり無条件ロード（後方互換）、ON のときはローダー関数を定義するだけで即時発火しません。

```twig
{% if BaseInfo.ga_id is not empty %}
    {% if not BaseInfo.optionCookieConsent %}
        {# クッキーポリシー同意機能が OFF のときは従来どおり無条件で読み込む（後方互換） #}
        <script async src="https://www.googletagmanager.com/gtag/js?id={{ BaseInfo.ga_id }}"></script>
        ...
    {% else %}
        <script>
            window.ECCUBE.cookieConsent.loadGoogleAnalytics = function() {
                if (typeof window.gtag !== 'undefined') {
                    return;  // 二重ロード防止
                }
                var trackingId = '{{ BaseInfo.ga_id }}';
                if (!trackingId) {
                    return;
                }

                var script = document.createElement('script');
                script.async = true;
                script.src = 'https://www.googletagmanager.com/gtag/js?id=' + trackingId;
                document.head.appendChild(script);
                ...
            };
```

:::message alert
このパターンを自分のタグに流用するときは、`<script>` ブロック内への Twig 値の埋め込み方に注意してください。Twig のデフォルト autoescape 戦略は `html` で、JS コンテキストには合いません。値によっては文字列を抜け出せてしまいます。

```twig
{# JS コンテキストなので json_encode で埋める #}
var trackingId = {{ MyValue|json_encode|raw }};
```

`|json_encode` か `|escape('js')` を明示してください。`ga_id` のように管理画面で店舗運営者しか設定できない値であればリスクは限定的ですが、作法としては明示しておくのが安全です。
:::

そして発火のゲートがこちら。

```javascript
(function() {
    // 初回チェック: 既に同意済みなら即ロード（再訪ユーザー向け）。
    function currentStatus() {
        if (window.ECCUBE.cookieConsent && window.ECCUBE.cookieConsent.getStatus) {
            return window.ECCUBE.cookieConsent.getStatus();
        }
        var matches = document.cookie.match(/(?:^|; )eccube_cookie_consent=([^;]*)/);
        return matches ? decodeURIComponent(matches[1]) : null;
    }

    if (currentStatus() === 'accepted') {
        window.ECCUBE.cookieConsent.loadGoogleAnalytics();
    }

    // 変化時: その場で同意したらリロードなしでロード（新規ユーザー向け）。
    document.addEventListener('eccube:cookie-consent:changed', function(e) {
        if (e.detail && e.detail.status === 'accepted') {
            window.ECCUBE.cookieConsent.loadGoogleAnalytics();
        }
    });
})();
```

初回チェックとイベント購読の二段構えです。再訪ユーザーは Cookie を読んで即ロード、新規ユーザーはバナーで同意した瞬間に、リロードなしでロードされます。

`getStatus()` が未定義のときは `document.cookie` の直読みにフォールバックしているのは、`cookie_consent.js` と GA ブロックの読み込み順に依存しないためです。テンプレートのカスタマイズでブロックの並びを変えられる EC-CUBE では、この手の防御は必要になります。

## 拡張ポイント: 他のタグをどう連動させるか

自分のサイトで GA 以外のタグ（Meta Pixel、広告タグ、ヒートマップなど）も同意連動させたい場合、この機能はちゃんと拡張点を公開しています。

**サーバ側（Twig）**

```twig
{% if is_cookie_consent_accepted() %}
    ...
{% endif %}
```

用意されている関数は3つです。

| Twig 関数 | 戻り値 |
| --- | --- |
| `is_cookie_consent_given()` | 同意/拒否のいずれかが選択済みなら `true` |
| `is_cookie_consent_accepted()` | 同意済みなら `true` |
| `get_cookie_consent_status()` | `'accepted'` / `'rejected'` / `null` |

繰り返しますが、**キャッシュ対象ページでの出し分けには使わないでください**。設定ページなど、キャッシュしないページ向けです。

**クライアント側（JS）**

```javascript
// 現在の状態を取る
var status = window.ECCUBE.cookieConsent.getStatus();
if (status === 'accepted') {
    loadYourTag();
}

// 状態が変わったら反応する
document.addEventListener('eccube:cookie-consent:changed', function(e) {
    if (e.detail.status === 'accepted') {
        loadYourTag();
    }
});
```

キャッシュ配下のページで使えるのはこちらです。コア標準の GA ローダー自身がこの公開フックを購読しているので、コアがやっているのとまったく同じやり方でタグを追加できます。コアを改変せずに拡張できる設計になっているのは、素直にありがたいところです。

## 操作記録は DB ではなく Monolog へ

この機能は同意ログを DB に持ちません。Monolog の専用チャンネル `cookie_consent` に出力します。

- `fingers_crossed` を経由しない（＝エラーが起きなくても info が確実に残る）
- `rotating_file` / `level: info` / `max_files: 365`
- prod / dev / e2e 環境で設定（`main` / `console` ハンドラ側では `'!cookie_consent'` で除外）

`fingers_crossed` は「一定レベル以上のログが出たときだけまとめて書き出す」ハンドラなので、これを通すと平常時の info が消えます。同意の証跡を残すのが目的なら通してはいけない、という判断です。prod の monolog 設定を触るときに引っかかりやすいポイントなので、覚えておいて損はありません。

コントローラ側では、ログ出力を**ベストエフォート**として扱っています。

```php
// 操作記録のログ出力（ベストエフォート：失敗してもユーザー体験を損なわない）
$this->cookieConsentLogService->saveLog($logData);
```

ディスクフルなどでログが書けなくても、Cookie の設定と画面動作は続行します。証跡は大事だけれど、それでユーザーが同意できなくなるのは本末転倒、という優先順位です。

## ⚠️ この機能でできないこと

ここが一番大事です。PR の実装コメントには、GDPR 観点での制限事項が正直に明記されています。導入を検討するなら必ず読んでください。

:::message
以下は PR の実装コメントに書かれている制限事項の紹介であり、法令解釈ではありません。自社サイトの対応可否は必ず専門家にご確認ください。
:::

**1. 既定 OFF なので、何もしなければ従来どおり無同意で GA が動く**

```twig
{# 【GDPR/ePrivacy 制限事項】本機能 OFF（既定）時は同意なしで GA を無条件ロードする。
   後方互換のための挙動であり、EU 圏の利用者を対象とする店舗では ePrivacy 指令・GDPR が
   要求する事前同意要件を満たさない。EU 対応が必要な場合は管理画面「店舗基本情報」で本機能を ON にすること。 #}
```

`dtb_base_info.option_cookie_consent` の既定値は `false` です。4.4 に上げただけでは何も変わりません。**明示的に ON にする必要があります。**

**2. 同意の撤回が即時反映されない**

こちらは `<script>` 内の JS 行コメントとして書かれています。

```javascript
// 【GDPR 制限事項】撤回（accepted→rejected）は即時反映されない。ロード済み gtag は
// 現在ページでは停止せず、ブラウザに残存する GA Cookie も削除しない（非ロードになるのは次ページ遷移以降）。
```

一度 gtag をロードした後に設定ページで「拒否」に変えても、**そのページでは GA が動き続け、すでにブラウザに書かれた GA の Cookie も削除されません**。次のページ遷移から反映されます。

厳密な GDPR 準拠を求められる要件では、この2点が問題になるとされています。EU 圏を主要ターゲットにする店舗であれば、本格的な CMP（Consent Management Platform）の導入を検討することになるでしょう。

**3. 同意カテゴリの粒度がない**

「必須 Cookie / 分析 Cookie / 広告 Cookie」のようなカテゴリ別同意ではなく、`accepted` / `rejected` の2値です。カテゴリ分けが必要なら自前で拡張する形になります。

こう書くと厳しく聞こえるかもしれませんが、まず一般的な EC サイトが GA について同意を取れる状態にする、という現実的なラインを、キャッシュ安全に、DB 追加なしで、後方互換を壊さずに実装した。それがこの PR の立ち位置だと理解すると腑に落ちます。制限事項をコード中に自分で書き残しているあたり、むしろ誠実な実装です。

なお国内でも、2023年施行の電気通信事業法における外部送信規律により、GA 等の外部送信について通知・公表等が求められる場面があります。「日本国内だから当面は不要」と読まないでください。詳細は専門家にご確認ください。

## テストの厚み

参考までに、この機能のテストは以下のとおりです。

- PHPUnit（PR 本文記載で 35 tests / 94 assertions。マージ済みコードではデータプロバイダ展開で 37 ケース）。Service / LogService / Twig 拡張 / Controller をカバーし、会員ログイン経路や不正な `consent_status` の 400 応答を含む
- E2E（Playwright）`front-cookie-consent.spec.ts` を matrix に登録。バナーの同意/拒否/閉じる・再表示、設定ページ、ポリシーページ、フッター導線、管理画面 ON/OFF、GA 連動（ON 未同意=未読込／同意でリロードなし読込／拒否=未読込／OFF=無条件）、CSRF トークン不正時の 403

CSRF の異常系が E2E 側、パラメータの異常系が PHPUnit 側、と担当が分かれているのが読み取れます。新機能でここまで E2E が書かれているのは、正直かなり手厚いです。

## まとめ

- EC-CUBE 4.4 に Cookie 同意機能が本体搭載（[PR #6844](https://github.com/EC-CUBE/ec-cube/pull/6844)）。既定は OFF
- 同意状態は Cookie に一元化、DB テーブル追加なし。バナー HTML は常時レンダリングし表示判定は JS → キャッシュ／CDN 安全
- 不正 Cookie 値・API パラメータは allowlist で正規化。ログに書く値まで正規化しているのが良い
- 拡張は Twig の `is_cookie_consent_accepted()` と JS の `eccube:cookie-consent:changed` イベントで。コア GA ローダー自身が同じフックを使っている
- 撤回の即時反映なし・カテゴリ別同意なし・既定 OFF という制限は把握した上で導入すること

キャッシュ配下で同意状態をどう扱うか。これは EC-CUBE に限らず、CDN を挟む Web アプリなら誰もが踏む論点です。その実例として読むだけでも価値のある PR です。

:::message alert
EC-CUBE 4.4 は本記事執筆時点（2026年7月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。また、本記事は法令解釈を提供するものではありません。GDPR・改正個人情報保護法等への対応可否は、必ず専門家にご確認ください。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
