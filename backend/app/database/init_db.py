from app.database.database import Base, SessionLocal, engine

# Core
from app.models.release import Release
from app.models.track import Track
from app.models.artist import Artist
from app.models.release_artist import ReleaseArtist
from app.models.playlist import Playlist
from app.models.playlist_landing_event import PlaylistLandingEvent

# YouTube
from app.models.youtube_video import YouTubeVideo
from app.models.youtube_metric import YouTubeMetric
from app.models.youtube_recommendation import YouTubeRecommendation

# Bandcamp
from app.models.bandcamp_sale import BandcampSale
from app.models.youtube_discovery_metric import (
    YouTubeDiscoveryMetric,
)

# Meta
from app.models.meta_interest import MetaInterest
from app.models.meta_campaign import MetaCampaign
from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_ad_action_metric import MetaAdActionMetric
from app.models.meta_ad_country_action_metric import (
    MetaAdCountryActionMetric,
)
from app.models.meta_creative import MetaCreative
from app.models.meta_audience import MetaAudience
from app.models.meta_audience_interest import MetaAudienceInterest
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_campaign_variant import MetaCampaignVariant
from app.models.meta_campaign_cell import MetaCampaignCell
from app.models.meta_campaign_variant_interest import (
    MetaCampaignVariantInterest,
)

# Historical Meta evidence
from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_targeting_item import (
    MetaAdSetTargetingItem,
)
from app.models.meta_adset_metric import MetaAdSetMetric

# Countries
from app.models.country import Country
from app.models.country_preset import CountryPreset
from app.models.country_preset_country import CountryPresetCountry
from app.models.meta_campaign_plan_country import MetaCampaignPlanCountry

# Promo / Contacts
from app.models.contact import Contact
from app.models.promo_campaign import PromoCampaign
from app.models.promo_recipient import PromoRecipient
from app.models.promo_click import PromoClick
from app.models.landing_event import LandingEvent

# Assets
from app.models.asset import Asset
from app.models.organic_asset_metric import OrganicAssetMetric
from app.models.meta_campaign_plan_asset import (
    MetaCampaignPlanAsset,
)

# Spotify popularity history

from app.models.spotify_popularity_snapshot import (
    SpotifyPopularitySnapshot,
)


