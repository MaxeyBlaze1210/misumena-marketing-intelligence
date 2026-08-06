from app.services.youtube_auth import get_youtube_credentials


credentials = get_youtube_credentials()

print("YouTube authentication successful")
print(credentials.valid)