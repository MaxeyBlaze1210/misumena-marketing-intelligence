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
        "promo_audio": None,
        "music_video": None,
        "errors": [],
    }

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

    return results
