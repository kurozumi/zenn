# EC-CUBEプラグインで「ブロックごとに異なるフォーム」をCollectionTypeで実装する

> この記事は EC-CUBE 4.3 以上を対象としています。
> また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

「テキストブロック・画像ブロック・ボタンブロックをひとつのコレクションで管理したい」——EC-CUBEのコンテンツ管理プラグインや商品オプション実装で、こういった要件に直面したことはありませんか？

現在の Symfony `CollectionType` は**全アイテムに同一の FormType**しか使えません。これを無理やり実装しようとすると、JavaScript や hidden フィールドで型を判定するハック的なコードが生まれます。

Symfony PR [#63487](https://github.com/symfony/symfony/pull/63487) では `entry_types` オプションが追加され、**アイテムごとに異なる FormType を使えるようになります**。

> **この記事のポイント（TL;DR）**
> - 現在の `CollectionType` は `entry_type`（単数）で全アイテムに同一 FormType しか使えない
> - PR #63487（Symfony 8.1向け）で `entry_types`（複数）オプションが追加される
> - `EntryTypeProviderInterface` でデータに応じて型を切り替える
> - EC-CUBE のコンテンツ管理・商品オプション・BtoB 受発注などポリモーフィックなフォームに有用

## 現状の課題：`entry_type` は1種類しか指定できない

EC-CUBE では `CollectionType` を多くの場所で使っています。例えば注文フォームの配送先リスト、商品規格マトリクスなどです。

現在の `CollectionType` には `entry_type` オプションがありますが、**配列内の全アイテムに同一の FormType が適用されます**。

```php
// 現在（Symfony 6.4）：全アイテムが同じ FormType
$builder->add('items', CollectionType::class, [
    'entry_type' => TextType::class, // 全部これ
    'allow_add' => true,
    'allow_delete' => true,
]);
```

「テキスト入力・数値入力・日付入力が混在するコレクション」を実装しようとすると、1つの FormType にすべての入力パターンを詰め込むか、JavaScript でフォームを動的に差し替えるかという苦肉の策になります。

### 現状の回避策（Symfony 6.4）

よくある回避策として「type 判別フィールドを持つ統合 FormType」を使う方法があります。

```php
// ContentBlockType：すべてのブロックタイプを1つに詰め込む
class ContentBlockType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('type', HiddenType::class)
            ->add('text', TextareaType::class, ['required' => false])
            ->add('imageUrl', UrlType::class, ['required' => false])
            ->add('buttonLabel', TextType::class, ['required' => false]);
    }
}

// コレクションに使う
$builder->add('blocks', CollectionType::class, [
    'entry_type' => ContentBlockType::class,
]);
```

不要なフィールドも全部レンダリングされるため、JavaScript でブロックタイプに応じて表示/非表示を切り替える必要があります。コードが複雑になりがちです。

---

## PR #63487 で何が変わるか：`entry_types` オプション

Symfony PR #63487 では `entry_types` オプションが追加されます。キー付き配列で複数の FormType を登録し、`EntryTypeProviderInterface` でデータに応じて型を選択します。

```php
// Symfony 8.1 以降（予定）
use Symfony\Component\Form\EntryTypeProviderInterface;

$builder->add('blocks', CollectionType::class, [
    'entry_types' => [
        'text'   => TextBlockType::class,
        'image'  => ImageBlockType::class,
        'button' => ButtonBlockType::class,
    ],
    'entry_type_provider' => new class implements EntryTypeProviderInterface {
        public function forModelData(mixed $data): int|string
        {
            // エンティティからタイプを判定
            return $data->getType(); // 'text', 'image', 'button'
        }

        public function forSubmittedData(mixed $data): int|string
        {
            // 送信データからタイプを判定
            return $data['type'] ?? 'text';
        }
    },
    'allow_add' => true,
    'allow_delete' => true,
]);
```

### EntryTypeProviderInterface

```php
// PR #63487 で追加されるインターフェース
namespace Symfony\Component\Form;

interface EntryTypeProviderInterface
{
    // 既存エンティティ（モデルデータ）からタイプキーを返す
    public function forModelData(mixed $data): int|string;

    // フォーム送信データからタイプキーを返す
    public function forSubmittedData(mixed $data): int|string;
}
```

2つのメソッドを実装する理由：「既存データの表示」と「新規追加時のフォーム送信データ処理」でデータ構造が異なるためです。

### タイプごとのオプション設定

`entry_type_options` でタイプ別にオプションを設定できます。

```php
$builder->add('blocks', CollectionType::class, [
    'entry_types' => [
        'text'  => TextBlockType::class,
        'image' => ImageBlockType::class,
    ],
    'entry_type_provider' => /** ... **/,
    'entry_type_options' => [
        'text'  => ['attr' => ['maxlength' => 500]],
        'image' => ['attr' => ['accept' => 'image/*']],
    ],
]);
```

### Twig テンプレートでのプロトタイプ

`entry_types` を使うと、各タイプのプロトタイプが `data-prototype-{タイプ名}` 属性として HTML に出力されます。

```html
<div id="page_blocks"
     data-prototype-text="<div>...テキストブロックのプロトタイプ...</div>"
     data-prototype-image="<div>...画像ブロックのプロトタイプ...</div>"
     data-prototype-button="<div>...ボタンブロックのプロトタイプ...</div>"
>
```

JavaScript からタイプに応じた適切なプロトタイプを取得して DOM に追加できます。

```javascript
// 追加ボタンのクリック時
const type = 'text'; // ユーザーが選択したタイプ
const prototype = form.dataset[`prototype${type.charAt(0).toUpperCase() + type.slice(1)}`];
const newItem = prototype.replace(/__name__/g, index);
form.appendChild(createElementFromHTML(newItem));
```

---

## EC-CUBEプラグインでの活用シーン

### コンテンツ管理プラグイン

ページ編集画面でブロックタイプ（テキスト・画像・動画・ボタン）ごとに専用フォームを持つ構成。

```php
// コンテンツブロックのエンティティ
class ContentBlock
{
    private string $type; // 'text', 'image', 'video', 'button'
    // ...
    public function getType(): string { return $this->type; }
}

// ページフォーム
class PageType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder->add('blocks', CollectionType::class, [
            'entry_types' => [
                'text'   => TextBlockType::class,
                'image'  => ImageBlockType::class,
                'button' => ButtonBlockType::class,
            ],
            'entry_type_provider' => new ContentBlockTypeProvider(),
        ]);
    }
}
```

### BtoB受発注プラグイン

注文明細に「通常商品・カスタム品・サービス」など異なる入力フォームが必要なケース。

```php
$builder->add('orderItems', CollectionType::class, [
    'entry_types' => [
        'product' => OrderProductItemType::class,  // 在庫から選択
        'custom'  => OrderCustomItemType::class,   // 品番・仕様を手入力
        'service' => OrderServiceItemType::class,  // サービス内容・工数
    ],
    'entry_type_provider' => new OrderItemTypeProvider(),
]);
```

---

## 現在の EC-CUBE での対応



Symfony 6.4 のうちは、以下のいずれかで対応します。

**選択肢1: 統合 FormType + JavaScript で表示切り替え**
前述の回避策。シンプルな要件には十分。

**選択肢2: サードパーティバンドル**
[InfiniteFormBundle](https://github.com/infinite-networks/InfiniteFormBundle) がポリモーフィックコレクションを実装しています。PR #63487 のREADMEでも言及されています。

---

## まとめ

| | 現在（Symfony 6.4） | PR #63487後（Symfony 8.1〜） |
|---|---|---|
| タイプの指定 | `entry_type`（1種類） | `entry_types`（複数・キー付き配列） |
| タイプの判定 | 手動（JavaScript等） | `EntryTypeProviderInterface` |
| プロトタイプ | `data-prototype`（1つ） | `data-prototype-{name}`（タイプごと） |
| 実装の複雑さ | フォームに全フィールドを詰め込む | タイプごとに独立した FormType |

ポリモーフィックなフォームはEC-CUBEプラグイン開発でよく出てくる要件です。Symfony 8.1以降で`entry_types`が使えるようになるまでの間、InfiniteFormBundleや統合FormTypeで対応しつつ、将来の移行を見据えた設計にしておくと安心です。

あなたのプラグインで「ブロックごとに異なるフォーム」を実装したことがあればコメントで教えてください。どんな工夫をしたか気になります。

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---