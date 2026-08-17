from pathlib import Path

from googleapiclient.http import MediaFileUpload

from app.services.youtube_service import get_youtube_client
from app.services.youtube_video_prepare_service import (
    prepare_video_for_youtube,
)


def upload_video(
    file_path: str,
    title: str,
    description: str = "",
    privacy_status: str = "private",
) -> dict:
    """
    Upload one local video file to the authenticated
    YouTube channel.

    The default visibility is deliberately private.
    """

    path = Path(file_path)

    if not path.is_file():
        raise FileNotFoundError(
            f"Video file does not exist: {path}"
        )

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        raise ValueError(
            "privacy_status must be private, unlisted, or public."
        )

    youtube = get_youtube_client()

    prepared_path = None
    created_prepared_file = False

    try:
        prepared_path, created_prepared_file = (
            prepare_video_for_youtube(
                str(path)
            )
        )

        media = MediaFileUpload(
            str(prepared_path),
            chunksize=8 * 1024 * 1024,
            resumable=True,
        )

        request = youtube.videos().insert(
        part="snippet,status",
        body={
            "snippet": {
                "title": title,
                "description": description,
                "categoryId": "10",
            },
            "status": {
                "privacyStatus": privacy_status,
            },
        },
        media_body=media,
    )

        response = None

        while response is None:
            status, response = request.next_chunk()

            if status:
                print(
                    f"YouTube upload: "
                    f"{int(status.progress() * 100)}%"
                )

        video_id = response["id"]

        return {
            "video_id": video_id,
            "youtube_url": (
                f"https://www.youtube.com/watch?v={video_id}"
            ),
            "title": response.get(
                "snippet",
                {},
            ).get("title", title),
            "privacy_status": response.get(
                "status",
                {},
            ).get(
                "privacyStatus",
                privacy_status,
            ),
        }

    finally:
        if (
            created_prepared_file
            and prepared_path
        ):
            Path(prepared_path).unlink(
                missing_ok=True
            )


def update_video_privacy(
    video_id: str,
    privacy_status: str,
) -> dict:
    """
    Change visibility of an existing YouTube video.
    """

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        raise ValueError(
            "privacy_status must be private, "
            "unlisted, or public."
        )

    if not video_id:
        raise ValueError(
            "YouTube video ID is required."
        )

    youtube = get_youtube_client()

    response = youtube.videos().update(
        part="status",
        body={
            "id": video_id,
            "status": {
                "privacyStatus": privacy_status,
            },
        },
    ).execute()

    actual_status = (
        response.get("status", {})
        .get(
            "privacyStatus",
            privacy_status,
        )
    )

    return {
        "video_id": video_id,
        "privacy_status": actual_status,
        "youtube_url": (
            f"https://www.youtube.com/watch?v="
            f"{video_id}"
        ),
    }
