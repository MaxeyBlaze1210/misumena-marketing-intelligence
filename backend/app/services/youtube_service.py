from googleapiclient.discovery import build

from app.core.config import settings


youtube = build(
    "youtube",
    "v3",
    developerKey=settings.youtube_api_key,
)


def search_videos(query: str):
    request = youtube.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=5,
    )

    response = request.execute()

    return response["items"]