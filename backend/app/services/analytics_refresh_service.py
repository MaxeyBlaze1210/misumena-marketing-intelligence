from app.importers.meta_importer import import_meta_campaign_country_metrics
from datetime import date

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.importers.meta_importer import (
    import_meta_campaign,
)
from app.importers.youtube_import import (
    import_youtube_release,
)
from app.importers.youtube_history_import import (
    replace_discovery,
)
from app.models.meta_campaign import MetaCampaign
from app.models.release import Release
from app.models.playlist import Playlist
from app.models.youtube_video import YouTubeVideo


def refresh_release_analytics(
    release_id: int,
) -> dict:
    db = SessionLocal()

    try:
        release = db.get(
            Release,
            release_id,
        )

        if release is None:
            raise RuntimeError(
                f"Release {release_id} not found."
            )

        meta_campaign_ids = [
            row.meta_campaign_id
            for row in (
                db.query(MetaCampaign)
                .filter(
                    MetaCampaign.release_id
                    == release_id
                )
                .all()
            )
        ]

        has_youtube = bool(
            release.youtube_url
        )

    finally:
        db.close()

    meta_refreshed = 0
    country_rows_imported = 0

    for campaign_id in meta_campaign_ids:
        import_meta_campaign(
            campaign_id=campaign_id,
            release_id=release_id,
        )

        country_rows_imported += (
            import_meta_campaign_country_metrics(
                campaign_id=campaign_id,
            )
        )

        meta_refreshed += 1

    youtube_result = None
    youtube_discovery = None

    if has_youtube:
        youtube_result = (
            import_youtube_release(
                release_id
            )
        )

        db = SessionLocal()

        try:
            release = db.get(
                Release,
                release_id,
            )

            video = (
                db.query(YouTubeVideo)
                .filter(
                    YouTubeVideo.release_id
                    == release_id
                )
                .order_by(
                    YouTubeVideo.published_at.desc()
                )
                .first()
            )

            if video is not None:
                youtube_discovery = (
                    replace_discovery(
                        db,
                        video,
                        release.release_date,
                        date.today(),
                    )
                )

                db.commit()

        except Exception:
            db.rollback()
            raise

        finally:
            db.close()

    return {
        "release_id": release_id,
        "meta_campaigns":
            meta_refreshed,
        "country_rows":
            country_rows_imported,
        "youtube":
            youtube_result,
        "youtube_discovery":
            youtube_discovery,
    }



def refresh_playlist_analytics(
    playlist_id: int,
) -> dict:
    db = SessionLocal()

    try:
        playlist = db.get(
            Playlist,
            playlist_id,
        )

        if playlist is None:
            raise RuntimeError(
                f"Playlist {playlist_id} not found."
            )

        meta_campaign_ids = [
            row.meta_campaign_id
            for row in (
                db.query(MetaCampaign)
                .filter(
                    MetaCampaign.playlist_id
                    == playlist_id
                )
                .all()
            )
            if row.meta_campaign_id
        ]

    finally:
        db.close()

    meta_refreshed = 0
    country_rows_imported = 0

    for campaign_id in meta_campaign_ids:
        import_meta_campaign(
            campaign_id=campaign_id,
            playlist_id=playlist_id,
        )

        country_rows_imported += (
            import_meta_campaign_country_metrics(
                campaign_id=campaign_id,
            )
        )

        meta_refreshed += 1

    return {
        "playlist_id": playlist_id,
        "meta_campaigns": meta_refreshed,
        "country_rows": country_rows_imported,
    }
