## EC-CUBEプラグインでの活用シーン

### コンテンツ管理プラグイン

ページ編集画面でブロックタイプ（テキスト・画像・動画・ボタン）ごとに専用フォームを持つ構成。

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

### BtoB受発注プラグイン

注文明細に「通常商品・カスタム品・サービス」など異なる入力フォームが必要なケース。

$builder->add('orderItems', CollectionType::class, [
    'entry_types' => [
        'product' => OrderProductItemType::class,  // 在庫から選択
        'custom'  => OrderCustomItemType::class,   // 品番・仕様を手入力
        'service' => OrderServiceItemType::class,  // サービス内容・工数
    ],
    'entry_type_provider' => new OrderItemTypeProvider(),
]);

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
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---