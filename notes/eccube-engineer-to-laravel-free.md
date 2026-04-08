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

```yaml
services:
  App\Service\UserService:
    arguments:
      - '@App\Repository\UserRepository'
```

**Laravel（サービスプロバイダー）:**

```php
// app/Providers/AppServiceProvider.php
public function register(): void
{
    // 依存関係がシンプルな場合、Laravelが自動解決するため登録不要
    // 複雑な依存がある場合はクロージャで明示する
    $this->app->bind(\App\Services\UserService::class, function ($app) {
        return new \App\Services\UserService(
            $app->make(\App\Repositories\UserRepository::class)
        );
    });
}

// コントローラーでの使用（Symfonyと同じ）
public function index(UserService $userService)
{
    // 自動的に注入される
}
```

概念は同じです。Symfonyの`services.yaml`に相当するのがLaravelの**サービスプロバイダー**です。依存関係がシンプルなクラスはコンテナが自動解決するため、明示的な登録が不要な場合も多いです。

### ルーティング

**Symfony:**

```yaml
# config/routes.yaml
user_index:
  path: /users
  controller: App\Controller\UserController::index
  methods: [GET]
```

**Laravel:**

```php
// routes/web.php
Route::get('/users', [UserController::class, 'index'])->name('users.index');

// RESTfulなルートを一括生成（Symfonyにはない）
Route::resource('users', UserController::class);
```

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

```blade
{{-- 認証状態チェック --}}
@auth
    ログイン中: {{ auth()->user()->name }}
@endauth

@guest
    <a href="/login">ログイン</a>
@endguest

{{-- 権限チェック --}}
@can('edit', $post)
    <a href="{{ route('posts.edit', $post) }}">編集</a>
@endcan

{{-- バリデーションエラー --}}
@error('email')
    <span class="text-red-500">{{ $message }}</span>
@enderror

{{-- CSRFトークン（フォームに必須） --}}
<form method="POST">
    @csrf
    ...
</form>

{{-- データなしのforeach --}}
@forelse ($users as $user)
    {{ $user->name }}
@empty
    ユーザーがいません
@endforelse
```

### ORM（Doctrine → Eloquent）

これが**一番大きな違い**です。

**Doctrineはデータマッパーパターン**（エンティティとDBを分離、リポジトリ経由で操作）
**EloquentはActive Recordパターン**（モデルが自身のDB操作を担当）

```php
// Doctrine（EC-CUBE）
$user = $userRepository->find(1);
$users = $userRepository->findBy(['status' => 'active']);

// Eloquent（Laravel）
$user = User::find(1);
$users = User::where('status', 'active')->get();
```

Eloquentの方がシンプルです。モデル定義も最小限です。

```php
// app/Models/User.php
class User extends Model
{
    // テーブル名は自動で 'users'（クラス名の複数形）
    protected $fillable = ['name', 'email'];

    // リレーション定義
    public function company()
    {
        return $this->belongsTo(Company::class);
    }

    public function posts()
    {
        return $this->hasMany(Post::class);
    }
}

// 使用例
$user = User::find(1);
echo $user->company->name;      // リレーションをプロパティとして取得
echo $user->posts->count();     // 投稿数
```

### バリデーション

**Symfony（フォームタイプベース）:**

```php
class UserType extends AbstractType
{
    public function buildForm(FormBuilderInterface $builder, array $options): void
    {
        $builder
            ->add('name', TextType::class, [
                'constraints' => [new NotBlank(), new Length(['min' => 3])],
            ])
            ->add('email', EmailType::class, [
                'constraints' => [new NotBlank(), new Email()],
            ]);
    }
}
```

**Laravel（FormRequest）:**

```php
// app/Http/Requests/StoreUserRequest.php
class StoreUserRequest extends FormRequest
{
    // ✅ 認可チェック：falseを返すと403 Forbiddenになる
    // 認証済みユーザーのみ許可する場合は auth()->check() を返す
    public function authorize(): bool
    {
        return auth()->check();
    }

    public function rules(): array
    {
        return [
            'name'  => 'required|string|min:3|max:255',
            'email' => 'required|email|unique:users,email',
        ];
    }

    public function messages(): array
    {
        return [
            'name.required' => '名前は必須です',
        ];
    }
}

// コントローラー（シンプル！）
public function store(StoreUserRequest $request): RedirectResponse
{
    User::create($request->validated());
    return redirect()->route('users.index');
}
```

Laravelのバリデーションはルールを文字列で指定するため、Symfonyより大幅にシンプルです。

### ミドルウェア

**Symfony（イベントリスナーベース）:**

```php
class AuthMiddleware implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [KernelEvents::REQUEST => 'onRequest'];
    }
}
```

**Laravel（Closureベース）:**

