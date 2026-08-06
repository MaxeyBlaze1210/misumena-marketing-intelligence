import os

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = [
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


CLIENT_SECRET_FILE = "secrets/youtube_client_secret.json"
TOKEN_FILE = "secrets/youtube_token.json"


def get_youtube_credentials():
    credentials = None

    # Load existing token
    if os.path.exists(TOKEN_FILE):
        credentials = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    # Refresh expired token
    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())

    # First-time login
    if not credentials or not credentials.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES,
        )

        credentials = flow.run_local_server(
            port=0
        )

        # Save token
        with open(TOKEN_FILE, "w") as token:
            token.write(credentials.to_json())

    return credentials