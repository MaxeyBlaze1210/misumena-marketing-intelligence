from googleapiclient.discovery import build

from app.core.config import settings
from app.services.youtube_auth import get_youtube_credentials


# Public YouTube Data API (API key)
youtube_public = build(
    "youtube",
    "v3",
    developerKey=settings.youtube_api_key,
)


def search_videos(query: str):
    request = youtube_public.search().list(
        part="snippet",
        q=query,
        type="video",
        maxResults=5,
    )

    response = request.execute()

    return response["items"]


# Authenticated YouTube client (OAuth)
def get_youtube_client():
    credentials = get_youtube_credentials()

    youtube = build(
        "youtube",
        "v3",
        credentials=credentials,
    )

    return youtube