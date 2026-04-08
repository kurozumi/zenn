## 3. 商品検索のインデックス最適化

### マイグレーションでインデックスを追加

```php
<?php

namespace Plugin\YourPlugin\DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20250215000000 extends AbstractMigration
{
    public function up(Schema $schema): void
    {
        // 商品名検索用の部分一致インデックス（PostgreSQL）
        $this->addSql("
            CREATE INDEX idx_product_name_trgm
            ON dtb_product
            USING gin (name gin_trgm_ops)
        ");

        // 複合インデックス（公開状態 + 作成日）
        $this->addSql("
            CREATE INDEX idx_product_status_date
            ON dtb_product (product_status_id, create_date DESC)
        ");
    }

    public function down(Schema $schema): void
    {
        $this->addSql("DROP INDEX IF EXISTS idx_product_name_trgm");
        $this->addSql("DROP INDEX IF EXISTS idx_product_status_date");
    }
}
```

## 4. Doctrine の Second Level Cache

### 設定

```yaml
# app/config/eccube/packages/doctrine.yaml
doctrine:
    orm:
        second_level_cache:
            enabled: true
            region_cache_driver:
                type: pool
                pool: cache.doctrine.second_level
            regions:
                default:
                    lifetime: 3600
                    cache_driver:
                        type: pool
                        pool: cache.doctrine.second_level
```

### エンティティにキャッシュ設定

プラグインの独自エンティティにキャッシュを設定できます。

```php
<?php

namespace Plugin\YourPlugin\Entity;

use Doctrine\ORM\Mapping as ORM;

#[ORM\Entity]
#[ORM\Table(name: 'plg_your_plugin_config')]
#[ORM\Cache(usage: 'READ_ONLY', region: 'default')]
class Config
{
    // ...
}
```

## 5. HTTP キャッシュの活用

### 商品一覧ページのキャッシュ

```php
<?php

namespace Plugin\YourPlugin\Controller;

use Eccube\Controller\AbstractController;
use Symfony\Component\HttpFoundation\Response;
use Symfony\Component\Routing\Attribute\Route;

class ProductListController extends AbstractController
{
    #[Route(path: '/products/cached', name: 'plugin_product_list_cached')]
    public function index(): Response
    {
        $response = $this->render('@YourPlugin/Product/list.twig', [
            'products' => $this->getProducts(),
        ]);

        // 5分間キャッシュ
        $response->setSharedMaxAge(300);
        $response->headers->addCacheControlDirective('must-revalidate');

        return $response;
    }
}
```

### ETag によるキャッシュ制御

```php
public function detail(Product $product): Response
{
    $response = new Response();
    $etag = md5($product->getUpdateDate()->format('U'));
    $response->setEtag($etag);

    if ($response->isNotModified($this->request)) {
        return $response; // 304 Not Modified
    }

    return $this->render('@YourPlugin/Product/detail.twig', [
        'Product' => $product,
    ], $response);
}
```

## 6. 遅延読み込みの活用

### Twig で必要な時だけ読み込む

```twig
{# 商品画像は表示領域に入った時に読み込む #}
<img
    src="{{ asset('img/placeholder.png') }}"
    data-src="{{ asset(Product.MainListImage|no_image_product, 'save_image') }}"
    loading="lazy"
    class="lazy-load"
>
```

### JavaScript での実装

```javascript
document.addEventListener('DOMContentLoaded', () => {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                observer.unobserve(img);
            }
        });
    });

    document.querySelectorAll('.lazy-load').forEach(img => {
        observer.observe(img);
    });
});
```

## 7. クエリ結果のキャッシュ

### Symfony Cache を使用

```php
<?php

namespace Plugin\YourPlugin\Service;

use Eccube\Repository\CategoryRepository;
use Symfony\Contracts\Cache\CacheInterface;
use Symfony\Contracts\Cache\ItemInterface;

class CachedCategoryService
{
    public function __construct(
        private CategoryRepository $categoryRepository,
        private CacheInterface $cache
    ) {
    }

    public function getCategoryTree(): array
    {
        return $this->cache->get('category_tree', function (ItemInterface $item) {
            $item->expiresAfter(3600); // 1時間キャッシュ

            return $this->categoryRepository->getList();
        });
    }

    public function clearCache(): void
    {
        $this->cache->delete('category_tree');
    }
}
```

