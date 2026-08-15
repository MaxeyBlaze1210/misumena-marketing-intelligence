import sys

from app.services.dropbox_service import (
    list_shared_folder_videos,
)


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.research.test_dropbox_folder "
            "<dropbox-folder-url>"
        )
        raise SystemExit(1)

    folder_url = sys.argv[1]

    videos = list_shared_folder_videos(
        folder_url
    )

    print()
    print("=" * 70)
    print("DROPBOX VIDEOS")
    print("=" * 70)

    for video in videos:
        print(
            video["dropbox_id"],
            "|",
            video["file_name"],
            "|",
            video["size"],
        )

    print()
    print(
        f"{len(videos)} video files found."
    )


if __name__ == "__main__":
    main()