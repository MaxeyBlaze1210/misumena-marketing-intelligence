from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
]

CLIENT_SECRET_FILE = Path(
    "secrets/gmail_client_secret.json"
)

TOKEN_FILE = Path(
    "secrets/gmail_token.json"
)


def get_gmail_credentials():
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(
            TOKEN_FILE,
            SCOPES,
        )

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES,
        )

        creds = flow.run_local_server(
            host="127.0.0.1",
            port=0,
            open_browser=True,
        )

        TOKEN_FILE.write_text(
            creds.to_json()
        )

    return creds


def get_gmail_service():
    return build(
        "gmail",
        "v1",
        credentials=get_gmail_credentials(),
    )


def authorize():
    get_gmail_service()

    print()
    print("Gmail authorization successful.")
    print(f"Token stored in: {TOKEN_FILE}")
    print()


if __name__ == "__main__":
    authorize()
