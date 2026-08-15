from app.models.asset import Asset
from app.services.dropbox_service import (
    list_shared_folder_videos,
)


def sync_dropbox_creatives(
    db,
    release_id: int,
    shared_folder_url: str,
) -> dict:

    dropbox_files = list_shared_folder_videos(
        shared_folder_url
    )

    created = 0
    updated = 0

    assets = []

    for dropbox_file in dropbox_files:

        source_id = dropbox_file["dropbox_id"]
        file_name = dropbox_file["file_name"]

        asset = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id,
                Asset.source == "dropbox",
                Asset.source_id == source_id,
            )
            .one_or_none()
        )

        if asset is None:
            asset = Asset(
                release_id=release_id,
                name=file_name,
                asset_type="short_form_video",
                source="dropbox",
                source_id=source_id,
                source_url=shared_folder_url,
                file_name=file_name,
                mime_type=dropbox_file["mime_type"],
            )

            db.add(asset)

            created += 1

        else:
            asset.name = file_name
            asset.file_name = file_name
            asset.mime_type = dropbox_file["mime_type"]
            asset.source_url = shared_folder_url

            updated += 1

        assets.append(asset)

    db.commit()

    return {
        "found": len(dropbox_files),
        "created": created,
        "updated": updated,
        "assets": assets,
    }