def init_db():
    Base.metadata.create_all(
        bind=engine
    )

    # Existing SQLite databases need the new Playlist column
    # before any ORM query against Playlist is executed.
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            playlist_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(playlists)"
                )
            }

            if "promo_folder_url" not in playlist_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE playlists "
                    "ADD COLUMN promo_folder_url VARCHAR"
                )

    # Seed artist-owned / artist-catalog playlist records.
    db = SessionLocal()
    try:
        spotify_playlist_id = "37i9dQZF1DZ06evO0OzFqe"

        playlist = (
            db.query(Playlist)
            .filter(
                Playlist.spotify_playlist_id
                == spotify_playlist_id
            )
            .one_or_none()
        )

        if playlist is None:
            db.add(
                Playlist(
                    name="This Is Misumena",
                    platform="Spotify",
                    spotify_playlist_id=spotify_playlist_id,
                    spotify_url=(
                        "https://open.spotify.com/playlist/"
                        + spotify_playlist_id
                    ),
                    description=(
                        "Spotify-generated Misumena catalog playlist."
                    ),
                    playlist_type="artist_catalog",
                )
            )
            db.commit()
    finally:
        db.close()

    if engine.dialect.name == "sqlite":
        # Existing production tables predate playlist-owned
        # campaigns/assets. SQLite cannot directly remove a
        # NOT NULL constraint, so the two affected tables are
        # rebuilt once while preserving IDs and existing data.

        with engine.connect() as connection:
            connection.exec_driver_sql(
                "PRAGMA foreign_keys=OFF"
            )
            connection.commit()

            with connection.begin():

                # ---------------------------------------------
                # assets
                # ---------------------------------------------

                asset_columns = {
                    row[1]: row
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info(assets)"
                    )
                }

                asset_release_not_null = (
                    asset_columns.get("release_id", [None] * 4)[3]
                    == 1
                )

                if (
                    "playlist_id" not in asset_columns
                    or asset_release_not_null
                ):
                    connection.exec_driver_sql(
                        "DROP TABLE IF EXISTS assets_new"
                    )

                    connection.exec_driver_sql(
                        """
                        CREATE TABLE assets_new (
                            id INTEGER NOT NULL PRIMARY KEY,
                            release_id INTEGER,
                            playlist_id INTEGER,
                            name VARCHAR NOT NULL,
                            asset_type VARCHAR NOT NULL,
                            source VARCHAR,
                            source_id VARCHAR,
                            source_url VARCHAR,
                            file_name VARCHAR,
                            mime_type VARCHAR,
                            youtube_video_id VARCHAR,
                            youtube_url VARCHAR,
                            youtube_privacy_status VARCHAR,
                            youtube_uploaded_at DATETIME,
                            created_at DATETIME NOT NULL,
                            FOREIGN KEY(release_id)
                                REFERENCES releases (id),
                            FOREIGN KEY(playlist_id)
                                REFERENCES playlists (id)
                        )
                        """
                    )

                    connection.exec_driver_sql(
                        """
                        INSERT INTO assets_new (
                            id,
                            release_id,
                            playlist_id,
                            name,
                            asset_type,
                            source,
                            source_id,
                            source_url,
                            file_name,
                            mime_type,
                            youtube_video_id,
                            youtube_url,
                            youtube_privacy_status,
                            youtube_uploaded_at,
                            created_at
                        )
                        SELECT
                            id,
                            release_id,
                            NULL,
                            name,
                            asset_type,
                            source,
                            source_id,
                            source_url,
                            file_name,
                            mime_type,
                            youtube_video_id,
                            youtube_url,
                            youtube_privacy_status,
                            youtube_uploaded_at,
                            created_at
                        FROM assets
                        """
                    )

                    connection.exec_driver_sql(
                        "DROP TABLE assets"
                    )

                    connection.exec_driver_sql(
                        "ALTER TABLE assets_new "
                        "RENAME TO assets"
                    )

                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_id ON assets (id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_release_id "
                    "ON assets (release_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_playlist_id "
                    "ON assets (playlist_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_asset_type "
                    "ON assets (asset_type)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_source_id "
                    "ON assets (source_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_assets_youtube_video_id "
                    "ON assets (youtube_video_id)"
                )

                # ---------------------------------------------
                # meta_campaign_plans
                # ---------------------------------------------

                plan_columns = {
                    row[1]: row
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info(meta_campaign_plans)"
                    )
                }

                plan_release_not_null = (
                    plan_columns.get(
                        "release_id",
                        [None] * 4,
                    )[3]
                    == 1
                )

                if (
                    "playlist_id" not in plan_columns
                    or plan_release_not_null
                ):
                    connection.exec_driver_sql(
                        "DROP TABLE IF EXISTS "
                        "meta_campaign_plans_new"
                    )

                    connection.exec_driver_sql(
                        """
                        CREATE TABLE meta_campaign_plans_new (
                            id INTEGER NOT NULL PRIMARY KEY,
                            release_id INTEGER,
                            playlist_id INTEGER,
                            meta_audience_id INTEGER NOT NULL,
                            objective VARCHAR NOT NULL,
                            optimization_goal VARCHAR NOT NULL,
                            conversion_event VARCHAR NOT NULL,
                            meta_pixel_id VARCHAR,
                            destination_url VARCHAR,
                            call_to_action VARCHAR NOT NULL,
                            country_preset VARCHAR,
                            total_budget NUMERIC(10, 2),
                            stage_1_cell_budget NUMERIC(10, 2),
                            status VARCHAR NOT NULL,
                            created_at DATETIME NOT NULL,
                            updated_at DATETIME NOT NULL,
                            meta_campaign_record_id INTEGER UNIQUE,
                            country_preset_id INTEGER,
                            age_min INTEGER NOT NULL,
                            age_max INTEGER NOT NULL,
                            campaign_type VARCHAR NOT NULL,
                            start_date DATE,
                            end_date DATE,
                            FOREIGN KEY(release_id)
                                REFERENCES releases (id),
                            FOREIGN KEY(playlist_id)
                                REFERENCES playlists (id),
                            FOREIGN KEY(meta_audience_id)
                                REFERENCES audience_families (id),
                            FOREIGN KEY(meta_campaign_record_id)
                                REFERENCES meta_campaigns (id),
                            FOREIGN KEY(country_preset_id)
                                REFERENCES country_presets (id)
                        )
                        """
                    )

                    connection.exec_driver_sql(
                        """
                        INSERT INTO meta_campaign_plans_new (
                            id,
                            release_id,
                            playlist_id,
                            meta_audience_id,
                            objective,
                            optimization_goal,
                            conversion_event,
                            meta_pixel_id,
                            destination_url,
                            call_to_action,
                            country_preset,
                            total_budget,
                            stage_1_cell_budget,
                            status,
                            created_at,
                            updated_at,
                            meta_campaign_record_id,
                            country_preset_id,
                            age_min,
                            age_max,
                            campaign_type,
                            start_date,
                            end_date
                        )
                        SELECT
                            id,
                            release_id,
                            NULL,
                            meta_audience_id,
                            objective,
                            optimization_goal,
                            conversion_event,
                            meta_pixel_id,
                            destination_url,
                            call_to_action,
                            country_preset,
                            total_budget,
                            stage_1_cell_budget,
                            status,
                            created_at,
                            updated_at,
                            meta_campaign_record_id,
                            country_preset_id,
                            age_min,
                            age_max,
                            campaign_type,
                            start_date,
                            end_date
                        FROM meta_campaign_plans
                        """
                    )

                    connection.exec_driver_sql(
                        "DROP TABLE meta_campaign_plans"
                    )

                    connection.exec_driver_sql(
                        "ALTER TABLE "
                        "meta_campaign_plans_new "
                        "RENAME TO meta_campaign_plans"
                    )

                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_meta_campaign_plans_id "
                    "ON meta_campaign_plans (id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_meta_campaign_plans_release_id "
                    "ON meta_campaign_plans (release_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_meta_campaign_plans_playlist_id "
                    "ON meta_campaign_plans (playlist_id)"
                )
                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_meta_campaign_plans_meta_audience_id "
                    "ON meta_campaign_plans (meta_audience_id)"
                )

                # ---------------------------------------------
                # meta_campaigns
                # ---------------------------------------------

                campaign_columns = {
                    row[1]
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info(meta_campaigns)"
                    )
                }

                if "playlist_id" not in campaign_columns:
                    connection.exec_driver_sql(
                        "ALTER TABLE meta_campaigns "
                        "ADD COLUMN playlist_id INTEGER "
                        "REFERENCES playlists(id)"
                    )

                connection.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS "
                    "ix_meta_campaigns_playlist_id "
                    "ON meta_campaigns (playlist_id)"
                )

                # Existing small additive migrations.
                plan_asset_columns = {
                    row[1]
                    for row in connection.exec_driver_sql(
                        "PRAGMA table_info("
                        "meta_campaign_plan_assets)"
                    )
                }

                if (
                    "meta_effective_object_story_id"
                    not in plan_asset_columns
                ):
                    connection.exec_driver_sql(
                        "ALTER TABLE "
                        "meta_campaign_plan_assets "
                        "ADD COLUMN "
                        "meta_effective_object_story_id "
                        "VARCHAR"
                    )

                if (
                    "instagram_permalink_url"
                    not in plan_asset_columns
                ):
                    connection.exec_driver_sql(
                        "ALTER TABLE "
                        "meta_campaign_plan_assets "
                        "ADD COLUMN "
                        "instagram_permalink_url TEXT"
                    )

            connection.exec_driver_sql(
                "PRAGMA foreign_keys=ON"
            )
            connection.commit()

            violations = list(
                connection.exec_driver_sql(
                    "PRAGMA foreign_key_check"
                )
            )

            if violations:
                raise RuntimeError(
                    "Foreign-key violations after "
                    f"playlist ownership migration: {violations}"
                )


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
