from googleapiclient.discovery import build

from app.services.youtube_auth import get_youtube_credentials

credentials = get_youtube_credentials()

youtube = build("youtube", "v3", credentials=credentials)

response = youtube.channels().list(
    part="snippet,statistics",
    mine=True,
).execute()

print(response)