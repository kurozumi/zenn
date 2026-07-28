---
title: "権限設定で自分の2段階認証が直せない。EC-CUBE 4.4が動かしたルート"
emoji: "🔐"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony", "security"]
published: false
---

:::message alert
## 🙋‍♂️ EC-CUBE 開発・カスタマイズのお仕事、募集しています！

プラグイン開発・バージョンアップ・機能追加など、EC-CUBE に関することならお気軽にご相談ください。

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**
:::

:::message
この記事は EC-CUBE 4.4 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## 結論: 拒否URLに `/setting` を入れると、そのメンバーは2段階認証を再設定できません

EC-CUBE の管理画面には権限管理があり、メンバーごとに「アクセスを許可しないURL」を設定できます。運用でよくあるのが、一般スタッフに `/setting`（システム設定）を触らせない設定です。

ところがこれをやると、そのメンバーは**自分の2段階認証を再設定できなくなります**。403 で弾かれます。

原因は、2段階認証の再設定画面が `/setting/system/two_factor_auth/edit` に置かれていたことでした。EC-CUBE 4.4 の [PR #6893](https://github.com/EC-CUBE/ec-cube/pull/6893)（`4.4` ブランチに 2026年7月24日マージ済み）で、このルートが `/setting` の外へ移動します。

あわせて、2段階認証が依存するライブラリも [PR #6898](https://github.com/EC-CUBE/ec-cube/pull/6898) で更新されました。この記事ではその2件をまとめて扱います。

**TL;DR**

- 2段階認証の再設定が `/setting/system/two_factor_auth/edit` → **`/two_factor_auth/edit`** に移動（[PR #6893](https://github.com/EC-CUBE/ec-cube/pull/6893)）
- 原因は `AuthorityVoter` の**前方一致**による拒否URL判定
- 「パスワード変更」は `/change_password` にあるため影響を受けず、対比で問題が見えていた
- `robthree/twofactorauth` が放棄済みの 1.8.2 から **3.x** へ（[PR #6898](https://github.com/EC-CUBE/ec-cube/pull/6898)）
- 破壊的変更は「コンストラクタで QR プロバイダが必須化」の1点のみ
- 新規シークレットが 80bit → 160bit に。DB のカラム長には影響なし

## 拒否URLは前方一致で判定される

`AuthorityVoter` の実装を見ると、判定方法がはっきり分かります。

```php
foreach ($AuthorityRoles as $AuthorityRole) {
    // 許可しないURLが含まれていればアクセス拒否
    try {
        // 正規表現でURLチェック
        $denyUrl = str_replace('/', '\/', $AuthorityRole->getDenyUrl());
        if (preg_match("/^(\/{$adminRoute}{$denyUrl})/i", (string) $path)) {
            return VoterInterface::ACCESS_DENIED;
        }
    } catch (\Exception) {
        // 拒否URLの指定に誤りがある場合、エスケープさせてチェック
        $denyUrl = preg_quote((string) $AuthorityRole->getDenyUrl(), '/');
        if (preg_match("/^(\/{$adminRoute}{$denyUrl})/i", (string) $path)) {
            return VoterInterface::ACCESS_DENIED;
        }
    }
}
```

正規表現が `/^(...)/ ` で始まっています。**先頭からのマッチ、つまり前方一致です。**

拒否URL に `/setting` を設定すると、`/admin/setting` で始まるパスがすべて拒否されます。

```
/admin/setting                              → 拒否
/admin/setting/shop                         → 拒否
/admin/setting/system/member                → 拒否
/admin/setting/system/two_factor_auth/edit  → 拒否 ← これが問題
```

システム設定を触らせたくない、という意図は満たされます。ただし**本人向けの操作まで巻き込まれます**。

自分の2段階認証をスマホの機種変更でリセットしたい。そういう場面で 403 が返ります。管理者に頼むしかありません。

:::message
`try` / `catch` の構造にも注目してください。拒否URL はユーザーが管理画面から自由に入力できるので、正規表現として不正な文字列（`[` だけ、など）が入りうる。その場合に `preg_quote()` でエスケープして再判定しています。ユーザー入力を正規表現に埋め込む処理としては、妥当な防御です。
:::

## パスワード変更との対比

Issue [#6406](https://github.com/EC-CUBE/ec-cube/issues/6406) で指摘されていたのは、同じ「本人向け操作」なのに扱いが違う、という点でした。

| 操作 | パス | `/setting` 拒否の影響 |
| --- | --- | --- |
| パスワード変更 | `/change_password` | 受けない |
| 2段階認証の再設定 | `/setting/system/two_factor_auth/edit` | **受ける** |

パスワード変更は `/setting` 配下にないので通ります。2段階認証だけが通りません。**同じ性質の操作なのに、置き場所の違いだけで挙動が分かれていた**わけです。

## 4.4 の修正

`admin_change_password`（`/change_password`）に倣って、ルートパスを `/setting` 名前空間の外へ移しました。

```php
#[Route(path: '/%eccube_admin_route%/two_factor_auth', name: 'admin_two_factor_auth', methods: ['GET', 'POST'])]
// ...
#[Route(path: '/%eccube_admin_route%/two_factor_auth/set', name: 'admin_two_factor_auth_set', methods: ['GET', 'POST'])]
// ...
#[Route(path: '/%eccube_admin_route%/two_factor_auth/edit', name: 'admin_setting_system_two_factor_auth_edit', methods: ['GET', 'POST'])]
```

もともと `admin_two_factor_auth`（`/two_factor_auth`）と `admin_two_factor_auth_set`（`/two_factor_auth/set`）は `/setting` の外にありました。`edit` だけが `/setting/system/` 配下という不揃いな状態だったので、揃えた形です。

**ルート名（`admin_setting_system_two_factor_auth_edit`）は変えていません。** パスだけを移動しています。ルート名はテンプレートやプラグインから `path()` / `url()` で参照されるので、変えると影響範囲が広がるためです。

なお、拒否URL の前方一致という設計そのものの見直しは [#6242](https://github.com/EC-CUBE/ec-cube/issues/6242) で別途議論されています。今回はその局所的な修正という位置づけです。

## カスタマイズしている場合の確認点

**URL を直書きしているテンプレートがあれば直す必要があります。** ルート名は変わっていないので、`path('admin_setting_system_two_factor_auth_edit')` と書いていれば自動で追従します。危ないのは `/setting/system/two_factor_auth/edit` とハードコードしている場合です。

**権限設定の運用も見直せます。** これまで「2段階認証を再設定させるために `/setting` を拒否URLから外す」という妥協をしていたなら、4.4 では不要になります。

**逆に、意図的に禁止していた場合は注意してください。** `/setting` を拒否することで結果的に2段階認証の再設定も封じていた運用があるなら、4.4 では通るようになります。とはいえ本人の2段階認証を本人が直せないほうが不自然なので、影響は小さいはずです。

## ライブラリ更新: robthree/twofactorauth 3.x

もう1つの変更が [PR #6898](https://github.com/EC-CUBE/ec-cube/pull/6898) です。

管理画面の2段階認証で使っている `robthree/twofactorauth` を、**放棄済みの 1.8.2**（最終リリース 2022年3月、PHP `>=5.6`）から **v3.x**（PHP 8.2+）へ移行します。4.4 は Symfony 7.4 / PHP 8.2+ が要件なので、バージョン要件が噛み合います。

### 影響したのは1点だけ

v3 の破壊的変更のうち、EC-CUBE に実際に影響したのは**コンストラクタで QR プロバイダが必須化された点だけ**でした。

```php
use RobThree\Auth\Providers\Qr\QRServerProvider;
use RobThree\Auth\TwoFactorAuth;
// ...
$this->tfa = new TwoFactorAuth(new QRServerProvider());
```

namespace は v1 と同じ `RobThree\Auth` のままです。

**EC-CUBE はライブラリの QR 生成機能を使っていません。** QR コードは Twig + JavaScript（jQuery qrcode）で、otpauth URI を手組みして生成しています。だから `QRServerProvider` を渡しても**構築時に外部通信は発生しません**。第1引数が必須なので形式的に注入しているだけです。

### シークレット長が変わります

`createSecret()` の既定シークレット長が 80bit → 160bit（16文字 → 32文字）に増えます。

DB への影響はありません。`Member::$two_factor_auth_key` は `length: 255` なので余裕があります。**新規に発行される分だけが長くなり**、既存のシークレットはそのまま動きます。

`verifyCode()` / `createSecret()` の公開シグネチャも変わっていないので、これらを呼んでいるプラグインがあってもそのまま動きます。

RobThree の API に直接触れているのはコア内の3ファイル・4種類の呼び出しだけ、と PR に書かれています。影響範囲が明確に切られた移行です。

## まとめ

- 2段階認証の再設定が `/setting` 配下から `/two_factor_auth/edit` へ移動（[PR #6893](https://github.com/EC-CUBE/ec-cube/pull/6893)）
- 原因は `AuthorityVoter` の拒否URL判定が前方一致であること。`/setting` を拒否すると本人向け操作まで巻き込まれていた
- ルート名は変更なし。`path()` で参照していれば影響を受けない。URL 直書きは要修正
- 拒否URL は正規表現として評価され、不正なら `preg_quote()` で再判定するフォールバックがある
- `robthree/twofactorauth` が放棄済み 1.8.2 から 3.x へ（[PR #6898](https://github.com/EC-CUBE/ec-cube/pull/6898)）
- 破壊的変更は QR プロバイダ必須化のみ。EC-CUBE は QR をライブラリで作っていないので実害なし
- 新規シークレットは 160bit に。DB カラム長への影響なし

「前方一致で拒否」という単純な仕組みは、実装としては分かりやすい反面、**URL の階層構造にアクセス制御が引きずられます**。今回のように、機能の性質（本人向けか管理者向けか）と URL の階層が一致していないと破綻します。自分でアクセス制御を設計するときの参考になる事例だと思います。

:::message alert
EC-CUBE 4.4 はこの記事を書いている時点（2026年7月）で未リリースです。`4.4` ブランチにマージ済みの内容をもとに書いていますので、リリース時には細部が変わる可能性があります。
:::

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