```php
// app/Http/Middleware/CheckAuth.php
class CheckAuth
{
    public function handle(Request $request, Closure $next): Response
    {
        if (!auth()->check()) {
            return redirect('login');
        }
        return $next($request);
    }
}

// ルートへの適用
Route::middleware('auth')->group(function () {
    Route::get('/dashboard', [DashboardController::class, 'index']);
});
```

Laravelのミドルウェアは`$next($request)`でリクエストを次へ渡すシンプルな構造で、Symfonyより直感的です。

### コンソールコマンド

**Symfony:**

```php
// Symfony 6.x では #[AsCommand] アトリビュートで宣言（$defaultName は非推奨）
#[AsCommand(name: 'app:create-user')]
class CreateUserCommand extends Command
{
    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $name = $input->getArgument('name');
        $output->writeln('User created!');
        return Command::SUCCESS;
    }
}

// 実行
// php bin/console app:create-user "John"
```

**Laravel:**

```php
protected $signature = 'app:create-user {name}';

public function handle(): void
{
    $name = $this->argument('name');
    $this->info('User created!');
}

// 実行
// php artisan app:create-user "John"
```

`$signature`で引数・オプションをシンプルに定義できます。また`php bin/console`の代わりに`php artisan`を使います。

---

## Laravel固有の概念（新たに覚えること）

### Eloquentのリレーションと N+1問題

Eloquentを使ううえで**最もつまずきやすいのがN+1クエリ問題**です。

```php
// ❌ N+1問題：ループ内で毎回クエリが発生
$users = User::all();
foreach ($users as $user) {
    echo $user->company->name;  // 1件ごとにSQLが走る！
}

// ✅ with()でイーガーロード（推奨）
$users = User::with('company')->get();  // SQLは2回だけ
foreach ($users as $user) {
    echo $user->company->name;
}

// ✅ 条件付きのイーガーロード
$users = User::with(['posts' => function ($query) {
    $query->where('published', true);
}])->get();
```

`with()`を使ったイーガーロードは必ず習慣づけてください。

### マスアサインメント（fillable の設定）

```php
// ❌ 危険：$request->all() はリクエストの全パラメータを渡す
// $fillable に 'role' や 'is_admin' が含まれていると権限昇格攻撃が可能になる
$user = User::create($request->all());

// ✅ モデルにfillableを定義する
class User extends Model
{
    protected $fillable = ['name', 'email', 'password'];
}

// ✅ FormRequestのvalidated()を使う（推奨）
// バリデーション済みのフィールドのみが渡されるため安全
$user = User::create($request->validated());
```

`$fillable`で許可するカラムを明示的に指定します。セキュリティ上重要な設定です。

`$request->all()`は絶対に使わないでください。`$fillable`を設定していても、攻撃者がリクエストに不正なフィールド（例: `role=admin`）を追加した場合、そのフィールドが`$fillable`に含まれていると書き換えられてしまいます。**常に`$request->validated()`または`$request->only([...])`を使う**ことがセキュリティのベストプラクティスです。

### Artisanコマンドによるコード生成

LaravelはArtisanコマンドでファイルを生成できます。Doctrineの`make:entity`よりはるかに多機能です。

```bash
# モデル + マイグレーション + リソースコントローラーを同時生成
php artisan make:model Post -mcr

# FormRequest生成
php artisan make:request StorePostRequest

# イベント/リスナー生成
php artisan make:event PostPublished
php artisan make:listener SendPublishedNotification

# 全マイグレーション実行
php artisan migrate

# マイグレーションを戻す
php artisan migrate:rollback
```

### マイグレーションの書き方

```php
// database/migrations/2024_01_01_000000_create_posts_table.php
public function up(): void
{
    Schema::create('posts', function (Blueprint $table) {
        $table->id();
        $table->foreignId('user_id')->constrained()->cascadeOnDelete(); // ⚠️ 業務要件によってはcascadeOnDeleteは慎重に検討すること
        $table->string('title');
        $table->text('body');
        $table->boolean('published')->default(false);
        $table->timestamps();  // created_at, updated_at を自動追加
    });
}

public function down(): void
{
    Schema::dropIfExists('posts');
}
```

Doctrineより読みやすく、フルエント（メソッドチェーン）で書けます。

### デプロイ時の注意点

Laravelのデプロイ手順はSymfonyと少し異なります。

```bash
git pull origin main
composer install --no-dev --optimize-autoloader

# 設定・ルートをキャッシュ（本番必須）
# Laravel 11以降は optimize コマンドで一括実行できる
php artisan optimize
# 個別に実行する場合: config:cache, route:cache, view:cache

# マイグレーション（--force は本番環境での確認プロンプトをスキップ）
# ⚠️ カラム削除などの破壊的なマイグレーションも警告なく実行されるため注意
php artisan migrate --force

# ストレージのシンボリックリンク（初回のみ）
php artisan storage:link

# キャッシュクリア
php artisan optimize:clear
```

`APP_KEY`は`.env`に必須です。初回セットアップ時に必ず生成してください。

```bash
php artisan key:generate
```

---