# EC-CUBE 4でカスタムルートを作成するとエラーになる原因と対処法

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## はじめに

EC-CUBE 4でプラグインやCustomizeディレクトリにカスタムコントローラーを作成し、独自のルートを定義した際に、開発環境（`APP_ENV=dev`）で以下のようなエラーが発生することがあります。

An exception has been thrown during the rendering of a template
("Parameter "route" for route "user_data" must match
"(?:[0-9a-zA-Z_\-]+\/?)+(?<!\/)" ("" given) to generate a corresponding URL.").

本記事では、このエラーの原因と対処法について解説します。

## エラーの再現手順

例として、`TopController`をカスタマイズして新しいルートを作成してみます。

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

このコントローラーを作成して `/home` にアクセスすると、エラーが発生します。