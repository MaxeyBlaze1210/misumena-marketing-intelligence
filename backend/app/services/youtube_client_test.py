from app.services.youtube_service import get_youtube_client


youtube = get_youtube_client()

print("YouTube API client created")
print(youtube)

