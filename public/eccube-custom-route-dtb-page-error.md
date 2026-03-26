---
title: 'EC-CUBE 4でカスタムルートを作成するとエラーになる原因と対処法'
tags:
  - EC-CUBE
  - PHP
  - Symfony
private: false
updated_at: '2026-03-19T15:13:05+09:00'
id: c8107abfe8873753f830
organization_url_name: null
slide: false
ignorePublish: false
---

:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [EC-CUBE 4でカスタムルートを作成するとエラーになる原因と対処法](https://zenn.dev/kurozumi/articles/eccube-custom-route-dtb-page-error)**

---

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

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[EC-CUBE 4でカスタムルートを作成するとエラーになる原因と対処法](https://zenn.dev/kurozumi/articles/eccube-custom-route-dtb-page-error)**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
