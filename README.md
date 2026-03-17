# Zenn Articles

[![Zenn](https://img.shields.io/badge/Zenn-Articles-3EA8FF?logo=zenn)](https://zenn.dev/kurozumi)
[![Qiita](https://img.shields.io/badge/Qiita-Articles-55C500?logo=qiita)](https://qiita.com/kurozumi)

Zennで公開している記事を管理するリポジトリです。
Qiitaには要約版を自動投稿し、Zennへ誘導します。

## 使い方

```bash
# 依存パッケージをインストール
npm install

# Zennプレビュー（localhost:8000）
npm run preview

# Qiitaプレビュー（localhost:8888）
npm run preview:qiita

# 新しい記事を作成
npm run new:article
```

## Qiita連携

Zennの記事をQiita用に変換して投稿できます。

```bash
# 特定の記事を変換
npm run qiita:convert articles/eccube-xxx.md

# 全記事を変換
npm run qiita:convert:all
```

### 仕組み

1. Zennに記事を書く（`articles/`）
2. 変換スクリプトがQiita用の要約記事を生成（`public/`）
3. GitHub ActionsでQiitaに自動投稿
4. Qiita記事から「詳細はZennで」とリンク

### セットアップ

1. [Qiitaのトークン](https://qiita.com/settings/tokens/new)を発行（`read_qiita`, `write_qiita` スコープ）
2. GitHubリポジトリのSecrets に `QIITA_TOKEN` を設定
3. `articles/` に変更をpushすると自動で変換・投稿

## ディレクトリ構成

```
.
├── articles/    # Zenn記事（メイン）
├── books/       # Zenn本
├── public/      # Qiita記事（自動生成）
└── scripts/     # 変換スクリプト
```
