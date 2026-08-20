from urllib.parse import (
    parse_qsl,
    urlencode,
    urlsplit,
    urlunsplit,
)

from app.services.promo.promo_audio_sync import (
    get_or_create_file_link,
)
from app.services.dropbox_service import (
    list_shared_folder_files,
)


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def make_direct_image_url(
    shared_url: str,
) -> str:
    parts = urlsplit(shared_url)

    query = dict(
        parse_qsl(
            parts.query,
            keep_blank_values=True,
        )
    )

    query.pop("dl", None)
    query["raw"] = "1"

    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urlencode(query),
            parts.fragment,
        )
    )


def sync_artwork(
    db,
    release,
):
    if not release.promo_folder_url:
        raise RuntimeError(
            "Release has no promo_folder_url."
        )

    files = list_shared_folder_files(
        release.promo_folder_url
    )

    candidates = [
        item
        for item in files
        if any(
            item["file_name"]
            .lower()
            .endswith(ext)
            for ext in IMAGE_EXTENSIONS
        )
    ]

    preferred = [
        item
        for item in candidates
        if (
            "cover"
            in item["file_name"].lower()
            or "artwork"
            in item["file_name"].lower()
        )
    ]

    if len(preferred) == 1:
        artwork = preferred[0]

    elif len(candidates) == 1:
        artwork = candidates[0]

    else:
        names = ", ".join(
            item["file_name"]
            for item in candidates
        )

        raise RuntimeError(
            "Could not uniquely identify artwork. "
            f"Candidates: {names}"
        )

    shared_url = get_or_create_file_link(
        artwork["path_lower"]
    )

    direct_url = make_direct_image_url(
        shared_url
    )

    release.artwork_url = direct_url

    db.commit()

    return {
        "file_name":
            artwork["file_name"],
        "dropbox_id":
            artwork["dropbox_id"],
        "artwork_url":
            direct_url,
    }