### イベントでキャッシュクリア

```php
<?php

namespace Plugin\YourPlugin\EventSubscriber;

use Eccube\Event\EccubeEvents;
use Plugin\YourPlugin\Service\CachedCategoryService;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class CacheClearSubscriber implements EventSubscriberInterface
{
    public function __construct(
        private CachedCategoryService $categoryService
    ) {
    }

    public static function getSubscribedEvents(): array
    {
        return [
            EccubeEvents::ADMIN_PRODUCT_CATEGORY_INDEX_COMPLETE => 'onCategoryUpdate',
        ];
    }

    public function onCategoryUpdate(): void
    {
        $this->categoryService->clearCache();
    }
}
```

## 8. バッチ処理の最適化

### 大量データの一括処理

```php
<?php

namespace Plugin\YourPlugin\Command;

use Doctrine\ORM\EntityManagerInterface;
use Eccube\Repository\ProductRepository;
use Symfony\Component\Console\Attribute\AsCommand;
use Symfony\Component\Console\Command\Command;
use Symfony\Component\Console\Input\InputInterface;
use Symfony\Component\Console\Output\OutputInterface;

#[AsCommand(name: 'plugin:update-products')]
class UpdateProductsCommand extends Command
{
    public function __construct(
        private ProductRepository $productRepository,
        private EntityManagerInterface $entityManager
    ) {
        parent::__construct();
    }

    protected function execute(InputInterface $input, OutputInterface $output): int
    {
        $batchSize = 100;
        $i = 0;

        $query = $this->productRepository->createQueryBuilder('p')
            ->getQuery();

        foreach ($query->toIterable() as $product) {
            // 商品を更新
            $product->setUpdateDate(new \DateTime());

            $i++;
            if ($i % $batchSize === 0) {
                $this->entityManager->flush();
                $this->entityManager->clear(); // メモリ解放
                $output->writeln("Processed $i products...");
            }
        }

        $this->entityManager->flush();
        $output->writeln("Completed! Total: $i products");

        return Command::SUCCESS;
    }
}
```

## 9. 画像の最適化

### WebP 変換プラグイン

```php
<?php

namespace Plugin\YourPlugin\EventSubscriber;

use Eccube\Event\EccubeEvents;
use Eccube\Event\EventArgs;
use Symfony\Component\EventDispatcher\EventSubscriberInterface;

class ImageOptimizeSubscriber implements EventSubscriberInterface
{
    public static function getSubscribedEvents(): array
    {
        return [
            EccubeEvents::ADMIN_PRODUCT_EDIT_COMPLETE => 'onProductEditComplete',
        ];
    }

    public function onProductEditComplete(EventArgs $event): void
    {
        $Product = $event->getArgument('Product');

        foreach ($Product->getProductImages() as $productImage) {
            $this->convertToWebP($productImage->getFileName());
        }
    }

    private function convertToWebP(string $fileName): void
    {
        $savePath = env('ECCUBE_SAVE_IMAGE_DIR');
        $originalPath = $savePath . '/' . $fileName;

        if (!file_exists($originalPath)) {
            return;
        }

        $image = imagecreatefromstring(file_get_contents($originalPath));
        if ($image === false) {
            return;
        }

        $webpPath = preg_replace('/\.(jpg|jpeg|png)$/i', '.webp', $originalPath);
        imagewebp($image, $webpPath, 80);
        imagedestroy($image);
    }
}
```

## 10. OPcache の設定

### php.ini の推奨設定

```ini
[opcache]
opcache.enable=1
opcache.memory_consumption=256
opcache.interned_strings_buffer=16
opcache.max_accelerated_files=20000
opcache.validate_timestamps=0  ; 本番環境のみ
opcache.save_comments=1
opcache.fast_shutdown=1
```

### プリロードの設定（PHP 8.x）

```php
<?php
// config/preload.php

require dirname(__DIR__).'/vendor/autoload.php';

// よく使うクラスをプリロード
$classes = [
    \Eccube\Entity\Product::class,
    \Eccube\Entity\ProductClass::class,
    \Eccube\Entity\Category::class,
    \Eccube\Repository\ProductRepository::class,
];

foreach ($classes as $class) {
    class_exists($class);
}
```

```ini
; php.ini
opcache.preload=/path/to/ec-cube/config/preload.php
opcache.preload_user=www-data
```

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