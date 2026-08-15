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


def build_match_plan(spotify_tracks, apple_tracks):
    unused_apple = set(range(len(apple_tracks)))
    plan = []
    missing = []

    for s_pos, s in enumerate(spotify_tracks):
        best_pos = None
        best_score = 0.0

        for a_pos in unused_apple:
            score = score_match(s, apple_tracks[a_pos])

            if score > best_score:
                best_score = score
                best_pos = a_pos

        if best_pos is not None and best_score >= 0.50:
            unused_apple.remove(best_pos)

            plan.append(
                {
                    "spotify_pos": s_pos,
                    "apple_pos": best_pos,
                    "score": best_score,
                    "spotify": s,
                    "apple": apple_tracks[best_pos],
                }
            )
        else:
            missing.append(
                {
                    "spotify_pos": s_pos,
                    "spotify": s,
                }
            )

    return plan, missing, sorted(unused_apple)


def rebuild_playlist(
    playlist_id: str,
    playlist_name: str,
    plan: list[dict],
):
    backup_name = f"{playlist_name} [MMI BACKUP]"
    temp_name = "__MMI_REBUILD_REAL__"

    source_indexes = [item["apple_pos"] + 1 for item in plan]
    index_list = ", ".join(str(i) for i in source_indexes)

    script = f'''
tell application "Music"
    set sourcePlaylist to first user playlist whose persistent ID is "{playlist_id}"

    -- Clean stale helper playlists
    try
        delete (first user playlist whose name is "{backup_name}")
    end try

    try
        delete (first user playlist whose name is "{temp_name}")
    end try

    -- Backup source by explicit numeric index
    set backupPlaylist to make new user playlist with properties {{name:"{backup_name}"}}

    set sourceCount to count of tracks of sourcePlaylist
    repeat with i from 1 to sourceCount
        duplicate track i of sourcePlaylist to backupPlaylist
    end repeat

    -- Verify backup before touching source
    if (count of tracks of backupPlaylist) is not sourceCount then
        error "Backup verification failed"
    end if

    -- Build exact target order in temporary playlist
    set rebuiltPlaylist to make new user playlist with properties {{name:"{temp_name}"}}
    set wantedIndexes to {{{index_list}}}

    repeat with idx in wantedIndexes
        duplicate track idx of sourcePlaylist to rebuiltPlaylist
    end repeat

    if (count of tracks of rebuiltPlaylist) is not (count of wantedIndexes) then
        error "Temporary rebuild verification failed"
    end if

    -- Only now clear the original
    repeat with i from (count of tracks of sourcePlaylist) to 1 by -1
        delete track i of sourcePlaylist
    end repeat

    -- Copy rebuilt order back by explicit index
    set rebuiltCount to count of tracks of rebuiltPlaylist

    repeat with i from 1 to rebuiltCount
        duplicate track i of rebuiltPlaylist to sourcePlaylist
    end repeat

    if (count of tracks of sourcePlaylist) is not rebuiltCount then
        error "Final playlist verification failed"
    end if

    delete rebuiltPlaylist

    return "Backup tracks=" & (count of tracks of backupPlaylist) & " | Final tracks=" & (count of tracks of sourcePlaylist)
end tell
'''

    return run_applescript(script)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("spotify_playlist_id")
    parser.add_argument("apple_playlist_id")
    parser.add_argument("apple_playlist_name")

    parser.add_argument(
        "--apply",
        action="store_true",
    )

    args = parser.parse_args()

    spotify_tracks = get_playlist_items(
        args.spotify_playlist_id
    )

    apple_tracks = get_apple_tracks(
        args.apple_playlist_name
    )

    plan, missing, extras = build_match_plan(
        spotify_tracks,
        apple_tracks,
    )

    print()
    print("=== REBUILD PLAN ===")
    print()
    print(f"Spotify tracks: {len(spotify_tracks)}")
    print(f"Apple tracks:   {len(apple_tracks)}")
    print(f"Matched:        {len(plan)}")
    print(f"Missing:        {len(missing)}")
    print(f"Extras:         {len(extras)}")
    print()

    if extras:
        print("WARNING: Apple extras still exist:")
        for pos in extras:
            t = apple_tracks[pos]
            print(
                f"  Apple {pos:03d}: "
                f"{t['artist']} — {t['title']}"
            )
        print()

    if not args.apply:
        print("DRY RUN — nothing changed.")
        return

    result = rebuild_playlist(
        args.apple_playlist_id,
        args.apple_playlist_name,
        plan,
    )

    print()
    print(result)
    print("Rebuild complete.")


if __name__ == "__main__":
    main()
