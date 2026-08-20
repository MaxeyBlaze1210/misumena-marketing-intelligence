from app.models.asset import Asset
from app.services.dropbox_service import (
    list_shared_folder_files,
)


VIDEO_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".m4v",
}


def sync_music_video(
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
            for ext in VIDEO_EXTENSIONS
        )
    ]

    # Prefer filenames that explicitly identify the
    # release's full-length / YouTube video.
    preferred = [
        item
        for item in candidates
        if (
            "official video"
            in item["file_name"].lower()
            or "youtube"
            in item["file_name"].lower()
            or "visualizer"
            in item["file_name"].lower()
            or "music video"
            in item["file_name"].lower()
        )
    ]

    if len(preferred) == 1:
        video = preferred[0]

    elif len(candidates) == 1:
        video = candidates[0]

    else:
        names = ", ".join(
            item["file_name"]
            for item in candidates
        )

        raise RuntimeError(
            "Could not uniquely identify music video. "
            f"Candidates: {names}"
        )

    asset = (
        db.query(Asset)
        .filter(
            Asset.release_id == release.id,
            Asset.asset_type == "music_video",
        )
        .one_or_none()
    )

    if asset is None:
        asset = Asset(
            release_id=release.id,
            name=video["file_name"],
            asset_type="music_video",
            source="dropbox",
            source_id=video["dropbox_id"],
            source_url=release.promo_folder_url,
            file_name=video["file_name"],
            mime_type=video["mime_type"],
        )

        db.add(asset)

    else:
        asset.name = video["file_name"]
        asset.source = "dropbox"
        asset.source_id = video["dropbox_id"]
        asset.source_url = release.promo_folder_url
        asset.file_name = video["file_name"]
        asset.mime_type = video["mime_type"]

    db.commit()

    return asset
