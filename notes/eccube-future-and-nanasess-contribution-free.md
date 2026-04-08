# EC-CUBEの未来を考える - 主要コントリビューターの貢献から見えるもの

ℹ️ この記事は EC-CUBE 4.3 以上を対象としています。
ℹ️ また、[Claude Code](https://claude.ai/claude-code) を使って書かれています。内容に誤りがある場合はコメントでお知らせください。

## はじめに

EC-CUBEは日本最大のオープンソースECプラットフォームとして、多くのECサイトで利用されています。しかし近年、Shopify、BASE、STORESなどのSaaS型ECプラットフォームの台頭により、オープンソースECを取り巻く環境は大きく変化しています。

本記事では、EC-CUBEの主要コントリビューターである大河内健太郎氏（[@nanasess](https://github.com/nanasess)）と木元伸彦氏（[@nobuhiko](https://github.com/nobuhiko)）の貢献を数値で振り返りながら、EC-CUBEが今後生き残っていくための戦略を考察します。

## 大河内健太郎氏（nanasess）とは

### 基本プロフィール

- **所属**: Skirnir Inc.（大阪）
- **GitHub参加**: 2011年5月〜（約15年）
- **プロフィール**: 自称「寿司職人」、GNU Emacsアイコンコントリビューター

プロフィールには「寿司職人」とありますが、その実態はEC-CUBEの心臓部を**約18年間**支え続けてきた中心人物です。

### EC-CUBEへの圧倒的な貢献

GitHubのデータを調査した結果、以下の数値が明らかになりました。

| 指標 | 数値 | 備考 |
|------|------|------|
| EC-CUBE本体コミット数 | **2,165** | **ダントツ1位** |
| EC-CUBE組織全体コミット | **6,867** | EC-CUBE2含む |
| マージされたPR | **529** | EC-CUBE本体のみ |
| EC-CUBE組織へのPR | **1,089** | 全リポジトリ |
| 貢献期間 | **2007年頃〜現在** | **約18年**（Subversion時代含む） |

ℹ️ 上記のGitHubの数値は、2014年にGitHubへ移行した後のデータです。大河内氏はSubversion時代の2007年頃からEC-CUBEに貢献しており、実際の貢献期間は約18年に及びます。

### コントリビューターランキング

EC-CUBE本体リポジトリのコントリビューターランキングを見てみましょう。

1位: nanasess       2,165 commits ← 大河内さん
2位: chihiro-adachi 1,742 commits
3位: k-yamamura     1,165 commits
4位: okazy          1,097 commits
5位: kiy0taka         942 commits

2位との差は**423コミット**。GitHub移行後だけで2,165コミット、Subversion時代を含めると18年以上の継続的な貢献です。これは個人の献身なくしては不可能な数字です。

### EC-CUBE以外の貢献

大河内氏はEC-CUBE以外にも多くの貢献をしています。

- **他プロジェクトへのマージ済みPR**: 1,075件
- **自作の[setup-chromedriver](https://github.com/nanasess/setup-chromedriver)**: 124スター、38フォーク
  - GitHub Actions用のChromeDriver自動セットアップツール
  - Ubuntu/macOS/Windows対応
  - 多くのCI/CDパイプラインで採用

# setup-chromedriverの使用例
- uses: nanasess/setup-chromedriver@v2

このツールは、GitHub Marketplaceに登録され、多くのプロジェクトのE2Eテストで利用されています。