#!/usr/bin/env python3
"""
note.com 投稿スクリプト

使い方:
  # 初回: ブラウザを開いてログインし、セッションを保存する
  python3 scripts/note-post.py login

  # 記事を投稿（下書き保存まで自動化）
  python3 scripts/note-post.py post <slug>
  例: python3 scripts/note-post.py post eccube-csrf-attribute-redirect-bug

  # 有料記事として投稿（無料/有料の分割あり）
  python3 scripts/note-post.py post <slug> --paid

オプション:
  --notes-dir  notes/ ディレクトリのパス（デフォルト: notes/）
  --paid       有料記事として投稿（paywall を挿入）
  --publish    投稿後に自動公開する（デフォルト: 下書き保存のみ）

前提:
  pip3 install playwright
  python3 -m playwright install chromium
"""

import sys
import time
import argparse
import subprocess
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# ブラウザのプロファイルを保存するディレクトリ（Cookieやローカルストレージをまるごと保持）
PROFILE_DIR = Path(".note-profile")
NOTE_BASE_URL = "https://note.com"


# ---------------------------------------------------------------------------
# ログインフロー
# ---------------------------------------------------------------------------

def cmd_login(args) -> None:
    """ブラウザを開いてユーザーが手動でログインし、プロファイルを保存する。"""
    print("ブラウザを開きます。note.com にログインしてください。")
    print(f"ログイン情報は {PROFILE_DIR}/ に保存されます（次回から自動ログイン）。")

    PROFILE_DIR.mkdir(exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(f"{NOTE_BASE_URL}/login")

        print("\nログイン画面が開きました。手動でログインしてください...")
        print("ログイン後のダッシュボードへの遷移を待っています（最大2分）...")

        try:
            page.wait_for_url(
                lambda url: "/login" not in url and "/signup" not in url,
                timeout=120_000,
            )
            print("\nログインを検出しました。")
        except PlaywrightTimeoutError:
            print("タイムアウト: ログインを確認できませんでした。")
            context.close()
            return

        print(f"セッションを保存しました: {PROFILE_DIR}/")
        print("ログイン成功！次回からは 'post' コマンドを使って投稿できます。")
        context.close()


# ---------------------------------------------------------------------------
# コンテンツ読み込み
# ---------------------------------------------------------------------------

def load_article(slug: str, notes_dir: Path, paid: bool) -> dict:
    """
    notes/ ディレクトリから記事を読み込む。
    戻り値: {"title": str, "free_body": str, "paid_body": str}
    """
    if paid:
        free_path = notes_dir / f"{slug}-free.md"
        paid_path = notes_dir / f"{slug}-paid.md"

        if not free_path.exists():
            print(f"エラー: {free_path} が見つかりません。", file=sys.stderr)
            sys.exit(1)

        free_text = free_path.read_text(encoding="utf-8")
        paid_text = paid_path.read_text(encoding="utf-8") if paid_path.exists() else ""

        title, free_body = _extract_title(free_text)
        return {"title": title, "free_body": free_body, "paid_body": paid_text}
    else:
        single_path = notes_dir / f"{slug}.md"
        free_path = notes_dir / f"{slug}-free.md"

        path = single_path if single_path.exists() else free_path
        if not path.exists():
            print(f"エラー: {single_path} または {free_path} が見つかりません。", file=sys.stderr)
            sys.exit(1)

        text = path.read_text(encoding="utf-8")
        title, body = _extract_title(text)
        return {"title": title, "free_body": body, "paid_body": ""}


def _extract_title(text: str) -> tuple[str, str]:
    """先頭の # タイトル行を抜き出す。"""
    lines = text.splitlines()
    title = ""
    body_lines = []
    for line in lines:
        if not title and line.startswith("# "):
            title = line[2:].strip()
        else:
            body_lines.append(line)
    body = "\n".join(body_lines).strip()
    return title, body


# ---------------------------------------------------------------------------
# クリップボードへテキストをコピー（macOS）
# ---------------------------------------------------------------------------

def copy_to_clipboard(text: str) -> None:
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)


# ---------------------------------------------------------------------------
# note.com エディタへの入力ヘルパー
# ---------------------------------------------------------------------------

