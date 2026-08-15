import sys

from app.services.playlist_mirror.spotify_reader import get_playlist_items


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m app.services.playlist_mirror.test_spotify_reader "
            "<spotify_playlist_id>"
        )
        raise SystemExit(1)

    tracks = get_playlist_items(sys.argv[1])

    print(f"\nFound {len(tracks)} tracks\n")

    for track in tracks:
        artists = ", ".join(track["artists"])
        print(
            f'{track["position"]:>3}  '
            f'{artists} — {track["title"]}'
        )
        print(f'     ISRC: {track["isrc"]}')


if __name__ == "__main__":
    main()
