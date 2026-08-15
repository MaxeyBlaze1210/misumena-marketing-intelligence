from app.services.playlist_mirror.spotify_reader import get_playlist_items
from app.services.playlist_mirror.compare_spotify_apple import (
    get_apple_tracks,
    score_match,
)
from app.services.playlist_mirror.rebuild_apple_playlist import (
    build_match_plan,
    rebuild_playlist,
)


PLAYLISTS = [
    {
        "name": "Light up your day",
        "spotify_id": "4ZF5vXUdRU4Ocev5sfzkQp",
        "apple_id": "335284DC4891CF25",
    },
    {
        "name": "Dance Groove Repeat",
        "spotify_id": "046qaNH5CuEcNeI7w5JLqY",
        "apple_id": "DC01151C2BC071B6",
    },
    {
        "name": "Roots & Chill",
        "spotify_id": "6yppNnxoQW5rYnU7igzL09",
        "apple_id": "5E459C828A15B962",
    },
]


def compare(spotify, apple):
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
                (s_pos, best_pos, best_score)
            )
        else:
            missing.append((s_pos, s))

    extras = sorted(unused_apple)

    apple_positions = [
        a_pos
        for _, a_pos, _ in matches
    ]

    ordered = (
        apple_positions
        == sorted(apple_positions)
    )

    return matches, missing, extras, ordered


def check_playlist(config):
    spotify = get_playlist_items(
        config["spotify_id"]
    )

    apple = get_apple_tracks(
        config["name"]
    )

    matches, missing, extras, ordered = compare(
        spotify,
        apple,
    )

    return {
        "config": config,
        "spotify": spotify,
        "apple": apple,
        "matches": matches,
        "missing": missing,
        "extras": extras,
        "ordered": ordered,
    }


def sync_playlist(config):
    before = check_playlist(config)

    needs_rebuild = (
        not before["ordered"]
        or bool(before["extras"])
    )

    if not needs_rebuild:
        return {
            "name": config["name"],
            "changed": False,
            "matched": len(before["matches"]),
            "missing": len(before["missing"]),
            "extras_removed": 0,
            "message": "Already synchronized",
        }

    plan, missing, extras = build_match_plan(
        before["spotify"],
        before["apple"],
    )

    result = rebuild_playlist(
        config["apple_id"],
        config["name"],
        plan,
    )

    after = check_playlist(config)

    if not after["ordered"]:
        raise RuntimeError(
            f"{config['name']}: order verification failed after rebuild"
        )

    if after["extras"]:
        raise RuntimeError(
            f"{config['name']}: Apple-only tracks remain after rebuild"
        )

    return {
        "name": config["name"],
        "changed": True,
        "matched": len(after["matches"]),
        "missing": len(after["missing"]),
        "extras_removed": len(extras),
        "message": result,
    }


def sync_all_playlists():
    results = []

    for config in PLAYLISTS:
        results.append(
            sync_playlist(config)
        )

    return results


def main():
    print()
    print("=== MMI PLAYLIST MIRROR ===")
    print()

    all_clean = True

    for config in PLAYLISTS:
        name = config["name"]

        print(name)
        print("-" * len(name))

        try:
            state = check_playlist(config)

            spotify = state["spotify"]
            apple = state["apple"]
            matches = state["matches"]
            missing = state["missing"]
            extras = state["extras"]
            ordered = state["ordered"]

            print(f"Spotify: {len(spotify)}")
            print(f"Apple:   {len(apple)}")
            print(f"Matched: {len(matches)}")
            print(f"Missing: {len(missing)}")
            print(f"Extras:  {len(extras)}")

            if ordered:
                print(
                    "Order:   ✓ correct relative Spotify order"
                )
            else:
                print(
                    "Order:   ✗ differs from Spotify"
                )
                all_clean = False

            if extras:
                all_clean = False

                print()
                print("Apple-only tracks:")

                for pos in extras:
                    t = apple[pos]
                    print(
                        f"  Apple {pos:03d}: "
                        f"{t['artist']} — {t['title']}"
                    )

            if missing:
                print()
                print("Missing from Apple:")

                for pos, t in missing:
                    artists = ", ".join(
                        t["artists"]
                    )

                    print(
                        f"  Spotify {pos:03d}: "
                        f"{artists} — {t['title']}"
                    )

            print()

        except Exception as exc:
            all_clean = False
            print(f"ERROR: {exc}")
            print()

    print("=== RESULT ===")

    if all_clean:
        print(
            "✓ All Apple playlists preserve "
            "Spotify relative ordering."
        )
    else:
        print(
            "⚠ One or more playlists need reconciliation."
        )

    print()


if __name__ == "__main__":
    main()
