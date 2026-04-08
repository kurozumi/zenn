#!/usr/bin/env python3
"""
Zenn の記事を note 向けリッチテキスト（HTML）に変換するスクリプト

使い方:
  # HTML に変換してブラウザで開く（Cmd+A → Cmd+C → note に貼り付け）
  python3 scripts/zenn-to-note.py articles/foo.md

  # 有料記事として無料・有料部分に分割
  python3 scripts/zenn-to-note.py articles/foo.md --paid

  # 出力先ディレクトリを指定（デフォルト: notes/）
  python3 scripts/zenn-to-note.py articles/foo.md -o notes/

前提:
  pip3 install markdown
"""

import re
import sys
import subprocess
import argparse
from pathlib import Path

try:
    import markdown as md_lib
    HAS_MARKDOWN = True
except ImportError:
    HAS_MARKDOWN = False

PAYWALL_MARKER = "<!-- paywall -->"

CSS = """
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  max-width: 780px;
  margin: 40px auto;
  padding: 0 24px 80px;
  line-height: 1.85;
  color: #333;
  font-size: 16px;
}
h1 { font-size: 1.7em; margin-top: 0; margin-bottom: 0.5em; }
h2 { font-size: 1.35em; margin-top: 2.2em; border-bottom: 1px solid #e8e8e8; padding-bottom: 0.3em; }
h3 { font-size: 1.15em; margin-top: 1.8em; }
p  { margin: 0.9em 0; }
code {
  background: #f3f3f3;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.88em;
  font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
}
pre {
  background: #f3f3f3;
  padding: 16px 18px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 1.2em 0;
}
pre code { background: none; padding: 0; font-size: 0.85em; }
blockquote {
  border-left: 4px solid #d0d0d0;
  margin: 1.2em 0;
  padding: 0.6em 1em;
  color: #555;
  background: #fafafa;
  border-radius: 0 4px 4px 0;
}
blockquote p { margin: 0.3em 0; }
hr { border: none; border-top: 1px solid #e0e0e0; margin: 2em 0; }
ul, ol { padding-left: 1.6em; margin: 0.8em 0; }
li { margin: 0.4em 0; }
table { border-collapse: collapse; width: 100%; margin: 1em 0; }
th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
th { background: #f3f3f3; font-weight: 600; }
a { color: #0070f3; text-decoration: none; }
a:hover { text-decoration: underline; }
img { max-width: 100%; border-radius: 4px; }
.info-box {
  text-align: center;
  background: #e8f4ff;
  border: 1px solid #b3d7ff;
  border-radius: 8px;
  padding: 14px 20px;
  margin-bottom: 32px;
  font-size: 14px;
  color: #0055aa;
}
"""


def build_html(title: str, body_html: str, show_hint: bool = True) -> str:
    title_attr = title if title else "note 変換プレビュー"
    title_tag = f"<h1>{title}</h1>\n" if title else ""
    hint = (
        '<div class="info-box">'
        "📋 <strong>Cmd+A</strong> で全選択 → <strong>Cmd+C</strong> でコピー → note エディタに貼り付け"
        "</div>\n"
        if show_hint
        else ""
    )
    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>{title_attr}</title>
<style>{CSS}</style>
</head>
<body>
{hint}{title_tag}{body_html}
</body>
</html>
"""


def extract_frontmatter(text: str) -> tuple[str, str]:
    title = ""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if m:
        tm = re.search(r'^title:\s*["\']?(.*?)["\']?\s*$', m.group(1), re.MULTILINE)
        if tm:
            title = tm.group(1).strip('"\'')
        text = text[m.end():]
    return title, text


def preprocess_zenn(text: str) -> str:
    """Zenn 固有の記法を標準 Markdown に変換する。"""

    # :::message alert ... ::: → 削除（バージョン注意書き等）
    text = re.sub(r":::message alert\n.*?:::", "", text, flags=re.DOTALL)

    # :::message ... ::: → blockquote
    def to_blockquote(m):
        lines = m.group(1).strip().splitlines()
        return "\n".join(f"> {line}" for line in lines)

    text = re.sub(r":::message\n(.*?):::", to_blockquote, text, flags=re.DOTALL)

    # :::details タイトル\n本文\n::: → bold タイトル + 本文
    text = re.sub(
        r":::details (.*?)\n(.*?):::",
        lambda m: f"**{m.group(1).strip()}**\n\n{m.group(2).strip()}",
        text,
        flags=re.DOTALL,
    )

    return text.strip()


def to_html(text: str) -> str:
    if not HAS_MARKDOWN:
        print("エラー: markdown ライブラリが必要です。\n  pip3 install markdown", file=sys.stderr)
        sys.exit(1)
    return md_lib.markdown(text, extensions=["fenced_code", "tables", "nl2br", "sane_lists"])


def split_paywall(text: str) -> tuple[str, str]:
    if PAYWALL_MARKER in text:
        parts = text.split(PAYWALL_MARKER, 1)
        return parts[0].strip(), parts[1].strip()

    matches = list(re.finditer(r"^## ", text, re.MULTILINE))
    if len(matches) >= 3:
        return text[: matches[2].start()].strip(), text[matches[2].start() :].strip()
    if len(matches) >= 1:
        return text[: matches[0].start()].strip(), text[matches[0].start() :].strip()
    return text, ""


def open_browser(path: Path) -> None:
    subprocess.run(["open", str(path)], check=False)


def main():
    parser = argparse.ArgumentParser(description="Zenn 記事を note 向けリッチテキスト（HTML）に変換する")
    parser.add_argument("input", help="変換する Zenn 記事のパス")
    parser.add_argument("-o", "--output", default="notes", help="出力先ディレクトリ（デフォルト: notes/）")
    parser.add_argument("--paid", action="store_true", help="有料記事として無料/有料部分に分割する")
    parser.add_argument("--no-open", action="store_true", help="ブラウザを自動で開かない（バッチ処理用）")
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
    body = preprocess_zenn(body)

    if args.paid:
        free_md, paid_md = split_paywall(body)

        free_path = out_dir / f"{slug}-free.html"
        paid_path = out_dir / f"{slug}-paid.html"

        free_path.write_text(build_html(title, to_html(free_md)), encoding="utf-8")
        print(f"✓ 無料部分: {free_path}")

        if paid_md:
            paid_path.write_text(build_html("", to_html(paid_md)), encoding="utf-8")
            print(f"✓ 有料部分: {paid_path}")

        if title:
            print(f"\nタイトル: {title}")

        if not args.no_open:
            print("\n【無料部分】ブラウザで開きます...")
            open_browser(free_path)
            if paid_md:
                input("\nEnter を押すと有料部分を開きます: ")
                open_browser(paid_path)

    else:
        out_path = out_dir / f"{slug}.html"
        out_path.write_text(build_html(title, to_html(body)), encoding="utf-8")

        if title:
            print(f"タイトル: {title}")
        print(f"✓ {out_path}")
        if not args.no_open:
            print("\nブラウザで開きます...")
            open_browser(out_path)

    if not args.no_open:
        print("\n操作: Cmd+A → Cmd+C → note エディタに貼り付け")


if __name__ == "__main__":
    main()