def _find_editor(page) -> object:
    """note.com のエディタ要素を返す。"""
    selectors = [
        ".ProseMirror",
        '[contenteditable="true"]',
        '[data-cy="editor-content"]',
        '[class*="editor"]',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                return el
        except Exception:
            continue
    return None


def _find_title_input(page) -> object:
    """note.com のタイトル入力欄を返す。"""
    selectors = [
        '[placeholder*="タイトル"]',
        '[data-cy="title-input"]',
        'input[name="name"]',
        'textarea[name="name"]',
    ]
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                return el
        except Exception:
            continue
    return None


def _paste_text(page, text: str) -> None:
    """クリップボード経由でテキストを貼り付ける。"""
    copy_to_clipboard(text)
    page.keyboard.press("Meta+v")
    time.sleep(0.8)


def _insert_paywall(page) -> bool:
    """
    有料エリア設定ボタンを押してペイウォールを挿入する。
    成功したら True を返す。
    """
    selectors = [
        'button:has-text("有料エリア")',
        'button:has-text("有料設定")',
        'button[aria-label*="有料"]',
        'button[title*="有料"]',
        '[data-cy*="paywall"]',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(0.5)
                print("  ✓ ペイウォールを挿入しました。")
                return True
        except Exception:
            continue

    print("  ⚠ ペイウォールボタンが見つかりませんでした。手動で挿入してください。")
    return False


# ---------------------------------------------------------------------------
# 投稿フロー
# ---------------------------------------------------------------------------

def cmd_post(args) -> None:
    if not PROFILE_DIR.exists():
        print("プロファイルが見つかりません。先に 'login' コマンドを実行してください。")
        sys.exit(1)

    notes_dir = Path(args.notes_dir)
    article = load_article(args.slug, notes_dir, args.paid)

    print(f"\n記事: {article['title']}")
    print(f"無料部分: {len(article['free_body'])} 文字")
    if args.paid:
        print(f"有料部分: {len(article['paid_body'])} 文字")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1280, "height": 900},
        )
        page = context.pages[0] if context.pages else context.new_page()

        # --- 新規投稿ページへ ---
        print("\nnote.com の新規投稿ページを開いています...")
        page.goto(f"{NOTE_BASE_URL}/notes/new", wait_until="networkidle")
        time.sleep(2)

        # ログイン確認
        if "/login" in page.url:
            print("セッションが無効です。'login' コマンドを再実行してください。")
            context.close()
            sys.exit(1)

        print(f"  ✓ URL: {page.url}")

        # --- タイトル入力 ---
        print("\nタイトルを入力中...")
        title_el = _find_title_input(page)
        if title_el:
            title_el.click()
            time.sleep(0.3)
            title_el.fill(article["title"])
            print(f"  ✓ タイトル: {article['title']}")
        else:
            print("  ⚠ タイトル入力欄が見つかりませんでした。手動で入力してください。")
            _wait_user("タイトルを入力したら Enter を押してください: ")

        # --- エディタへフォーカス ---
        print("\n本文を入力中...")
        editor = _find_editor(page)
        if not editor:
            print("  ⚠ エディタが見つかりませんでした。")
            page.screenshot(path="/tmp/note-debug.png")
            print("  スクリーンショット → /tmp/note-debug.png")
            _wait_user("手動でエディタをクリックしたら Enter を押してください: ")
            editor = _find_editor(page)

        if editor:
            editor.click()
            time.sleep(0.3)

        # --- 無料部分を貼り付け ---
        _paste_text(page, article["free_body"])
        print("  ✓ 無料部分を貼り付けました。")
        time.sleep(1)

        # --- 有料部分（ペイウォール挿入） ---
        if args.paid and article["paid_body"]:
            print("\nペイウォールを挿入中...")
            page.keyboard.press("End")
            time.sleep(0.3)

            inserted = _insert_paywall(page)
            if not inserted:
                _wait_user("ペイウォールを手動で挿入したら Enter を押してください: ")

            time.sleep(0.5)
            _paste_text(page, article["paid_body"])
            print("  ✓ 有料部分を貼り付けました。")

        # --- 公開 or 下書き保存 ---
        if args.publish:
            print("\n公開処理を実行中...")
            _publish(page)
        else:
            print("\n下書き保存中...")
            _save_draft(page)

        print("\n完了！ブラウザで内容を確認してください。")
        _wait_user("確認が終わったら Enter を押してブラウザを閉じます: ")
        context.close()


def _wait_user(prompt: str) -> None:
    try:
        input(prompt)
    except (KeyboardInterrupt, EOFError):
        sys.exit(0)


def _save_draft(page) -> None:
    selectors = [
        'button:has-text("下書き保存")',
        'button[aria-label*="下書き"]',
        '[data-cy="save-draft"]',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(1)
                print("  ✓ 下書き保存しました。")
                return
        except Exception:
            continue
    print("  ⚠ 下書き保存ボタンが見つかりません。手動で保存してください。")


def _publish(page) -> None:
    selectors = [
        'button:has-text("公開")',
        'button[aria-label*="公開"]',
        '[data-cy="publish"]',
    ]
    for sel in selectors:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                time.sleep(1)
                print("  ✓ 公開ボタンをクリックしました。")
                try:
                    confirm = page.locator('button:has-text("公開する")').first
                    if confirm.is_visible(timeout=3000):
                        confirm.click()
                        print("  ✓ 公開確認しました。")
                except Exception:
                    pass
                return
        except Exception:
            continue
    print("  ⚠ 公開ボタンが見つかりません。手動で公開してください。")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="note.com 投稿スクリプト")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # login
    subparsers.add_parser("login", help="ブラウザでログインしてセッションを保存")

    # post
    post_parser = subparsers.add_parser("post", help="記事を投稿")
    post_parser.add_argument("slug", help="記事のスラッグ（例: eccube-csrf-attribute-redirect-bug）")
    post_parser.add_argument("--notes-dir", default="notes", help="notes/ ディレクトリのパス（デフォルト: notes/）")
    post_parser.add_argument("--paid", action="store_true", help="有料記事として投稿")
    post_parser.add_argument("--publish", action="store_true", help="投稿後に自動公開（デフォルト: 下書き保存）")

    args = parser.parse_args()

    if args.command == "login":
        cmd_login(args)
    elif args.command == "post":
        cmd_post(args)


if __name__ == "__main__":
    main()
