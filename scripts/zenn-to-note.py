#!/usr/bin/env python3
"""
Zenn の記事を note に貼り付けやすい Markdown に変換するスクリプト

使い方:
  python3 scripts/zenn-to-note.py articles/eccube-ga4-funnel-ai-analysis.md
  python3 scripts/zenn-to-note.py articles/eccube-ga4-funnel-ai-analysis.md -o output.md
"""

import re
import sys
import argparse
from pathlib import Path


def convert(text: str) -> tuple[str, str]:
    """
    Zenn markdown を note 向けに変換する。
    戻り値: (title, converted_body)
    """

    # --- フロントマターを抽出して除去 ---
    title = ""
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        title_match = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', frontmatter, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip('"\'')
        text = text[match.end():]

    # --- Zenn 固有の記法を変換 ---

    # :::message alert ... ::: → 枠で囲った注意書き
    text = re.sub(
        r":::message alert\n(.*?):::",
        lambda m: "⚠️ " + m.group(1).strip().replace("\n", "\n⚠️ "),
        text,
        flags=re.DOTALL,
    )

    # :::message ... ::: → ℹ️ 付きの注記
    text = re.sub(
        r":::message\n(.*?):::",
        lambda m: "ℹ️ " + m.group(1).strip().replace("\n", "\nℹ️ "),
        text,
        flags=re.DOTALL,
    )

    # :::details タイトル\n本文\n::: → 折りたたみなし（タイトル + 本文を展開）
    text = re.sub(
        r":::details (.*?)\n(.*?):::",
        lambda m: f"📋 {m.group(1).strip()}\n\n{m.group(2).strip()}",
        text,
        flags=re.DOTALL,
    )

    # 先頭・末尾の空白行を整理
    text = text.strip()

    return title, text


def main():
    parser = argparse.ArgumentParser(description="Zenn 記事を note 向けに変換する")
    parser.add_argument("input", help="変換する Zenn 記事のパス")
    parser.add_argument("-o", "--output", help="出力ファイルパス（省略時は標準出力）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    title, body = convert(text)

    output = f"# {title}\n\n{body}" if title else body

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"変換完了: {args.output}")
        if title:
            print(f"タイトル: {title}")
    else:
        if title:
            print(f"【タイトル】{title}", file=sys.stderr)
            print("-" * 40, file=sys.stderr)
        print(output)


if __name__ == "__main__":
    main()
