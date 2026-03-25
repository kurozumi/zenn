---
title: "EC-CUBE 4でカスタムルートを作成するとエラーになる原因と対処法"
emoji: "🛣️"
type: "tech"
topics: ["eccube", "eccube4", "php", "symfony"]
published: true
---

:::message
この記事は EC-CUBE 4.3 以上を対象としています。
また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。
:::

## はじめに

EC-CUBE 4でプラグインやCustomizeディレクトリにカスタムコントローラーを作成し、独自のルートを定義した際に、開発環境（`APP_ENV=dev`）で以下のようなエラーが発生することがあります。

```
An exception has been thrown during the rendering of a template
("Parameter "route" for route "user_data" must match
"(?:[0-9a-zA-Z_\-]+\/?)+(?<!\/)" ("" given) to generate a corresponding URL.").
```

本記事では、このエラーの原因と対処法について解説します。

## エラーの再現手順

例として、`TopController`をカスタマイズして新しいルートを作成してみます。

```php
// app/Customize/Controller/HomeController.php

namespace Customize\Controller;

use Eccube\Controller\AbstractController;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Template;
use Symfony\Component\Routing\Annotation\Route;

class HomeController extends AbstractController
{
    /**
     * @Route("/home", name="homepage2", methods={"GET"})
     * @Template("index.twig")
     */
    public function index()
    {
        return [];
    }
}
```

このコントローラーを作成して `/home` にアクセスすると、エラーが発生します。

## エラーの原因

### EC-CUBEのページ管理の仕組み

EC-CUBEでは、フロント画面のすべてのページが `dtb_page` テーブルで管理されています。このテーブルには以下の情報が格納されています。

- ページ名
- URL（ルート名）
- ファイル名
- レイアウト情報
- メタ情報（description等）

### TwigInitializeListenerの処理

フロント画面にアクセスすると、`TwigInitializeListener` がリクエストを処理し、ルート名から対応する `Page` エンティティを取得します。

```php
// src/Eccube/EventListener/TwigInitializeListener.php

public function setFrontVariables(RequestEvent $event)
{
    $request = $event->getRequest();
    $route = $attributes->get('_route');

    // URLからPageを取得
    $Page = $this->pageRepository->getPageByRoute($route);

    // Twigグローバル変数に設定
    $this->twig->addGlobal('Page', $Page);
    // ...
}
```

### PageRepositoryの挙動

`PageRepository::getPageByRoute()` は、指定されたルート名で `dtb_page` を検索します。

```php
// src/Eccube/Repository/PageRepository.php

public function getPageByRoute($route)
{
    try {
        $Page = $qb
            ->where('p.url = :url')
            ->setParameter('url', $route)
            ->getSingleResult();
    } catch (\Exception $e) {
        // 見つからない場合は空のPageを返す
        return $this->newPage();
    }

    return $Page;
}

public function newPage()
{
    $Page = new Page();
    $Page->setEditType(Page::EDIT_TYPE_USER);  // edit_type = 0

    return $Page;
}
```

**ポイント**: `dtb_page` にルートが登録されていない場合、`url` プロパティが空の `Page` エンティティが返されます。

### meta.twigでのエラー発生

テンプレートの `meta.twig` では、canonical URLを生成する際に `Page.url` を使用しています。

```twig
{# src/Eccube/Resource/template/default/meta.twig #}

{% elseif Page is defined and Page.edit_type == 0 and Page.url is defined and Page.url is not empty %}
    {% set meta_canonical = url('user_data', {'route': Page.url}) %}
{% endif %}
```

`dtb_page` に登録されていないカスタムルートでは、`Page.url` が空になるため、`url('user_data', {'route': ''})` が呼ばれてしまい、`user_data` ルートの要件（`route` パラメータが必須）を満たせずエラーが発生します。

## 対処法

### 方法1: dtb_pageにページを登録する（推奨）

最も正しい方法は、カスタムルートを `dtb_page` に登録することです。

```php
// app/Customize/Controller/HomeController.php

namespace Customize\Controller;

use Eccube\Controller\AbstractController;
use Eccube\Annotation\EntityExtension;
use Sensio\Bundle\FrameworkExtraBundle\Configuration\Template;
use Symfony\Component\Routing\Annotation\Route;

class HomeController extends AbstractController
{
    /**
     * @Route("/home", name="homepage2", methods={"GET"})
     * @Template("home.twig")
     */
    public function index()
    {
        return [];
    }
}
```

マイグレーションファイルを作成して、`dtb_page` にレコードを追加します。

```php
// app/DoctrineMigrations/Version20240101000000.php

namespace DoctrineMigrations;

use Doctrine\DBAL\Schema\Schema;
use Doctrine\Migrations\AbstractMigration;

final class Version20240101000000 extends AbstractMigration
{
    public function up(Schema $schema): void
    {
        // dtb_pageにページを登録
        $this->addSql("INSERT INTO dtb_page (
            master_page_id, page_name, url, file_name, edit_type,
            create_date, update_date, meta_robots, discriminator_type
        ) VALUES (
            NULL, 'ホーム', 'homepage2', 'home', 2,
            NOW(), NOW(), 'noindex', 'page'
        )");

        // dtb_page_layoutにレイアウトを紐付け
        $pageId = $this->connection->lastInsertId();
        $this->addSql("INSERT INTO dtb_page_layout (
            page_id, layout_id, device_type_id, sort_no, discriminator_type
        ) VALUES (
            {$pageId}, 1, 10, 0, 'pagelayout'
        )");
    }

    public function down(Schema $schema): void
    {
        $this->addSql("DELETE FROM dtb_page WHERE url = 'homepage2'");
    }
}
```

