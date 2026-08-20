from app.services.dropbox_service import (
    list_shared_folder_files,
)


IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


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
            item["file_name"].lower().endswith(ext)
            for ext in IMAGE_EXTENSIONS
        )
    ]

    preferred = [
        item
        for item in candidates
        if (
            "cover" in item["file_name"].lower()
            or "artwork" in item["file_name"].lower()
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

    # Keep the shared-folder URL as the source reference.
    # We do not overwrite release.artwork_url here because
    # that field needs a directly renderable image URL.

    return artwork
