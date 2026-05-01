#!/usr/bin/env python3
"""
Zenn book → EPUB (Kindle) 変換スクリプト
Usage: python3 scripts/zenn-book-to-epub.py
"""

import re
import subprocess
import sys
from pathlib import Path

BOOK_DIR = Path("books/eccube-btob-plugin-guide")
OUTPUT_DIR = Path("epub")
OUTPUT_FILE = OUTPUT_DIR / "eccube-btob-plugin-guide.epub"

CHAPTERS = ["intro", "chapter1", "chapter2", "chapter3", "chapter4", "chapter5", "chapter6", "chapter7"]

METADATA = {
    "title": "EC-CUBEではじめるBtoB ECサイト構築ガイド",
    "author": "kurozumi",
    "language": "ja",
    "description": "EC-CUBE標準では実現できないBtoB要件（法人審査・卸価格・支払い制限・配送制限）を、会員グループ管理プラグインとアドオン群でコーディング不要で解決する方法を解説します。",
}


def strip_frontmatter(text: str) -> tuple[str, dict]:
    """フロントマターを除去してタイトルを返す"""
    meta = {}
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm = text[3:end].strip()
            for line in fm.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip().strip('"')
            text = text[end + 3:].strip()
    return text, meta


def strip_zenn_syntax(text: str) -> str:
    """Zenn固有の記法を除去・変換する"""

    # :::message alert ... ::: → 囲み文字に変換
    text = re.sub(
        r":::message alert\n(.*?):::",
        lambda m: "\n> ⚠️ **注意**\n>\n" + "\n".join("> " + l for l in m.group(1).strip().splitlines()) + "\n",
        text,
        flags=re.DOTALL,
    )

    # :::message ... ::: → 囲み文字に変換
    text = re.sub(
        r":::message\n(.*?):::",
        lambda m: "\n> 📝 **メモ**\n>\n" + "\n".join("> " + l for l in m.group(1).strip().splitlines()) + "\n",
        text,
        flags=re.DOTALL,
    )

    # :::details ... ::: → 展開（Kindleはdetailsタグ非対応）
    text = re.sub(
        r":::details (.+?)\n(.*?):::",
        lambda m: f"\n**{m.group(1).strip()}**\n\n{m.group(2).strip()}\n",
        text,
        flags=re.DOTALL,
    )

    return text


def strip_cta_banners(text: str) -> str:
    """お仕事募集バナーと末尾CTAを除去する"""

    # 冒頭バナー（:::message alert ブロック全体）
    # すでに strip_zenn_syntax で変換済みの場合はスキップ
    # ここでは変換前に適用するため、特定パターンで除去
    text = re.sub(
        r"> ⚠️ \*\*注意\*\*\n>.*?募集.*?\n(?:>.*?\n)*",
        "",
        text,
        flags=re.DOTALL,
    )

    # 末尾CTA（## 📩 EC-CUBE開発... 以降）
    text = re.sub(
        r"\n---\n\n## 📩 EC-CUBE開発・カスタマイズのご相談.*$",
        "",
        text,
        flags=re.DOTALL,
    )

    # プラグイン一覧セクション（## 🔌 プラグイン一覧 以降も末尾CTAの前にある場合）
    # ※ 本のチャプターには含まれないが念のため

    return text


def process_chapter(chapter_name: str) -> str:
    """チャプターファイルを処理してMarkdownを返す"""
    path = BOOK_DIR / f"{chapter_name}.md"
    text = path.read_text(encoding="utf-8")

    text, meta = strip_frontmatter(text)
    title = meta.get("title", "")

    text = strip_zenn_syntax(text)
    text = strip_cta_banners(text)

    # チャプタータイトルを H1 として先頭に追加
    if title:
        text = f"# {title}\n\n{text.strip()}\n"
    else:
        text = text.strip() + "\n"

    return text


def build_combined_markdown(tmp_path: Path):
    """全チャプターを結合した Markdown ファイルを生成する"""
    parts = []
    for chapter in CHAPTERS:
        print(f"  Processing {chapter}.md ...")
        parts.append(process_chapter(chapter))

    tmp_path.write_text("\n\n---\n\n".join(parts), encoding="utf-8")


def build_epub(md_path: Path):
    """PandocでEPUBを生成する"""
    cover = BOOK_DIR / "cover.png"

    cmd = [
        "pandoc",
        str(md_path),
        "--from=markdown",
        "--to=epub3",
        f"--output={OUTPUT_FILE}",
        f"--metadata=title:{METADATA['title']}",
        f"--metadata=author:{METADATA['author']}",
        f"--metadata=lang:{METADATA['language']}",
        "--toc",
        "--toc-depth=2",
        "--epub-title-page=false",
    ]

    if cover.exists():
        cmd.append(f"--epub-cover-image={cover}")

    print(f"\n  Running: {' '.join(cmd)}\n")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print("Pandoc error:")
        print(result.stderr)
        sys.exit(1)

    if result.stderr:
        print(result.stderr)


def main():
    print("=== Zenn Book → EPUB 変換 ===\n")

    OUTPUT_DIR.mkdir(exist_ok=True)

    tmp_md = OUTPUT_DIR / "_combined.md"

    print("[1/2] チャプターを結合中...")
    build_combined_markdown(tmp_md)
    print(f"  → {tmp_md} ({tmp_md.stat().st_size // 1024} KB)\n")

    print("[2/2] EPUB生成中...")
    build_epub(tmp_md)
    print(f"  → {OUTPUT_FILE} ({OUTPUT_FILE.stat().st_size // 1024} KB)\n")

    tmp_md.unlink()

    print(f"✅ 完成: {OUTPUT_FILE}")
    print("\nKindle Direct Publishing へのアップロード手順:")
    print("  1. https://kdp.amazon.co.jp/ にアクセス")
    print("  2. 「新しいタイトルを追加」→「Kindle 電子書籍」")
    print("  3. epub/ フォルダの .epub ファイルをアップロード")


if __name__ == "__main__":
    main()
