# Symfony 8.1のEntityExistsをEC-CUBE 4.3で今すぐ使う方法

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

**TL;DR（要約）**

- EC-CUBE プラグインで DTO に外部参照 ID を受け取るとき、ID 存在確認のバリデーションが抜けがちな落とし穴がある
- `EntityType` を使えば自動で存在確認が入るが、DTO + `ValidatorInterface` では自前実装が必要
- `ConstraintValidator` を継承した `EntityExistsValidator` を実装することで、属性1行で存在チェックが書ける
- Symfony 8.1（2026年5月予定）では公式の `EntityExists` 制約が追加されるため、移行コストも最小限
- `repositoryMethod` オプションで「退会済み会員を除外」など複雑な条件にも対応できる

## はじめに

**外部システムから受け取った商品 ID が存在しないまま処理が通ってしまう。**
こうしたバグは本番環境で静かに積み上がります。

**この記事では、そのリスクをゼロにする `EntityExists` カスタム Validator を、コピーして使えるコードとともに解説します。**

EC-CUBE プラグインで DTO や API リクエストのバリデーションを書くとき、`EntityType` を使ったフォームなら選択肢の検証が自動で入りますが、DTO に直接バリデーションを書く場合は自前で実装する必要があります。

**しかも Symfony 8.1 で `EntityExists` 制約が公式に追加予定（PR #63483）です。EC-CUBE 4.3（Symfony ^6.4）ではまだ使えないため、今回は同等機能を先取り実装します。**

この記事でわかること：

1. Symfony 8.1 で追加予定の `EntityExists` 制約の仕様
2. EC-CUBE 4.3 で今すぐ動く `EntityExistsValidator` の完全実装
3. DTO・FormType・カスタムリポジトリメソッドへの適用例

## Symfony 8.1 の EntityExists 制約（予告）

Symfony 8.1（2026年5月リリース予定、PR #63483）で追加される `EntityExists` 制約は、エンティティの存在確認を属性で簡潔に書けるようにします。

```php
use Symfony\Bridge\Doctrine\Validator\Constraints\EntityExists;

class ProductImportDto
{
    #[EntityExists(entityClass: Product::class)]
    public int $productId;
}
```

主なパラメーター：

| パラメーター | 説明 |
|---|---|
| `entityClass` | 検索対象エンティティクラス（必須） |
| `identifierField` | 検索フィールド名（省略時は主キー） |
| `repositoryMethod` | カスタムリポジトリメソッド名 |
| `em` | 使用するエンティティマネージャー名 |
| `message` | カスタムエラーメッセージ |

`null` や空文字列はバリデーションをスキップするため、任意フィールドにも使いやすい設計です。

`identifierField` と `repositoryMethod` は同時指定できません（`\InvalidArgumentException` が発生）。