### 方法2: プラグインの場合はPluginManager で登録

プラグイン開発の場合は、`PluginManager` の `enable` メソッドでページを登録します。

```php
// PluginManager.php

namespace Plugin\MyPlugin;

use Eccube\Entity\Layout;
use Eccube\Entity\Page;
use Eccube\Entity\PageLayout;
use Eccube\Plugin\AbstractPluginManager;
use Eccube\Repository\LayoutRepository;
use Eccube\Repository\PageRepository;
use Eccube\Repository\PageLayoutRepository;
use Symfony\Component\DependencyInjection\ContainerInterface;

class PluginManager extends AbstractPluginManager
{
    public function enable(array $meta, ContainerInterface $container)
    {
        $em = $container->get('doctrine.orm.entity_manager');
        $pageRepository = $container->get(PageRepository::class);
        $layoutRepository = $container->get(LayoutRepository::class);
        $pageLayoutRepository = $container->get(PageLayoutRepository::class);

        // ページの作成
        $Page = $pageRepository->findOneBy(['url' => 'myplugin_index']);
        if (null === $Page) {
            $Page = new Page();
            $Page->setName('マイプラグイン');
            $Page->setUrl('myplugin_index');
            $Page->setFileName('MyPlugin/index');
            $Page->setEditType(Page::EDIT_TYPE_DEFAULT);
            $Page->setMetaRobots('noindex');
            $em->persist($Page);
            $em->flush();

            // レイアウトとの紐付け
            $Layout = $layoutRepository->find(Layout::DEFAULT_LAYOUT_UNDERLAYER_PAGE);
            $PageLayout = new PageLayout();
            $PageLayout->setPage($Page);
            $PageLayout->setLayout($Layout);
            $PageLayout->setDeviceTypeId(\Eccube\Entity\Master\DeviceType::DEVICE_TYPE_PC);
            $PageLayout->setSortNo(0);
            $em->persist($PageLayout);
            $em->flush();
        }
    }

    public function disable(array $meta, ContainerInterface $container)
    {
        $em = $container->get('doctrine.orm.entity_manager');
        $pageRepository = $container->get(PageRepository::class);

        $Page = $pageRepository->findOneBy(['url' => 'myplugin_index']);
        if (null !== $Page) {
            $em->remove($Page);
            $em->flush();
        }
    }
}
```

### 方法3: レイアウトを使用しないページの場合

管理画面のようにレイアウトを使用しないページの場合は、Twigテンプレートで `default_frame.twig` を継承せずに独自のテンプレートを使用します。

```twig
{# app/template/default/Home/index.twig #}

<!DOCTYPE html>
<html>
<head>
    <title>カスタムページ</title>
</head>
<body>
    <h1>カスタムページ</h1>
</body>
</html>
```

```php
// コントローラー側

/**
 * @Route("/home", name="homepage2", methods={"GET"})
 */
public function index()
{
    return $this->render('Home/index.twig');
}
```

この方法では `meta.twig` が読み込まれないため、エラーは発生しません。ただし、EC-CUBEの共通レイアウト（ヘッダー、フッター、ブロック等）が使用できなくなります。

## なぜdtb_pageへの登録が必要なのか

EC-CUBEのフロント画面では、`dtb_page` テーブルが以下の役割を担っています。

| 機能 | 説明 |
|------|------|
| レイアウト管理 | ページごとにヘッダー・フッター・サイドバーのレイアウトを設定 |
| ブロック配置 | ページごとにブロックの表示/非表示を制御 |
| SEO設定 | メタタグ（description, robots等）の管理 |
| canonical URL | 正規URLの生成 |
| ページ名管理 | パンくずリストやタイトルに使用 |

`dtb_page` に登録することで、これらの機能が正しく動作するようになります。

## まとめ

- EC-CUBE 4でカスタムルートを作成する際は、`dtb_page` テーブルへの登録が必要
- 登録しないと `meta.twig` でcanonical URL生成時にエラーが発生する
- プラグイン開発では `PluginManager` でページを登録するのがベストプラクティス
- 管理画面で「ページ管理」からも追加可能だが、プログラムで管理する方が保守性が高い

## 参考リンク

- [GitHub Issue: dtb_pageに登録していないルートを作成し、アクセスするとエラーになる](https://github.com/EC-CUBE/ec-cube/issues/6504)
- [EC-CUBE 4 開発者向けドキュメント - ページ管理](https://doc4.ec-cube.net/)

---

## 📩 EC-CUBE開発・カスタマイズのご相談

以下のような案件、お気軽にご相談ください。

- プラグイン開発・既存プラグインの改修
- EC-CUBE 4系へのバージョンアップ対応
- カスタマイズ・機能追加
- エンタープライズ向け開発・導入支援

👉 **[お問い合わせはこちら](https://a-zumi.net/contact/)**

---
