from datetime import date, timedelta
from urllib.parse import urlparse, parse_qs

# Register all SQLAlchemy models before querying.
# This is required when the importer runs standalone,
# because Release has relationships to other model classes.
import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.models.release import Release
from app.models.youtube_video import YouTubeVideo
from app.models.youtube_metric import YouTubeMetric
from app.services.youtube_service import get_youtube_client
from app.services.youtube_analytics_service import (
    get_youtube_analytics_client,
)


def extract_youtube_video_id(url: str) -> str:
    if not url:
        raise ValueError("YouTube URL is required.")

    parsed = urlparse(url)

    # https://youtu.be/VIDEO_ID
    if parsed.netloc in {
        "youtu.be",
        "www.youtu.be",
    }:
        video_id = parsed.path.strip("/")

        if video_id:
            return video_id

    # https://www.youtube.com/watch?v=VIDEO_ID
    if parsed.netloc in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
    }:
        query = parse_qs(parsed.query)
        values = query.get("v")

        if values:
            return values[0]

        # /shorts/VIDEO_ID or /embed/VIDEO_ID
        parts = [
            part
            for part in parsed.path.split("/")
            if part
        ]

        if (
            len(parts) >= 2
            and parts[0] in {
                "shorts",
                "embed",
            }
        ):
            return parts[1]

    raise ValueError(
        f"Could not extract YouTube video ID from: {url}"
    )


def get_video_metadata(
    youtube_video_id: str,
) -> dict:
    youtube = get_youtube_client()

    response = (
        youtube.videos()
        .list(
            part="snippet",
            id=youtube_video_id,
        )
        .execute()
    )

    items = response.get("items", [])

    if not items:
        raise RuntimeError(
            f"YouTube video {youtube_video_id} not found."
        )

    snippet = items[0]["snippet"]

    thumbnails = snippet.get(
        "thumbnails",
        {}
    )

    thumbnail_url = None

    for key in (
        "maxres",
        "standard",
        "high",
        "medium",
        "default",
    ):
        item = thumbnails.get(key)

        if item and item.get("url"):
            thumbnail_url = item["url"]
            break

    return {
        "youtube_video_id":
            youtube_video_id,

        "title":
            snippet.get("title"),

        "published_at":
            snippet.get("publishedAt"),

        "thumbnail_url":
            thumbnail_url,
    }


def get_daily_video_analytics(
    youtube_video_id: str,
    start_date: date,
    end_date: date,
) -> list[dict]:
    analytics = get_youtube_analytics_client()

    response = (
        analytics.reports()
        .query(
            ids="channel==MINE",
            startDate=start_date.isoformat(),
            endDate=end_date.isoformat(),
            metrics=(
                "views,"
                "estimatedMinutesWatched,"
                "averageViewDuration,"
                "subscribersGained"
            ),
            dimensions="day",
            filters=(
                f"video=={youtube_video_id}"
            ),
            sort="day",
        )
        .execute()
    )

    headers = [
        item["name"]
        for item in response.get(
            "columnHeaders",
            []
        )
    ]

    rows = []

    for raw_row in response.get(
        "rows",
        []
    ):
        item = dict(
            zip(
                headers,
                raw_row,
            )
        )

        watch_minutes = (
            item.get(
                "estimatedMinutesWatched"
            )
            or 0
        )

        rows.append(
            {
                "date":
                    date.fromisoformat(
                        item["day"]
                    ),

                "views":
                    int(
                        item.get("views")
                        or 0
                    ),

                "watch_time_hours":
                    float(
                        watch_minutes
                    )
                    / 60.0,

                "average_view_duration_seconds":
                    int(
                        item.get(
                            "averageViewDuration"
                        )
                        or 0
                    ),

                "subscribers_gained":
                    int(
                        item.get(
                            "subscribersGained"
                        )
                        or 0
                    ),
            }
        )

    return rows


def import_youtube_release(
    release_id: int,
) -> dict:
    db = SessionLocal()

    try:
        release = (
            db.query(Release)
            .filter(
                Release.id == release_id
            )
            .one_or_none()
        )

        if release is None:
            raise RuntimeError(
                f"Release {release_id} not found."
            )

        if not release.youtube_url:
            raise RuntimeError(
                f"Release {release_id} has no YouTube URL."
            )

        youtube_video_id = (
            extract_youtube_video_id(
                release.youtube_url
            )
        )

        metadata = get_video_metadata(
            youtube_video_id
        )

        video = (
            db.query(YouTubeVideo)
            .filter(
                YouTubeVideo.youtube_video_id
                == youtube_video_id
            )
            .one_or_none()
        )

        if video is None:
            video = YouTubeVideo(
                release_id=release.id,
                youtube_video_id=
                    youtube_video_id,
            )

            db.add(video)

        video.release_id = release.id
        video.title = metadata["title"]
        video.thumbnail_url = (
            metadata["thumbnail_url"]
        )

        published_at = (
            metadata["published_at"]
        )

        if published_at:
            from datetime import datetime

            video.published_at = (
                datetime.fromisoformat(
                    published_at.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

        db.flush()

        analytics_start = (
            release.release_date
        )

        analytics_end = date.today()

        daily_rows = (
            get_daily_video_analytics(
                youtube_video_id,
                analytics_start,
                analytics_end,
            )
        )

        # Replace this video's imported daily history.
        # Simple and safe for this MVP.
        (
            db.query(YouTubeMetric)
            .filter(
                YouTubeMetric.video_id
                == video.id
            )
            .delete(
                synchronize_session=False
            )
        )

        for row in daily_rows:
            db.add(
                YouTubeMetric(
                    video_id=
                        video.id,

                    date=
                        row["date"],

                    views=
                        row["views"],

                    watch_time_hours=
                        row[
                            "watch_time_hours"
                        ],

                    average_view_duration_seconds=
                        row[
                            "average_view_duration_seconds"
                        ],

                    subscribers_gained=
                        row[
                            "subscribers_gained"
                        ],

                    impressions=None,
                    ctr=None,
                )
            )

        db.commit()

        return {
            "release_id":
                release.id,

            "youtube_video_id":
                youtube_video_id,

            "title":
                video.title,

            "metric_rows":
                len(daily_rows),

            "first_date":
                (
                    daily_rows[0]["date"]
                    if daily_rows
                    else None
                ),

            "last_date":
                (
                    daily_rows[-1]["date"]
                    if daily_rows
                    else None
                ),
        }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: "
            "python -m app.importers.youtube_import "
            "<release_id>"
        )

    result = import_youtube_release(
        int(sys.argv[1])
    )

    print()
    print("=== YOUTUBE IMPORT COMPLETE ===")

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )
