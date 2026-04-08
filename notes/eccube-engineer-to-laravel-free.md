# EC-CUBEエンジニアがLaravel案件に参画するために覚えること【2〜3週間で即戦力になる変換表】

ℹ️ この記事はEC-CUBEエンジニア（Symfonyベースの知識あり）を対象としています。
ℹ️ [Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

「Laravel案件に参画してほしい」と言われたとき、あなたはどう感じますか？

実は、**EC-CUBEエンジニアはすでにLaravelの半分を知っています**。EC-CUBEはSymfonyをベースに構築されており、LaravelはSymfonyと設計思想が異なるものの、DI・ルーティング・ORM・バリデーション・ミドルウェアといった核心概念はすべて対応しています。

この記事では、EC-CUBEエンジニアが「何を知っていて」「何を新たに覚える必要があるか」をSymfonyとの対応表で整理します。Symfony知識を活かせば、**2〜3週間で業務レベルのLaravelコードが書けるようになります**。

## Symfony → Laravel 概念マッピング

EC-CUBEエンジニアがすでに知っている概念と、Laravelでの対応を比較します。

### ServiceContainer / DI（依存性注入）

**Symfony（services.yaml）:**


**Laravel（サービスプロバイダー）:**


概念は同じです。Symfonyの`services.yaml`に相当するのがLaravelの**サービスプロバイダー**です。依存関係がシンプルなクラスはコンテナが自動解決するため、明示的な登録が不要な場合も多いです。

### ルーティング

**Symfony:**


**Laravel:**


Laravelではルートを`routes/web.php`にPHPで直接記述します。`Route::resource()` を使うとCRUDに必要な7つのルートが自動生成されます。

### テンプレートエンジン（Twig → Blade）

| 概念 | Twig（EC-CUBE） | Blade（Laravel） |
|---|---|---|
| 変数出力 | `{{ var }}` | `{{ $var }}` |
| コメント | `{# comment #}` | `{{-- comment --}}` |
| 継承 | `{% extends %}` | `@extends()` |
| ブロック定義 | `{% block name %}...{% endblock %}` | `@section('name')...@endsection` |
| ループ | `{% for item in items %}` | `@foreach ($items as $item)` |
| 条件 | `{% if %}` | `@if` |
| インクルード | `{% include %}` | `@include()` |

構文は違いますが概念はほぼ同じです。**変数に`$`が必要**なことと、**`@`ディレクティブ**を使う点が主な違いです。

Bladeには以下のような便利なディレクティブがあります。


### ORM（Doctrine → Eloquent）

これが**一番大きな違い**です。

**Doctrineはデータマッパーパターン**（エンティティとDBを分離、リポジトリ経由で操作）
**EloquentはActive Recordパターン**（モデルが自身のDB操作を担当）


Eloquentの方がシンプルです。モデル定義も最小限です。


### バリデーション

**Symfony（フォームタイプベース）:**


**Laravel（FormRequest）:**


Laravelのバリデーションはルールを文字列で指定するため、Symfonyより大幅にシンプルです。

### ミドルウェア

**Symfony（イベントリスナーベース）:**


**Laravel（Closureベース）:**


Laravelのミドルウェアは`$next($request)`でリクエストを次へ渡すシンプルな構造で、Symfonyより直感的です。

### コンソールコマンド

**Symfony:**


**Laravel:**


`$signature`で引数・オプションをシンプルに定義できます。また`php bin/console`の代わりに`php artisan`を使います。

---

## Laravel固有の概念（新たに覚えること）

### Eloquentのリレーションと N+1問題

Eloquentを使ううえで**最もつまずきやすいのがN+1クエリ問題**です。


`with()`を使ったイーガーロードは必ず習慣づけてください。

### マスアサインメント（fillable の設定）


`$fillable`で許可するカラムを明示的に指定します。セキュリティ上重要な設定です。

`$request->all()`は絶対に使わないでください。`$fillable`を設定していても、攻撃者がリクエストに不正なフィールド（例: `role=admin`）を追加した場合、そのフィールドが`$fillable`に含まれていると書き換えられてしまいます。**常に`$request->validated()`または`$request->only([...])`を使う**ことがセキュリティのベストプラクティスです。

### Artisanコマンドによるコード生成

LaravelはArtisanコマンドでファイルを生成できます。Doctrineの`make:entity`よりはるかに多機能です。


### マイグレーションの書き方


Doctrineより読みやすく、フルエント（メソッドチェーン）で書けます。

### デプロイ時の注意点

Laravelのデプロイ手順はSymfonyと少し異なります。


`APP_KEY`は`.env`に必須です。初回セットアップ時に必ず生成してください。


---