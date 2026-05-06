---
title: "パスワードに記号必須はもう古い — EC-CUBEをNIST最新基準に対応させるプラグイン実装"
emoji: "🔐"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
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

EC-CUBE 4.3 のデフォルトパスワード設定はこうなっています。

```yaml
# app/config/eccube/packages/eccube.yaml
eccube_password_pattern: '/\A(?=.*?[a-z])(?=.*?\d)[!-~]+\z/i'
```

「英字と数字を両方含む」「記号OK」——セキュリティ強化のために設計されたデフォルト設定です。しかし **NIST（米国国立標準技術研究所）の最新ガイドライン SP 800-63B-4 は、この要件を明確に禁止しています。**

複雑なパスワードを強制すると、ユーザーは `Password1!` のような「要件を通過するだけの弱いパスワード」を作ります。攻撃者はこのパターンを熟知しています。

**現代のセキュリティ研究が示す答えは逆です。長さだけを求め、複雑さは禁止する。**

本記事では、EC-CUBE 4.4.0での公式対応（[Issue #6488](https://github.com/EC-CUBE/ec-cube/issues/6488)）を待たずに、今すぐ4.3でNIST準拠を実現するプラグインの完全実装を解説します。

:::details TL;DR — この記事で実装するもの
- `services.yaml` 3行でパスワード最小長を15文字・Unicode対応に変更
- `FormTypeExtension` でブロックリストと HaveIBeenPwned API 連携を追加
- NFKC正規化でUnicodeパスワードの一貫性を確保
- 所要時間: 実装30分、動作確認10分
:::

## NIST SP 800-63B-4 とは

NIST が公開したパスワード認証のガイドライン改訂版です。従来の「複雑なパスワード」思想を転換し、「長くてシンプル」なパスワードを推奨する内容になっています。

主な変更点を整理します。

| 項目 | 旧基準（63B-3） | 新基準（63B-4） |
|------|----------------|----------------|
| 最小文字数 | 8文字以上 | 15文字以上（多要素認証併用時は8文字） |
| 最大文字数 | 規定なし | 64文字以上受け付けることを要求 |
| 文字種の組み合わせ | 大文字・小文字・数字・記号の混在を推奨 | **禁止**（Verifierは複雑さを課してはならない） |
| Unicode | 必須ではない | 全Unicode文字の許可を要求 |
| ブロックリスト | 任意 | **必須**（よく使われるパスワードの拒否） |
| 定期変更の強制 | 一般的 | **禁止**（侵害時のみ変更を求める） |
| ヒント・秘密の質問 | 一般的 | **禁止** |

## EC-CUBE 4.3 の現状

EC-CUBE 4.3 のパスワード設定は `app/config/eccube/packages/eccube.yaml` で定義されています。

```yaml
eccube_password_min_len: 12
eccube_password_max_len: 50
eccube_password_pattern: '/\A(?=.*?[a-z])(?=.*?\d)[!-~]+\z/i'
```

このパターンは「英字と数字の両方を含む印刷可能なASCII文字」を要求しており、NIST新基準と照らし合わせると以下の問題があります。

- **文字種の組み合わせ要件**: 英字＋数字の混在を必須としており、新基準では禁止されている
- **Unicode非対応**: `[!-~]`（ASCII印刷可能文字のみ）のため、Unicode文字が使えない
- **最大文字数**: 50文字は要求を満たすが、より長い設定が望ましい

パスワードに関するフォームは `RepeatedPasswordType`（`src/Eccube/Form/Type/RepeatedPasswordType.php`）が中心的に使われており、会員登録・マイページ変更・パスワードリセットすべてでこのクラスが利用されています。

## 実装方針

プラグインで以下の3点を実装します。

1. **パラメータ上書き**: `services.yaml` で最小長・最大長・パターンを変更
2. **FormTypeExtension**: `RepeatedPasswordType` を拡張してNIST準拠のバリデーションを追加
3. **侵害パスワードチェック**: Symfonyの `NotCompromisedPassword` 制約で漏洩パスワードを拒否

## プラグインの実装

### ディレクトリ構成

```
app/Plugin/NistPassword43/
├── composer.json
├── Resource/
│   └── config/
│       └── services.yaml
└── Form/
    └── Extension/
        └── NistPasswordTypeExtension.php
```

### composer.json

```json
{
    "name": "your-vendor/nist-password43",
    "version": "1.0.0",
    "description": "NIST SP 800-63B-4対応パスワードバリデーションプラグイン",
    "type": "eccube-plugin",
    "require": {
        "ec-cube/plugin-installer": "~0.0.6 || ^2.0",
        "symfony/http-client": "^6.4"
    },
    "extra": {
        "code": "NistPassword43"
    }
}
```

`symfony/http-client` は `NotCompromisedPassword`（HaveIBeenPwned API との通信）に必要です。EC-CUBE 4.3 が依存する Symfony ^6.4 に合わせてバージョンを指定しています。

### Step 1: services.yaml でパラメータを上書き

`Resource/config/services.yaml` に以下を記述します。EC-CUBEのKernelは `app/Plugin/*/Resource/config/services*.yaml` を自動でロードするため、ここに書くだけで既存の設定を上書きできます。

```yaml
parameters:
    # NIST SP 800-63B-4: 最小15文字
    eccube_password_min_len: 15
    # 最大128文字（NISTは64文字以上を要求）
    eccube_password_max_len: 128
    # 文字種の組み合わせ要件を廃止し、Unicode印刷可能文字をすべて許可
    eccube_password_pattern: '/\A[\pL\pM\pN\pP\pS\pZ]+\z/u'
```

`[\pL\pM\pN\pP\pS\pZ]` はPCREのUnicodeカテゴリで「文字・記号・数字・句読点・区切り文字」を意味します。これにより：

- ASCII印刷可能文字（スペースを含む）
- 全角文字・絵文字を含むUnicode文字
- を許可しつつ、NULバイト・制御文字・ゼロ幅スペース（U+200B）などの不可視文字は拒否します。

`\P{C}` でも同様の効果が得られますが、書式文字（Cf）カテゴリに含まれるゼロ幅スペースが通過してしまうため、より明示的なカテゴリ指定を推奨します。

このパラメータ変更により、`RepeatedPasswordType` が内部で生成する `Assert\Length` と `Assert\Regex` の制約が自動的に更新されます。

### Step 2: FormTypeExtension の実装

`Form/Extension/NistPasswordTypeExtension.php` を作成します。

```php
<?php

declare(strict_types=1);

namespace Plugin\NistPassword43\Form\Extension;

use Eccube\Form\Type\RepeatedPasswordType;
use Symfony\Component\Form\AbstractTypeExtension;
use Symfony\Component\Form\FormBuilderInterface;
use Symfony\Component\Form\FormError;
use Symfony\Component\Form\FormEvent;
use Symfony\Component\Form\FormEvents;
use Symfony\Component\Validator\Constraints\NotCompromisedPassword;
use Symfony\Component\Validator\Validator\ValidatorInterface;

class NistPasswordTypeExtension extends AbstractTypeExtension
{
    /**
     * よく使われる弱いパスワードのブロックリスト（最低限のサンプル）。
     * 実運用では外部ファイルから読み込むか、より大きなリストを使用することを推奨。
     */
    private const BLOCK_LIST = [
        'password123456789',
        '123456789012345',
        'qwertyuiopasdfgh',
        'abcdefghijklmnop',
        'passwordpassword',
        '111111111111111',
        'iloveyouiloveyou',
        'letmeinletmein12',
        'welcomewelcome12',
        'monkey123monkey1',
    ];

    public function __construct(
        private readonly ValidatorInterface $validator
    ) {}

    public static function getExtendedTypes(): iterable
    {
        return [RepeatedPasswordType::class];
    }

    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder->addEventListener(FormEvents::POST_SUBMIT, function (FormEvent $event): void {
            $form = $event->getForm();

            if (!$form->has('first')) {
                return;
            }

            $firstField = $form->get('first');
            $password = $firstField->getData();

            if (null === $password || '' === $password) {
                return;
            }

            // NIST SP 800-63B-4 推奨: NFKC正規化でUnicodeの表記ゆれを統一する
            // ext-intl が必要。異なるエンコーディングで入力された同一文字列を同一視する
            if (class_exists(\Normalizer::class)) {
                $normalized = \Normalizer::normalize($password, \Normalizer::NFKC);
                if (false === $normalized) {
                    $firstField->addError(new FormError('使用できない文字が含まれています。'));
                    return;
                }
                $password = $normalized;
            }

            // ブロックリストチェック（Unicode対応の小文字変換）
            if ($this->isBlockListed($password)) {
                $firstField->addError(
                    new FormError('よく使われるパスワードのため使用できません。別のパスワードを設定してください。')
                );
                return;
            }

            // HaveIBeenPwned APIで漏洩パスワードをチェック
            // skipOnError: true でAPIエラー時はチェックをスキップ
            $violations = $this->validator->validate(
                $password,
                [new NotCompromisedPassword(['skipOnError' => true])]
            );

            foreach ($violations as $violation) {
                $firstField->addError(new FormError($violation->getMessage()));
            }
        });
    }

    private function isBlockListed(string $password): bool
    {
        // mb_strtolower でUnicode対応の小文字変換を行う
        return in_array(mb_strtolower($password, 'UTF-8'), self::BLOCK_LIST, true);
    }
}
```

`autoconfigure: true` が設定されているため、`services.yaml` への明示的な登録は不要です。Symfonyが `AbstractTypeExtension` を継承していることを検出し、`form.type_extension` タグを自動付与します。

## NFKC正規化について

NIST SP 800-63B-4 では、Unicodeパスワードに対して **NFKC正規化** を適用することを推奨（SHOULD）しています。

正規化を行わないと、「パスワード」を全角・半角・異なるエンコーディングで入力した場合に同一のパスワードが異なる文字列として扱われ、ログインできない事態が起きる可能性があります。

上記の実装では `\Normalizer::normalize()` を使用しています。これは PHP の `ext-intl` 拡張が必要ですが、`class_exists(\Normalizer::class)` で事前チェックしているため、`ext-intl` がない環境ではNFKC正規化をスキップします。本番環境では `ext-intl` のインストールを推奨します。

## NotCompromisedPassword の仕組み

### Have I Been Pwned とは

[Have I Been Pwned](https://haveibeenpwned.com/)（HIBP）は、世界中で発生したデータ漏洩事件で流出したパスワードを収集したデータベースサービスです。セキュリティ研究者の Troy Hunt が運営しており、数十億件以上の漏洩パスワードが登録されています。

「過去に漏洩したことがあるパスワード」はすでに攻撃者の辞書に載っているため、いくら長くても危険です。NIST SP 800-63B-4 がブロックリストを必須としている背景の一つがこれです。

### Symfony の NotCompromisedPassword

`NotCompromisedPassword` は Symfony 組み込みの制約で、HIBP の API を使って入力されたパスワードが過去の漏洩に含まれているかをリアルタイムで照合します。

プライバシーへの配慮として **k-匿名性モデル** を採用しています。パスワードのSHA-1ハッシュの先頭5文字のみをAPIに送信し、パスワード本文や完全なハッシュ値が外部に漏れない設計になっています。

```
例: パスワード「mysecretpassword15chars」
SHA-1: 8BE3C943B1609FFFBFC51AAD666D0A04ADF83C9D
API送信: 8BE3C（先頭5文字のみ）
```

## 動作確認

プラグインを有効化したあと、会員登録画面で以下を確認します。

**拒否されるべきパスワード:**
- 14文字以下 → 「15文字以上で入力してください」
- ブロックリストにあるもの → 「よく使われるパスワードのため使用できません」
- 漏洩済みパスワード → `NotCompromisedPassword` のエラーメッセージ

**許可されるべきパスワード:**
- 15文字以上の任意の文字列（英数字・記号混在不要）
- 「これはパスワードです！2026」のような自然言語+数字
- Unicode文字を含むパスワード

## 注意点

### 既存会員のパスワードは変更されない

このプラグインは新規登録・パスワード変更時のバリデーションにのみ適用されます。既存会員の保存済みパスワードハッシュには影響しません。既存会員には次回ログイン時にパスワード変更を促す別途の仕組みが必要です。

### 管理者パスワード変更画面は別途対応が必要

`AdminChangePasswordType`（`src/Eccube/Form/Type/Admin/ChangePasswordType.php`）は `RepeatedPasswordType` を使っていないため、このプラグインの TypeExtension（ブロックリストチェック・漏洩チェック）は適用されません。ただし、`services.yaml` で上書きしたパラメータ（最小長・最大長・パターン）は `AdminChangePasswordType` でも `EccubeConfig` 経由で参照されるため、長さとパターンのバリデーションは適用されます。

ブロックリストチェックと漏洩チェックも適用したい場合は、`AdminChangePasswordType` 向けの TypeExtension を別途追加してください。

### ブロックリストの充実

本記事のブロックリストはサンプルです。実運用では [SecLists](https://github.com/danielmiessler/SecLists) の `Passwords/Common-Credentials/` などを参考に、より多くの弱いパスワードを登録することを推奨します。リストが大きい場合は、定数配列ではなくファイル読み込みやキャッシュを活用してください。

### Have I Been Pwned API は外部通信が必要

`NotCompromisedPassword` は HIBP の外部APIにリアルタイムで通信します。そのため以下の点に注意してください。

- **閉域網環境**: インターネットへの外部接続ができない環境では使用できません。オフライン用のローカルブロックリストのみに頼る構成を検討してください
- **API障害時**: `skipOnError: true` を設定しているため、API障害時はチェックをスキップして登録を継続します。`skipOnError: false`（デフォルト）にするとAPI障害時に登録不能になるため、可用性とセキュリティのトレードオフとして運用環境に合わせて選択してください

### パスワードハッシャーの設定

EC-CUBE 4.3 のデフォルトパスワードハッシャーは `auto`（`config/packages/security.yaml` で確認できます）です。`auto` は `ext-sodium` が利用可能な場合は Argon2id を、そうでない場合は bcrypt を自動選択します。

Symfony の `NativePasswordHasher` は bcrypt を使用する場合でも、72バイトを超えるパスワードを `sha512` でハッシュしてから bcrypt にかけます。そのため、素のbcryptが持つ「72バイト切り捨て」の問題は Symfony 経由では発生しません。

環境依存を排除して常に Argon2id を使用したい場合は、明示的に指定できます。

```yaml
security:
    password_hashers:
        Eccube\Entity\Member:
            algorithm: argon2id
            # memory_cost: 65536  # KB単位（デフォルト: 64MB）
            # time_cost: 4        # 反復回数
        Eccube\Entity\Customer:
            algorithm: argon2id
```

Symfony はbcryptで保存された既存ユーザーのパスワードを自動的に検証し、次回ログイン時に Argon2id で再ハッシュします。**既存ユーザーへの影響はありません。**

Argon2id を使うには PHP の `ext-sodium` 拡張（PHP 7.2 以降では標準バンドル）が必要です。本番環境では `memory_cost` と `time_cost` をサーバースペックに合わせてベンチマークし、適切な値に調整することを推奨します。

## まとめ

NIST SP 800-63B-4 対応のプラグインを実装しました。

- **services.yaml** でパスワード最小長（15文字）・パターン（Unicode対応・複雑さ不要）を上書き
- **FormTypeExtension** で `RepeatedPasswordType` にNFKC正規化・ブロックリストチェック・漏洩チェックを追加
- EC-CUBE 4.4.0での公式対応を待ちながら、今すぐNIST準拠を実現できます

「英字+数字を含む8文字以上」から「15文字以上なら何でもOK」へ。一見ゆるくなったように見えますが、これが現代のセキュリティ研究が示す最適解です。複雑さを求めるよりも、長さと漏洩チェックの組み合わせのほうが実際の攻撃に対して有効です。

## あなたのサイトはどう対応しますか？

「15文字必須にしたら離脱率が上がった」「閉域網でHaveIBeenPwnedが使えない環境をどう対処したか」など、実際に対応してみた経験があればぜひコメントで教えてください。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
