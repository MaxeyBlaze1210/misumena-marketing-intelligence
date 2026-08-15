import re
import subprocess
import sys
import unicodedata

from app.services.playlist_mirror.spotify_reader import get_playlist_items


def normalize(value: str) -> str:
    value = value or ""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(c for c in value if not unicodedata.combining(c))
    value = value.lower()

    # Normalize some common Apple/Spotify presentation differences
    value = value.replace("&", " and ")
    value = re.sub(r"\bfeat\.?\b", " ", value)
    value = re.sub(r"\bfeaturing\b", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return " ".join(value.split())


def get_apple_tracks(playlist_name: str) -> list[dict]:
    safe_name = playlist_name.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
tell application "Music"
    set p to first user playlist whose name is "{safe_name}"
    set output to ""

    repeat with t in tracks of p
        try
            set trackName to name of t
        on error
            set trackName to ""
        end try

        try
            set trackArtist to artist of t
        on error
            set trackArtist to ""
        end try

        set output to output & trackArtist & tab & trackName & linefeed
    end repeat

    return output
end tell
'''

    result = subprocess.run(
        ["osascript"],
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )

    tracks = []

    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue

        artist, title = line.split("\t", 1)

        tracks.append(
            {
                "artist": artist.strip(),
                "title": title.strip(),
            }
        )

    return tracks


def similarity_key(title: str, artist: str) -> set[str]:
    return set(normalize(title + " " + artist).split())


def score_match(spotify_track: dict, apple_track: dict) -> float:
    spotify_artist = " ".join(spotify_track["artists"])
    spotify_words = similarity_key(
        spotify_track["title"],
        spotify_artist,
    )
    apple_words = similarity_key(
        apple_track["title"],
        apple_track["artist"],
    )

    if not spotify_words or not apple_words:
        return 0.0

    intersection = len(spotify_words & apple_words)
    union = len(spotify_words | apple_words)

    return intersection / union


def main():
    if len(sys.argv) != 3:
        print(
            "Usage: python -m "
            "app.services.playlist_mirror.compare_spotify_apple "
            "<spotify_playlist_id> <apple_playlist_name>"
        )
        raise SystemExit(1)

    spotify_playlist_id = sys.argv[1]
    apple_playlist_name = sys.argv[2]

    spotify = get_playlist_items(spotify_playlist_id)
    apple = get_apple_tracks(apple_playlist_name)

    print()
    print("=== PLAYLIST COMPARISON ===")
    print()
    print(f"Spotify: {len(spotify)} tracks")
    print(f"Apple:   {len(apple)} tracks")
    print()

    unused_apple = set(range(len(apple)))
    matches = []
    missing = []

    for s_pos, s in enumerate(spotify):
        best_pos = None
        best_score = 0.0

        for a_pos in unused_apple:
            score = score_match(s, apple[a_pos])

            if score > best_score:
                best_score = score
                best_pos = a_pos

        if best_pos is not None and best_score >= 0.50:
            unused_apple.remove(best_pos)

            matches.append(
                (s_pos, best_pos, best_score, s, apple[best_pos])
            )
        else:
            missing.append((s_pos, s))

    print("=== MATCHED ===")

    for s_pos, a_pos, score, s, a in matches:
        marker = "✓" if s_pos == a_pos else "↕"

        spotify_artist = ", ".join(s["artists"])

        print(
            f"{marker} Spotify {s_pos:03d} -> Apple {a_pos:03d} "
            f"[{score:.2f}] "
            f"{spotify_artist} — {s['title']}"
        )

    print()
    print("=== MISSING FROM APPLE ===")

    if not missing:
        print("None")
    else:
        for pos, track in missing:
            artists = ", ".join(track["artists"])
            print(
                f"Spotify {pos:03d}: "
                f"{artists} — {track['title']} "
                f"[ISRC {track['isrc']}]"
            )

    print()
    print("=== EXTRA IN APPLE ===")

    if not unused_apple:
        print("None")
    else:
        for pos in sorted(unused_apple):
            track = apple[pos]
            print(
                f"Apple {pos:03d}: "
                f"{track['artist']} — {track['title']}"
            )

    print()
    print(
        f"SUMMARY: {len(matches)} matched | "
        f"{len(missing)} missing | "
        f"{len(unused_apple)} extra"
    )


if __name__ == "__main__":
    main()
