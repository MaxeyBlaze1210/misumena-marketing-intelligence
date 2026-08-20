from app.services.asset_sync_service import (
    sync_dropbox_creatives,
)
from app.services.promo.artwork_sync import (
    sync_artwork,
)
from app.services.promo.music_video_sync import (
    sync_music_video,
)
from app.services.promo.promo_audio_sync import (
    sync_promo_audio,
)


def sync_release_promo_assets(
    db,
    release,
):
    results = {
        "artwork": None,
        "promo_audio": None,
        "music_video": None,
        "short_form_creatives": None,
        "errors": [],
    }

    try:
        results["artwork"] = sync_artwork(
            db,
            release,
        )
    except Exception as exc:
        results["errors"].append(
            f"Artwork: {exc}"
        )

    try:
        results["promo_audio"] = sync_promo_audio(
            db,
            release,
        )
    except Exception as exc:
        results["errors"].append(
            f"Audio master: {exc}"
        )

    try:
        results["music_video"] = sync_music_video(
            db,
            release,
        )
    except Exception as exc:
        results["errors"].append(
            f"Music video: {exc}"
        )

    try:
        results["short_form_creatives"] = (
            sync_dropbox_creatives(
                db,
                release_id=release.id,
                shared_folder_url=
                    release.promo_folder_url,
            )
        )
    except Exception as exc:
        results["errors"].append(
            f"Short-form creatives: {exc}"
        )

    return results
