import os
import requests

GRAPH_API_VERSION = "v25.0"
BASE_URL = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]
INSTAGRAM_ACCOUNT_ID = os.environ["INSTAGRAM_ACCOUNT_ID"]


def get_instagram_media():
    url = f"{BASE_URL}/{INSTAGRAM_ACCOUNT_ID}/media"

    params = {
        "fields": (
            "id,"
            "caption,"
            "media_type,"
            "media_product_type,"
            "permalink,"
            "timestamp,"
            "like_count,"
            "comments_count"
        ),
        "limit": 100,
        "access_token": ACCESS_TOKEN,
    }

    items = []

    while url:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()

        payload = response.json()
        items.extend(payload.get("data", []))

        url = payload.get("paging", {}).get("next")
        params = None

    return items


def get_reels():
    media = get_instagram_media()

    return [
        item
        for item in media
        if item.get("media_product_type") == "REELS"
    ]


if __name__ == "__main__":
    reels = get_reels()

    print(f"Found {len(reels)} reels\n")

    for reel in reels:
        print(
            reel["id"],
            reel.get("timestamp"),
            f"likes={reel.get('like_count')}",
            f"comments={reel.get('comments_count')}",
            reel.get("caption", "")[:80],
        )
