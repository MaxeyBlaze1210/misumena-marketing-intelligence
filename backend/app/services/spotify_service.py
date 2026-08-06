import time

import requests

from app.core.config import settings

TOKEN_URL = "https://accounts.spotify.com/api/token"
SEARCH_URL = "https://api.spotify.com/v1/search"
ALBUM_URL = "https://api.spotify.com/v1/albums"
TRACK_URL = "https://api.spotify.com/v1/tracks"

_access_token = None
_token_expires = 0


def get_access_token():
    global _access_token, _token_expires

    if _access_token and time.time() < _token_expires:
        return _access_token

    response = requests.post(
        TOKEN_URL,
        auth=(
            settings.spotify_client_id,
            settings.spotify_client_secret,
        ),
        data={
            "grant_type": "client_credentials"
        },
    )

    response.raise_for_status()

    data = response.json()

    _access_token = data["access_token"]
    _token_expires = time.time() + data["expires_in"] - 60

    return _access_token

def get_headers():
    return {
        "Authorization": f"Bearer {get_access_token()}"
    }

def search_track(query: str):
    response = requests.get(
        SEARCH_URL,
        headers=get_headers(),
        params={
            "q": query,
            "type": "track",
            "limit": 5,
        },
    )

    response.raise_for_status()

    return response.json()["tracks"]["items"]

def get_album(album_id: str):
    response = requests.get(
        f"{ALBUM_URL}/{album_id}",
        headers=get_headers(),
    )

    response.raise_for_status()

    return response.json()

def get_album_tracks(album_id: str):
    response = requests.get(
        f"{ALBUM_URL}/{album_id}/tracks",
        headers=get_headers(),
    )

    response.raise_for_status()

    return response.json()["items"]

def get_track(track_id: str):
    response = requests.get(
        f"{TRACK_URL}/{track_id}",
        headers=get_headers(),
    )

    response.raise_for_status()

    return response.json()    