import requests

from app.services.playlist_mirror.spotify_oauth import get_user_access_token


SPOTIFY_API = "https://api.spotify.com/v1"


def get_playlist_items(playlist_id: str) -> list[dict]:
    token = get_user_access_token()

    headers = {
        "Authorization": f"Bearer {token}"
    }

    url = f"{SPOTIFY_API}/playlists/{playlist_id}/items"

    params = {
        "limit": 50,
        "offset": 0,
    }

    results = []

    while True:
        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=30,
        )

        if not response.ok:
            print("Spotify response:")
            print(response.status_code)
            print(response.text)

        response.raise_for_status()

        data = response.json()

        for index, playlist_item in enumerate(data.get("items", [])):
            track = (
                playlist_item.get("item")
                or playlist_item.get("track")
            )

            if not track:
                continue

            artists = [
                artist["name"]
                for artist in track.get("artists", [])
            ]

            external_ids = track.get("external_ids") or {}

            results.append(
                {
                    "position": params["offset"] + index,
                    "spotify_id": track.get("id"),
                    "spotify_uri": track.get("uri"),
                    "title": track.get("name"),
                    "artists": artists,
                    "album": (track.get("album") or {}).get("name"),
                    "duration_ms": track.get("duration_ms"),
                    "isrc": external_ids.get("isrc"),
                    "added_at": playlist_item.get("added_at"),
                }
            )

        if not data.get("next"):
            break

        params["offset"] += params["limit"]

    return results
