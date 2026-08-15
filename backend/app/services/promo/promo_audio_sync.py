from app.models.asset import Asset
from app.services.dropbox_service import (
    get_dropbox_client,
    list_shared_folder_files,
)


AUDIO_EXTENSIONS = {
    ".wav",
    ".wave",
}


def get_or_create_file_link(
    path_lower: str,
) -> str:
    dbx = get_dropbox_client()

    existing = dbx.sharing_list_shared_links(
        path=path_lower,
        direct_only=True,
    )

    if existing.links:
        return existing.links[0].url

    created = (
        dbx.sharing_create_shared_link_with_settings(
            path_lower
        )
    )

    return created.url


def sync_promo_audio(
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

    wav_files = [
        item
        for item in files
        if any(
            item["file_name"].lower().endswith(ext)
            for ext in AUDIO_EXTENSIONS
        )
    ]

    if not wav_files:
        raise RuntimeError(
            "No WAV file found in promo folder."
        )

    if len(wav_files) > 1:
        names = ", ".join(
            item["file_name"]
            for item in wav_files
        )

        raise RuntimeError(
            f"Multiple WAV files found: {names}"
        )

    wav = wav_files[0]

    file_url = get_or_create_file_link(
        wav["path_lower"]
    )

    asset = (
        db.query(Asset)
        .filter(
            Asset.release_id == release.id,
            Asset.asset_type == "promo_audio",
        )
        .one_or_none()
    )

    if asset is None:
        asset = Asset(
            release_id=release.id,
            name=wav["file_name"],
            asset_type="promo_audio",
            source="dropbox",
            source_id=wav["dropbox_id"],
            source_url=file_url,
            file_name=wav["file_name"],
            mime_type=wav["mime_type"],
        )

        db.add(asset)

    else:
        asset.name = wav["file_name"]
        asset.source = "dropbox"
        asset.source_id = wav["dropbox_id"]
        asset.source_url = file_url
        asset.file_name = wav["file_name"]
        asset.mime_type = wav["mime_type"]

    db.commit()

    return asset
