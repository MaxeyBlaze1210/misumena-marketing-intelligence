from app.models.asset import Asset


def get_release_links(db, release):
    promo_audio = (
        db.query(Asset)
        .filter(
            Asset.release_id == release.id,
            Asset.asset_type == "promo_audio",
            Asset.source == "dropbox",
            Asset.source_url.isnot(None),
        )
        .first()
    )

    return {
        "spotify": release.spotify_url,
        "apple_music": release.apple_music_url,
        "youtube": release.youtube_url,
        "dropbox": (
            promo_audio.source_url
            if promo_audio
            else None
        ),
    }
