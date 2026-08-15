import argparse
import subprocess

from app.services.playlist_mirror.compare_spotify_apple import (
    get_apple_tracks,
    score_match,
)
from app.services.playlist_mirror.spotify_reader import get_playlist_items


def run_applescript(script: str) -> str:
    result = subprocess.run(
        ["osascript"],
        input=script,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def find_extras(spotify_tracks, apple_tracks):
    unused_apple = set(range(len(apple_tracks)))

    for spotify_track in spotify_tracks:
        best_pos = None
        best_score = 0.0

        for apple_pos in unused_apple:
            score = score_match(
                spotify_track,
                apple_tracks[apple_pos],
            )

            if score > best_score:
                best_score = score
                best_pos = apple_pos

        if best_pos is not None and best_score >= 0.50:
            unused_apple.remove(best_pos)

    return sorted(unused_apple)


def delete_track_by_index(playlist_id: str, index: int):
    # AppleScript indexes are 1-based.
    apple_index = index + 1

    script = f'''
tell application "Music"
    set p to first user playlist whose persistent ID is "{playlist_id}"
    delete track {apple_index} of p
end tell
'''

    run_applescript(script)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("spotify_playlist_id")
    parser.add_argument("apple_playlist_id")
    parser.add_argument("apple_playlist_name")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually remove Apple-only tracks",
    )

    args = parser.parse_args()

    spotify_tracks = get_playlist_items(
        args.spotify_playlist_id
    )

    apple_tracks = get_apple_tracks(
        args.apple_playlist_name
    )

    extras = find_extras(
        spotify_tracks,
        apple_tracks,
    )

    print()
    print("=== APPLE PLAYLIST CLEANUP ===")
    print()
    print(
        f"Spotify tracks: {len(spotify_tracks)}"
    )
    print(
        f"Apple tracks:   {len(apple_tracks)}"
    )
    print()

    if not extras:
        print("No Apple-only tracks found.")
        return

    print("Apple-only tracks:")

    for pos in extras:
        track = apple_tracks[pos]

        print(
            f"  Apple {pos:03d}: "
            f"{track['artist']} — {track['title']}"
        )

    print()

    if not args.apply:
        print("DRY RUN — nothing changed.")
        print()
        print(
            "Run again with --apply to remove "
            "these tracks."
        )
        return

    print("Removing tracks...")

    # Delete backwards so earlier indexes don't move.
    for pos in sorted(extras, reverse=True):
        track = apple_tracks[pos]

        print(
            f"Removing Apple {pos:03d}: "
            f"{track['artist']} — {track['title']}"
        )

        delete_track_by_index(
            args.apple_playlist_id,
            pos,
        )

    print()
    print("Cleanup complete.")


if __name__ == "__main__":
    main()
