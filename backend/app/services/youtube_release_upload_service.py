import tempfile
from pathlib import Path

from app.models.asset import Asset
from app.services.dropbox_service import (
    download_shared_folder_asset,
)


def get_release_music_video(
    db,
    release,
) -> Asset:
    asset = (
        db.query(Asset)
        .filter(
            Asset.release_id == release.id,
            Asset.asset_type == "music_video",
        )
        .one_or_none()
    )

    if asset is None:
        raise RuntimeError(
            "No music_video asset is configured "
            f"for release {release.id}."
        )

    if asset.source != "dropbox":
        raise RuntimeError(
            "Current YouTube uploader only supports "
            "Dropbox-backed music videos."
        )

    if not asset.source_id:
        raise RuntimeError(
            "Music video asset has no Dropbox source ID."
        )

    if not release.promo_folder_url:
        raise RuntimeError(
            "Release has no Dropbox promo folder URL."
        )

    return asset


def download_release_music_video(
    db,
    release,
) -> tuple[str, Asset]:
    asset = get_release_music_video(
        db,
        release,
    )

    suffix = (
        Path(asset.file_name or asset.name)
        .suffix
        or ".mp4"
    )

    handle = tempfile.NamedTemporaryFile(
        prefix=f"mmi_youtube_{release.id}_",
        suffix=suffix,
        delete=False,
    )

    destination = handle.name
    handle.close()

    try:
        download_shared_folder_asset(
            shared_folder_url=
                release.promo_folder_url,
            dropbox_file_id=
                asset.source_id,
            destination_path=
                destination,
        )

        return destination, asset

    except Exception:
        Path(destination).unlink(
            missing_ok=True
        )
        raise
