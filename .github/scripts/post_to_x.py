#!/usr/bin/env python3
import os
import re
import sys
from requests_oauthlib import OAuth1Session


def get_title_from_file(filepath):
    """記事ファイルからタイトルを取得"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'^title:\s*["\']?([^"\']+)["\']?\s*$', content, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return None


def post_tweet(text):
    """X API v2 でツイートを投稿"""
    client = OAuth1Session(
        os.environ['X_API_KEY'],
        client_secret=os.environ['X_API_KEY_SECRET'],
        resource_owner_key=os.environ['X_ACCESS_TOKEN'],
        resource_owner_secret=os.environ['X_ACCESS_TOKEN_SECRET']
    )

    response = client.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text}
    )

    if response.status_code == 201:
        print("Tweet posted successfully!")
        print(response.json())
        return True
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
        return False


def main():
    added_files = os.environ.get('ADDED_FILES', '').strip()

    if not added_files:
        print("No new articles found.")
        return

    for filepath in added_files.split('\n'):
        filepath = filepath.strip()
        if not filepath:
            continue

        print(f"Processing: {filepath}")

        # タイトルを取得
        title = get_title_from_file(filepath)
        if not title:
            print(f"Could not extract title from {filepath}")
            continue

        # スラッグを取得（ファイル名から.mdを除く）
        slug = os.path.basename(filepath).replace('.md', '')

        # URLを生成
        url = f"https://zenn.dev/kurozumi/articles/{slug}"

        # ツイート本文を作成
        tweet = f"""📝 新しい記事を投稿しました

{title}

{url}

#eccube #php #symfony"""

        print(f"Tweet content:\n{tweet}\n")

        if not post_tweet(tweet):
            sys.exit(1)


if __name__ == '__main__':
    main()
