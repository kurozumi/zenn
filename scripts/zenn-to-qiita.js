#!/usr/bin/env node

/**
 * Zenn記事からQiita用の要約記事を生成するスクリプト
 *
 * 使い方:
 *   node scripts/zenn-to-qiita.js articles/eccube-xxx.md
 *   node scripts/zenn-to-qiita.js --all  # 全記事を変換
 */

const fs = require('fs');
const path = require('path');

// Zennの記事ディレクトリ
const ZENN_ARTICLES_DIR = path.join(__dirname, '..', 'articles');
// Qiitaの記事ディレクトリ
const QIITA_PUBLIC_DIR = path.join(__dirname, '..', 'public');

// トピック名の変換マップ（Zenn → Qiita）
const TOPIC_MAP = {
  'eccube': 'EC-CUBE',
  'eccube4': 'EC-CUBE',
  'php': 'PHP',
  'symfony': 'Symfony',
  'btob': 'BtoB',
  'oss': 'OSS',
  'キャリア': 'キャリア',
  'AI': 'AI',
};

/**
 * Zenn記事のフロントマターを解析
 */
function parseZennFrontmatter(content) {
  const match = content.match(/^---\n([\s\S]*?)\n---/);
  if (!match) return null;

  const frontmatter = {};
  const lines = match[1].split('\n');

  for (const line of lines) {
    const [key, ...valueParts] = line.split(':');
    if (key && valueParts.length > 0) {
      let value = valueParts.join(':').trim();
      // 配列の場合
      if (value.startsWith('[') && value.endsWith(']')) {
        value = value.slice(1, -1).split(',').map(v => v.trim().replace(/"/g, ''));
      } else {
        value = value.replace(/"/g, '');
      }
      frontmatter[key.trim()] = value;
    }
  }

  return {
    frontmatter,
    body: content.slice(match[0].length).trim()
  };
}

/**
 * Zennのトピックをタグに変換
 */
function convertTopicsToTags(topics) {
  if (!Array.isArray(topics)) return ['EC-CUBE'];

  const tags = topics.map(topic => TOPIC_MAP[topic.toLowerCase()] || topic);
  // 重複を除去して最大5つまで
  return [...new Set(tags)].slice(0, 5);
}

/**
 * Zenn記事のURLを生成
 */
function getZennArticleUrl(filename) {
  const slug = path.basename(filename, '.md');
  return `https://zenn.dev/and_and/articles/${slug}`;
}

/**
 * 記事の冒頭部分を抽出（要約用）
 */
function extractSummary(body) {
  // Zennのメッセージブロックを除去
  let cleanBody = body.replace(/:::message[\s\S]*?:::/g, '');

  // 最初の見出しまでを取得
  const lines = cleanBody.split('\n');
  const summary = [];
  let foundFirstHeading = false;
  let headingCount = 0;

  for (const line of lines) {
    if (line.startsWith('## ')) {
      headingCount++;
      if (headingCount > 2) break; // 最初の2セクションまで
      foundFirstHeading = true;
    }
    if (foundFirstHeading || !line.startsWith('#')) {
      summary.push(line);
    }
  }

  return summary.join('\n').trim();
}

/**
 * Qiita用の記事を生成
 */
function generateQiitaArticle(zennFilename, zennContent) {
  const parsed = parseZennFrontmatter(zennContent);
  if (!parsed) {
    console.error(`Failed to parse frontmatter: ${zennFilename}`);
    return null;
  }

  const { frontmatter, body } = parsed;
  const tags = convertTopicsToTags(frontmatter.topics);
  const zennUrl = getZennArticleUrl(zennFilename);
  const summary = extractSummary(body);

  // Qiita用のフロントマター
  const qiitaFrontmatter = `---
title: '${frontmatter.title}'
tags:
${tags.map(tag => `  - ${tag}`).join('\n')}
private: false
updated_at: ''
id: null
organization_url_name: null
slide: false
ignorePublish: false
---
`;

  // Qiita用の本文
  const qiitaBody = `
:::note info
この記事はZennに投稿した記事の要約です。詳細は以下のリンクからご覧ください。
:::

**詳細記事: [${frontmatter.title}](${zennUrl})**

---

${summary}

---

## 続きはZennで

この記事では概要のみを紹介しました。詳細な解説やコード例は、Zennの記事をご覧ください。

**[${frontmatter.title}](${zennUrl})**

---

:::note
EC-CUBEのカスタマイズや開発のご相談は、お気軽にお問い合わせください。
:::
`;

  return qiitaFrontmatter + qiitaBody;
}

/**
 * メイン処理
 */
function main() {
  const args = process.argv.slice(2);

  if (args.length === 0) {
    console.log('Usage:');
    console.log('  node scripts/zenn-to-qiita.js <article-file>');
    console.log('  node scripts/zenn-to-qiita.js --all');
    process.exit(1);
  }

  // publicディレクトリがなければ作成
  if (!fs.existsSync(QIITA_PUBLIC_DIR)) {
    fs.mkdirSync(QIITA_PUBLIC_DIR, { recursive: true });
  }

  let files = [];

  if (args[0] === '--all') {
    // 全記事を変換
    files = fs.readdirSync(ZENN_ARTICLES_DIR)
      .filter(f => f.endsWith('.md'))
      .map(f => path.join(ZENN_ARTICLES_DIR, f));
  } else {
    // 指定された記事を変換
    files = args.map(f => {
      if (path.isAbsolute(f)) return f;
      if (f.startsWith('articles/')) return path.join(__dirname, '..', f);
      return path.join(ZENN_ARTICLES_DIR, f);
    });
  }

  for (const file of files) {
    if (!fs.existsSync(file)) {
      console.error(`File not found: ${file}`);
      continue;
    }

    const filename = path.basename(file);
    const content = fs.readFileSync(file, 'utf-8');

    // published: false の記事はスキップ
    if (content.includes('published: false')) {
      console.log(`Skipping (not published): ${filename}`);
      continue;
    }

    const qiitaContent = generateQiitaArticle(filename, content);
    if (!qiitaContent) continue;

    const outputPath = path.join(QIITA_PUBLIC_DIR, filename);
    fs.writeFileSync(outputPath, qiitaContent);
    console.log(`Generated: ${outputPath}`);
  }

  console.log('\nDone!');
}

main();
