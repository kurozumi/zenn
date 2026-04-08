## 3. 商品検索のインデックス最適化

### マイグレーションでインデックスを追加


## 4. Doctrine の Second Level Cache

### 設定


### エンティティにキャッシュ設定

プラグインの独自エンティティにキャッシュを設定できます。


## 5. HTTP キャッシュの活用

### 商品一覧ページのキャッシュ


### ETag によるキャッシュ制御


## 6. 遅延読み込みの活用

### Twig で必要な時だけ読み込む


### JavaScript での実装


## 7. クエリ結果のキャッシュ

### Symfony Cache を使用


### イベントでキャッシュクリア


## 8. バッチ処理の最適化

### 大量データの一括処理


## 9. 画像の最適化

### WebP 変換プラグイン


## 10. OPcache の設定

### php.ini の推奨設定


### プリロードの設定（PHP 8.x）



## まとめ

| テクニック | 効果 | 難易度 |
|-----------|------|--------|
| N+1問題の解決 | 大 | 中 |
| ページネーション最適化 | 大 | 中 |
| インデックス追加 | 大 | 低 |
| Second Level Cache | 中 | 中 |
| HTTP キャッシュ | 大 | 低 |
| 遅延読み込み | 中 | 低 |
| クエリキャッシュ | 中 | 中 |
| バッチ処理最適化 | 大 | 中 |
| 画像最適化 | 中 | 中 |
| OPcache 設定 | 大 | 低 |

パフォーマンス改善は計測が重要です。Blackfire や Xdebug などのプロファイラを使って、ボトルネックを特定してから対策を行いましょう。

## 参考リンク

- [EC-CUBE 4 開発者向けドキュメント](https://doc4.ec-cube.net/)
- [Doctrine ORM Performance](https://www.doctrine-project.org/projects/doctrine-orm/en/current/reference/improving-performance.html)
- [Symfony Performance](https://symfony.com/doc/current/performance.html)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---