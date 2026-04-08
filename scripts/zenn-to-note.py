#!/usr/bin/env python3
"""
Zenn の記事を note に貼り付けやすい Markdown に変換するスクリプト

使い方:
  # 通常変換（標準出力）
  python3 scripts/zenn-to-note.py articles/foo.md

  # ファイルに出力
  python3 scripts/zenn-to-note.py articles/foo.md -o notes/foo.md

  # 有料記事として無料・有料部分に分割して出力
  python3 scripts/zenn-to-note.py articles/foo.md --paid

記事内に <!-- paywall --> と書いた行が無料/有料の境界になります。
"""

import re
import sys
import argparse
from pathlib import Path

PAYWALL_MARKER = "<!-- paywall -->"


def zenn_to_note(text: str) -> tuple[str, str]:
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

    # :::message alert ... ::: → 削除（note では宣伝ブロックを除去）
    text = re.sub(
        r":::message alert\n.*?:::\n?",
        "",
        text,
        flags=re.DOTALL,
    )

    # :::message ... ::: → ℹ️ 付きテキスト
    text = re.sub(
        r":::message\n(.*?):::",
        lambda m: "ℹ️ " + m.group(1).strip().replace("\n", "\nℹ️ "),
        text,
        flags=re.DOTALL,
    )

    # :::details タイトル\n本文\n::: → タイトル + 本文を展開
    text = re.sub(
        r":::details (.*?)\n(.*?):::",
        lambda m: f"📋 {m.group(1).strip()}\n\n{m.group(2).strip()}",
        text,
        flags=re.DOTALL,
    )

    text = text.strip()
    return title, text


def split_paywall(body: str) -> tuple[str, str]:
    """
    <!-- paywall --> マーカーで無料部分と有料部分に分割する。
    マーカーがない場合は最初の ## 見出しの直前で分割する。
    戻り値: (free_part, paid_part)
    """
    if PAYWALL_MARKER in body:
        parts = body.split(PAYWALL_MARKER, 1)
        return parts[0].strip(), parts[1].strip()

    # マーカーがない場合: 3番目の ## 見出しの直前で分割
    # （1番目は広告、2番目は最初の本文セクションを無料に含める）
    matches = list(re.finditer(r"^## ", body, re.MULTILINE))
    if len(matches) >= 3:
        return body[:matches[2].start()].strip(), body[matches[2].start():].strip()
    elif len(matches) >= 1:
        return body[:matches[0].start()].strip(), body[matches[0].start():].strip()

    # 見出しもない場合: 全文を無料とする
    return body, ""


def main():
    parser = argparse.ArgumentParser(description="Zenn 記事を note 向けに変換する")
    parser.add_argument("input", help="変換する Zenn 記事のパス")
    parser.add_argument("-o", "--output", help="出力先ディレクトリまたはファイルパス")
    parser.add_argument("--paid", action="store_true", help="有料記事として無料/有料部分に分割する")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    text = input_path.read_text(encoding="utf-8")
    title, body = zenn_to_note(text)
    slug = input_path.stem

    if args.paid:
        # 有料記事モード: 無料部分と有料部分に分割して出力
        free_part, paid_part = split_paywall(body)

        if args.output:
            out_dir = Path(args.output) if Path(args.output).is_dir() else Path(args.output).parent
            out_dir.mkdir(parents=True, exist_ok=True)
            free_path = out_dir / f"{slug}-free.md"
            paid_path = out_dir / f"{slug}-paid.md"
            free_path.write_text(f"# {title}\n\n{free_part}" if title else free_part, encoding="utf-8")
            paid_path.write_text(paid_part, encoding="utf-8")
            print(f"【無料部分】{free_path}")
            print(f"【有料部分】{paid_path}")
        else:
            sep = "=" * 60
            print(f"【タイトル】{title}")
            print()
            print(f"{'─' * 60} 無料部分（ここまで無料で読める） {'─' * 60}")
            print(f"# {title}\n\n{free_part}" if title else free_part)
            print()
            print(f"{'─' * 60} 有料部分（ここから購入が必要） {'─' * 60}")
            print(paid_part)

    else:
        # 通常モード
        output = f"# {title}\n\n{body}" if title else body

        if args.output:
            out_path = Path(args.output)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(output, encoding="utf-8")
            print(f"変換完了: {out_path}")
            if title:
                print(f"タイトル: {title}")
        else:
            if title:
                print(f"【タイトル】{title}", file=sys.stderr)
                print("-" * 40, file=sys.stderr)
            print(output)


if __name__ == "__main__":
    main()
