import mimetypes

import dropbox
from dropbox.files import FileMetadata, SharedLink

from app.core.config import settings


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
    ".webm",
}


def get_dropbox_client() -> dropbox.Dropbox:
    if (
        settings.dropbox_refresh_token
        and settings.dropbox_app_key
    ):
        return dropbox.Dropbox(
            oauth2_refresh_token=
                settings.dropbox_refresh_token,
            app_key=
                settings.dropbox_app_key,
            app_secret=
                settings.dropbox_app_secret,
        )

    if settings.dropbox_access_token:
        return dropbox.Dropbox(
            oauth2_access_token=
                settings.dropbox_access_token,
        )

    raise RuntimeError(
        "Dropbox authentication is not configured."
    )


def list_shared_folder_files(
    shared_folder_url: str,
) -> list[dict]:
    dbx = get_dropbox_client()

    shared_link = SharedLink(
        url=shared_folder_url
    )

    result = dbx.files_list_folder(
        path="",
        recursive=False,
        shared_link=shared_link,
    )

    entries = list(result.entries)

    while result.has_more:
        result = dbx.files_list_folder_continue(
            result.cursor
        )
        entries.extend(result.entries)

    files = []

    for entry in entries:
        if not isinstance(entry, FileMetadata):
            continue

        file_name = entry.name

        mime_type, _ = mimetypes.guess_type(
            file_name
        )

        files.append(
            {
                "dropbox_id": entry.id,
                "name": file_name,
                "file_name": file_name,
                "mime_type": mime_type,
                "size": entry.size,
                "path_lower": entry.path_lower,
            }
        )

    return files


def list_shared_folder_videos(
    shared_folder_url: str,
) -> list[dict]:
    files = list_shared_folder_files(
        shared_folder_url
    )

    videos = []

    for item in files:
        file_name = item["file_name"].lower()

        if any(
            file_name.endswith(extension)
            for extension in VIDEO_EXTENSIONS
        ):
            videos.append(item)

    return videos

def download_shared_folder_asset(
    shared_folder_url: str,
    dropbox_file_id: str,
    destination_path: str,
) -> str:
    """
    Download an asset that MMI discovered through a
    Dropbox shared-folder link.

    The stored Dropbox ID identifies the desired file.
    The actual download is performed through the shared
    link using the file's relative path.
    """

    if not shared_folder_url:
        raise ValueError(
            "Dropbox shared-folder URL is required."
        )

    if not dropbox_file_id:
        raise ValueError(
            "Dropbox file ID is required."
        )

    files = list_shared_folder_files(
        shared_folder_url
    )

    matching = next(
        (
            item
            for item in files
            if item["dropbox_id"]
            == dropbox_file_id
        ),
        None,
    )

    if matching is None:
        raise RuntimeError(
            "Dropbox asset was not found "
            "in its shared folder."
        )

    relative_path = matching[
        "path_lower"
    ]

    if not relative_path:
        raise RuntimeError(
            "Dropbox asset has no relative path."
        )

    dbx = get_dropbox_client()

    metadata, response = (
        dbx.sharing_get_shared_link_file(
            url=shared_folder_url,
            path=relative_path,
        )
    )

    try:
        with open(
            destination_path,
            "wb",
        ) as handle:
            handle.write(
                response.content
            )

    finally:
        response.close()

    return destination_path
