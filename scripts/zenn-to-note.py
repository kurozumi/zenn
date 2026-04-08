#!/usr/bin/env python3
"""
Zenn の記事を note 向け Markdown に変換するスクリプト

note がサポートする Markdown 記法:
  ## + スペース   大見出し
  ### + スペース  小見出し
  ---             区切り線
  > + スペース    引用
  ```             コードブロック
  - + スペース    箇条書き
  1. + スペース   番号付きリスト
  **text**        強調（太字）
  ~~text~~        取り消し線

使い方:
  # 通常変換（notes/ に出力）
  python3 scripts/zenn-to-note.py articles/foo.md

  # 出力先ディレクトリを指定
  python3 scripts/zenn-to-note.py articles/foo.md -o notes/

  # バッチ処理（全記事一括変換）
  for f in articles/*.md; do python3 scripts/zenn-to-note.py "$f" --no-open; done
"""

import re
import sys
import subprocess
import argparse
from pathlib import Path


def extract_frontmatter(text: str) -> tuple[str, str]:
    """フロントマターからタイトルを抽出し、本文を返す。"""
    title = ""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m:
        tm = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', m.group(1), re.MULTILINE)
        if tm:
            title = tm.group(1).strip('"\'')
        text = text[m.end():]
    return title, text


def convert_to_note_md(text: str) -> str:
    """Zenn 固有の記法を note 対応 Markdown に変換する。"""

    # :::message alert ... ::: → 削除
    text = re.sub(r":::message alert\n.*?:::", "", text, flags=re.DOTALL)

    # :::message ... ::: → blockquote（> スペース）
    def to_blockquote(m):
        lines = m.group(1).strip().splitlines()
        return "\n".join(f"> {line}" if line.strip() else ">" for line in lines)

    text = re.sub(r":::message\n(.*?):::", to_blockquote, text, flags=re.DOTALL)

    # :::details タイトル\n本文\n::: → **タイトル** + 本文
    text = re.sub(
        r":::details (.*?)\n(.*?):::",
        lambda m: f"**{m.group(1).strip()}**\n\n{m.group(2).strip()}",
        text,
        flags=re.DOTALL,
    )

    # H1（# ）→ 削除（note ではタイトルフィールドに入力）
    text = re.sub(r"^# .+\n?", "", text, flags=re.MULTILINE)

    # H4 以下（#### 〜）→ ### に統一（note は ## と ### のみ対応）
    text = re.sub(r"^#{4,} ", "### ", text, flags=re.MULTILINE)

    # *italic* → **italic**（note は italic 非対応のため太字に変換）
    # ただし **bold** は変換しない
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"**\1**", text)

    return text.strip()



def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


def main():
    parser = argparse.ArgumentParser(description="Zenn 記事を note 向け Markdown に変換する")
    parser.add_argument("input", help="変換する Zenn 記事のパス")
    parser.add_argument("-o", "--output", default="notes", help="出力先ディレクトリ（デフォルト: notes/）")
    parser.add_argument("--no-open", action="store_true", help="クリップボードコピーをスキップ（バッチ処理用）")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"エラー: ファイルが見つかりません: {input_path}", file=sys.stderr)
        sys.exit(1)

    slug = input_path.stem
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    text = input_path.read_text(encoding="utf-8")
    title, body = extract_frontmatter(text)
    body = convert_to_note_md(body)

    output = f"# {title}\n\n{body}" if title else body
    out_path = out_dir / f"{slug}.md"
    out_path.write_text(output, encoding="utf-8")

    if title:
        print(f"タイトル: {title}")
    print(f"✓ {out_path}")

    if not args.no_open:
        copy_to_clipboard(output)
        print("\n✓ クリップボードにコピーしました。note エディタに貼り付けてください。")


if __name__ == "__main__":
    main()
