import json
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import requests

from app.core.config import settings


AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"

REDIRECT_URI = "http://127.0.0.1:8888/callback"
TOKEN_FILE = Path("secrets/spotify_playlist_token.json")

SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
]


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    authorization_code = None
    received_state = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)

        OAuthCallbackHandler.authorization_code = params.get("code", [None])[0]
        OAuthCallbackHandler.received_state = params.get("state", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        self.wfile.write(
            b"<h2>Spotify authorization successful.</h2>"
            b"<p>You can close this browser tab and return to Terminal.</p>"
        )

    def log_message(self, format, *args):
        return


def save_token(token_data: dict):
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    token_data["saved_at"] = int(time.time())

    TOKEN_FILE.write_text(
        json.dumps(token_data, indent=2)
    )


def load_token() -> dict | None:
    if not TOKEN_FILE.exists():
        return None

    return json.loads(TOKEN_FILE.read_text())


def refresh_access_token(refresh_token: str) -> dict:
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        auth=(
            settings.spotify_playlist_client_id,
            settings.spotify_playlist_client_secret,
        ),
        timeout=30,
    )

    response.raise_for_status()

    new_data = response.json()

    old_data = load_token() or {}

    if "refresh_token" not in new_data:
        new_data["refresh_token"] = old_data.get("refresh_token")

    save_token(new_data)

    return new_data


def get_user_access_token() -> str:
    token_data = load_token()

    if not token_data:
        raise RuntimeError(
            "No Spotify playlist token found. "
            "Run authorize() first."
        )

    saved_at = token_data.get("saved_at", 0)
    expires_in = token_data.get("expires_in", 3600)

    if time.time() < saved_at + expires_in - 60:
        return token_data["access_token"]

    refreshed = refresh_access_token(
        token_data["refresh_token"]
    )

    return refreshed["access_token"]


def authorize():
    state = secrets.token_urlsafe(24)

    query = urllib.parse.urlencode(
        {
            "client_id": settings.spotify_playlist_client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": " ".join(SCOPES),
            "state": state,
            "show_dialog": "true",
        }
    )

    url = f"{AUTH_URL}?{query}"

    print()
    print("Opening Spotify authorization in your browser...")
    print()
    print("IMPORTANT:")
    print("Log in as your Premium Maxey Blaze Spotify account.")
    print()

    webbrowser.open(url)

    server = HTTPServer(
        ("127.0.0.1", 8888),
        OAuthCallbackHandler,
    )

    print("Waiting for Spotify callback...")
    server.handle_request()

    code = OAuthCallbackHandler.authorization_code
    received_state = OAuthCallbackHandler.received_state

    if not code:
        raise RuntimeError("Spotify did not return an authorization code")

    if received_state != state:
        raise RuntimeError("OAuth state mismatch")

    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
        auth=(
            settings.spotify_playlist_client_id,
            settings.spotify_playlist_client_secret,
        ),
        timeout=30,
    )

    response.raise_for_status()

    token_data = response.json()
    save_token(token_data)

    print()
    print("Spotify playlist OAuth token saved successfully.")
    print(f"Saved to: {TOKEN_FILE}")


if __name__ == "__main__":
    authorize()
