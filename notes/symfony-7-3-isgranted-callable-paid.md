## 基本的な使い方

### シンプルな例：投稿者チェック


### IsGrantedContext が提供するもの

コーラブルには `IsGrantedContext` と `$subject` の2つのパラメータが渡されます：

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `$context` | `IsGrantedContext` | 認可コンテキスト |
| `$subject` | `mixed` | アクセス対象のオブジェクト |

`IsGrantedContext` は以下のプロパティとメソッドを提供します：

| プロパティ/メソッド | 説明 |
|-------------------|------|
| `$context->token` | 認証トークン（`TokenInterface`） |
| `$context->user` | 現在のユーザー（未認証時は `null`） |
| `$context->isGranted()` | 他のロール/パーミッションをチェック |
| `$context->isAuthenticated()` | 認証済みかどうか |
| `$context->isAuthenticatedFully()` | 完全認証済みかどうか |

## EC-CUBEでの実用例

### 例1: 商品の編集権限チェック

EC-CUBEで特定のメンバーが作成した商品のみ編集可能にする例です：


### 例2: 注文の閲覧権限（顧客側）

マイページで自分の注文のみ閲覧可能にする例：


### 例3: 複雑な条件分岐

公開状態に応じたアクセス制御：


## subject パラメータの柔軟な指定

`subject` パラメータにもコーラブルを使用できます：


## 従来の方法との比較

### Voter を使う場合（従来）


### コーラブルを使う場合（Symfony 7.3+）


### 比較表

| 観点 | Voter | コーラブル |
|------|-------|----------|
| コード量 | 多い（別ファイル必要） | 少ない（インライン） |
| 再利用性 | 高い | 低い |
| 型安全性 | あり | あり |
| IDE補完 | あり | あり |
| テスト | 単体テスト可能 | コントローラーテストで確認 |

ℹ️ **覚えておきたいルール:**
ℹ️ 複数箇所で使うなら **Voter**、1箇所だけなら **コーラブル**。
ℹ️ 迷ったらVoterを選べば間違いない。

## どっちを使う？30秒判断フローチャート

1. **そのチェック、2箇所以上で使う？**
   - Yes → Voter
   - No → 次へ

2. **ロジックが3行以下？**
   - Yes → コーラブル
   - No → Voter

3. **単体テストが必要？**
   - Yes → Voter
   - No → コーラブル

## あなたはどっち派？

この機能を見て、開発者の間で意見が分かれています：

**コーラブル推進派:**
> 「Voterを作るほどでもない小さなチェックが多い。インラインで書けるのは神機能」

**Voter維持派:**
> 「ロジックが属性に埋まると、テストしにくくなる。保守性を考えるとVoter一択」

あなたはどう思いますか？ぜひコメントで教えてください。

## まとめ

Symfony 7.3の `#[IsGranted]` コーラブル対応は、シンプルなアクセス制御を直感的に記述できる便利な機能です。

- **メリット**: コード量削減、型安全、IDE補完
- **デメリット**: 再利用性が低い、複雑なロジックには不向き
- **EC-CUBEでの活用**: 商品や注文の所有者チェックなど

EC-CUBEがSymfony 7.x系に対応した際には、ぜひ活用してみてください。

## 参考リンク

- [New in Symfony 7.3: Security Improvements](https://symfony.com/blog/new-in-symfony-7-3-security-improvements)
- [Symfony PR #59150: Allow using a callable with IsGranted](https://github.com/symfony/symfony/pull/59150)
- [PHP RFC: Closures in const expressions](https://wiki.php.net/rfc/closures_in_const_expr)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---