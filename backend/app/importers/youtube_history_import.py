from datetime import date, datetime

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.models.release import Release
from app.models.youtube_discovery_metric import (
    YouTubeDiscoveryMetric,
)
from app.models.youtube_metric import YouTubeMetric
from app.models.youtube_recommendation import (
    YouTubeRecommendation,
)
from app.models.youtube_video import YouTubeVideo
from app.services.youtube_analytics_service import (
    get_youtube_analytics_client,
)
from app.services.youtube_service import (
    get_youtube_client,
)
from app.importers.youtube_import import (
    extract_youtube_video_id,
    get_daily_video_analytics,
)


def parse_response(response):
    headers = [
        item["name"]
        for item in response.get(
            "columnHeaders",
            []
        )
    ]

    return [
        dict(zip(headers, row))
        for row in response.get(
            "rows",
            []
        )
    ]


def get_channel_upload_ids():
    youtube = get_youtube_client()

    channel = (
        youtube.channels()
        .list(
            part="contentDetails",
            mine=True,
        )
        .execute()
    )

    items = channel.get("items", [])

    if not items:
        raise RuntimeError(
            "Authenticated YouTube channel not found."
        )

    uploads_id = (
        items[0]
        ["contentDetails"]
        ["relatedPlaylists"]
        ["uploads"]
    )

    video_ids = []
    page_token = None

    while True:
        response = (
            youtube.playlistItems()
            .list(
                part="contentDetails",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=page_token,
            )
            .execute()
        )

        for item in response.get(
            "items",
            []
        ):
            video_id = (
                item.get(
                    "contentDetails",
                    {}
                )
                .get("videoId")
            )

            if video_id:
                video_ids.append(
                    video_id
                )

        page_token = response.get(
            "nextPageToken"
        )

        if not page_token:
            break

    return video_ids


def get_video_metadata_batch(
    video_ids,
):
    youtube = get_youtube_client()

    results = {}

    for start in range(
        0,
        len(video_ids),
        50,
    ):
        chunk = video_ids[
            start:start + 50
        ]

        response = (
            youtube.videos()
            .list(
                part=(
                    "snippet,"
                    "contentDetails"
                ),
                id=",".join(chunk),
            )
            .execute()
        )

        for item in response.get(
            "items",
            []
        ):
            snippet = item.get(
                "snippet",
                {}
            )

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
                candidate = thumbnails.get(
                    key
                )

                if candidate and candidate.get(
                    "url"
                ):
                    thumbnail_url = (
                        candidate["url"]
                    )
                    break

            results[item["id"]] = {
                "title":
                    snippet.get("title"),

                "published_at":
                    snippet.get(
                        "publishedAt"
                    ),

                "thumbnail_url":
                    thumbnail_url,
            }

    return results


def analytics_query(
    video_id,
    start_date,
    end_date,
    *,
    metrics,
    dimensions=None,
    traffic_source=None,
):
    analytics = (
        get_youtube_analytics_client()
    )

    filters = [
        f"video=={video_id}"
    ]

    if traffic_source:
        filters.append(
            "insightTrafficSourceType"
            f"=={traffic_source}"
        )

    kwargs = {
        "ids":
            "channel==MINE",

        "startDate":
            start_date.isoformat(),

        "endDate":
            end_date.isoformat(),

        "metrics":
            metrics,

        "filters":
            ";".join(filters),
    }

    if dimensions:
        kwargs["dimensions"] = (
            dimensions
        )

    # Traffic-source detail reports have stricter
    # YouTube Analytics API requirements:
    # maxResults must be <= 25 and sort is required.
    if dimensions == "insightTrafficSourceDetail":
        kwargs["maxResults"] = 25
        kwargs["sort"] = "-views"
    else:
        kwargs["maxResults"] = 200

    response = (
        analytics.reports()
        .query(**kwargs)
        .execute()
    )

    return parse_response(
        response
    )


def get_traffic_sources(
    video_id,
    start_date,
    end_date,
):
    return analytics_query(
        video_id,
        start_date,
        end_date,
        metrics="views",
        dimensions=(
            "insightTrafficSourceType"
        ),
    )


def get_countries(
    video_id,
    start_date,
    end_date,
):
    return analytics_query(
        video_id,
        start_date,
        end_date,
        metrics="views",
        dimensions="country",
    )


def get_source_details(
    video_id,
    start_date,
    end_date,
    source_type,
):
    return analytics_query(
        video_id,
        start_date,
        end_date,
        metrics="views",
        dimensions=(
            "insightTrafficSourceDetail"
        ),
        traffic_source=
            source_type,
    )


def resolve_related_videos(
    video_ids,
):
    if not video_ids:
        return {}

    youtube = get_youtube_client()

    resolved = {}

    ids = list(
        dict.fromkeys(video_ids)
    )

    for start in range(
        0,
        len(ids),
        50,
    ):
        chunk = ids[
            start:start + 50
        ]

        response = (
            youtube.videos()
            .list(
                part="snippet",
                id=",".join(chunk),
            )
            .execute()
        )

        for item in response.get(
            "items",
            []
        ):
            snippet = item.get(
                "snippet",
                {}
            )

            resolved[item["id"]] = {
                "title":
                    snippet.get("title"),

                "channel":
                    snippet.get(
                        "channelTitle"
                    ),
            }

    return resolved


def build_release_video_map(db):
    mapping = {}

    releases = (
        db.query(Release)
        .filter(
            Release.youtube_url
            .isnot(None)
        )
        .all()
    )

    for release in releases:
        try:
            video_id = (
                extract_youtube_video_id(
                    release.youtube_url
                )
            )
        except ValueError:
            continue

        mapping[video_id] = (
            release.id
        )

    return mapping


def replace_daily_metrics(
    db,
    video,
    start_date,
    end_date,
):
    rows = (
        get_daily_video_analytics(
            video.youtube_video_id,
            start_date,
            end_date,
        )
    )

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

    for row in rows:
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

    return len(rows)


def replace_discovery(
    db,
    video,
    start_date,
    end_date,
):
    snapshot_date = date.today()

    (
        db.query(
            YouTubeDiscoveryMetric
        )
        .filter(
            YouTubeDiscoveryMetric.video_id
            == video.id
        )
        .delete(
            synchronize_session=False
        )
    )

    (
        db.query(
            YouTubeRecommendation
        )
        .filter(
            YouTubeRecommendation.video_id
            == video.id
        )
        .delete(
            synchronize_session=False
        )
    )

    # --------------------------------------------------
    # Traffic-source mix
    # --------------------------------------------------

    traffic_rows = get_traffic_sources(
        video.youtube_video_id,
        start_date,
        end_date,
    )

    total_traffic_views = sum(
        int(row.get("views") or 0)
        for row in traffic_rows
    )

    for row in traffic_rows:
        source = row.get(
            "insightTrafficSourceType"
        )

        views = int(
            row.get("views")
            or 0
        )

        percentage = (
            views
            / total_traffic_views
            * 100
            if total_traffic_views
            else None
        )

        db.add(
            YouTubeDiscoveryMetric(
                video_id=
                    video.id,

                snapshot_date=
                    snapshot_date,

                category=
                    "traffic_source",

                key=
                    source,

                label=
                    source,

                views=
                    views,

                percentage=
                    percentage,
            )
        )

    # --------------------------------------------------
    # Countries
    # --------------------------------------------------

    country_rows = get_countries(
        video.youtube_video_id,
        start_date,
        end_date,
    )

    total_country_views = sum(
        int(row.get("views") or 0)
        for row in country_rows
    )

    for row in country_rows:
        country = row.get(
            "country"
        )

        views = int(
            row.get("views")
            or 0
        )

        percentage = (
            views
            / total_country_views
            * 100
            if total_country_views
            else None
        )

        db.add(
            YouTubeDiscoveryMetric(
                video_id=
                    video.id,

                snapshot_date=
                    snapshot_date,

                category=
                    "country",

                key=
                    country,

                label=
                    country,

                views=
                    views,

                percentage=
                    percentage,
            )
        )

    # --------------------------------------------------
    # Search terms
    # --------------------------------------------------

    search_rows = get_source_details(
        video.youtube_video_id,
        start_date,
        end_date,
        "YT_SEARCH",
    )

    search_total = sum(
        int(row.get("views") or 0)
        for row in search_rows
    )

    for row in search_rows:
        detail = row.get(
            "insightTrafficSourceDetail"
        )

        views = int(
            row.get("views")
            or 0
        )

        percentage = (
            views
            / search_total
            * 100
            if search_total
            else None
        )

        db.add(
            YouTubeDiscoveryMetric(
                video_id=
                    video.id,

                snapshot_date=
                    snapshot_date,

                category=
                    "search_term",

                key=
                    detail,

                label=
                    detail,

                views=
                    views,

                percentage=
                    percentage,
            )
        )

    # --------------------------------------------------
    # External referrers
    # --------------------------------------------------

    external_rows = (
        get_source_details(
            video.youtube_video_id,
            start_date,
            end_date,
            "EXT_URL",
        )
    )

    external_total = sum(
        int(row.get("views") or 0)
        for row in external_rows
    )

    for row in external_rows:
        detail = row.get(
            "insightTrafficSourceDetail"
        )

        views = int(
            row.get("views")
            or 0
        )

        percentage = (
            views
            / external_total
            * 100
            if external_total
            else None
        )

        db.add(
            YouTubeDiscoveryMetric(
                video_id=
                    video.id,

                snapshot_date=
                    snapshot_date,

                category=
                    "external_source",

                key=
                    detail,

                label=
                    detail,

                views=
                    views,

                percentage=
                    percentage,
            )
        )

    # --------------------------------------------------
    # Suggested / related videos
    # --------------------------------------------------

    related_rows = get_source_details(
        video.youtube_video_id,
        start_date,
        end_date,
        "RELATED_VIDEO",
    )

    related_ids = [
        row.get(
            "insightTrafficSourceDetail"
        )
        for row in related_rows
        if row.get(
            "insightTrafficSourceDetail"
        )
    ]

    resolved = (
        resolve_related_videos(
            related_ids
        )
    )

    related_total = sum(
        int(row.get("views") or 0)
        for row in related_rows
    )

    for row in related_rows:
        related_id = row.get(
            "insightTrafficSourceDetail"
        )

        views = int(
            row.get("views")
            or 0
        )

        info = resolved.get(
            related_id,
            {},
        )

        percentage = (
            views
            / related_total
            * 100
            if related_total
            else None
        )

        db.add(
            YouTubeRecommendation(
                video_id=
                    video.id,

                date=
                    snapshot_date,

                recommended_video_id=
                    related_id,

                recommended_title=
                    info.get("title"),

                recommended_channel=
                    info.get("channel"),

                views=
                    views,

                percentage=
                    percentage,
            )
        )

    return {
        "traffic_sources":
            len(traffic_rows),

        "countries":
            len(country_rows),

        "search_terms":
            len(search_rows),

        "external_sources":
            len(external_rows),

        "recommendations":
            len(related_rows),
    }


def import_channel_history():
    db = SessionLocal()

    try:
        video_ids = (
            get_channel_upload_ids()
        )

        metadata = (
            get_video_metadata_batch(
                video_ids
            )
        )

        release_map = (
            build_release_video_map(
                db
            )
        )

        results = []

        for index, video_id in enumerate(
            video_ids,
            start=1,
        ):
            data = metadata.get(
                video_id
            )

            if not data:
                continue

            published_raw = data.get(
                "published_at"
            )

            if not published_raw:
                continue

            published_at = (
                datetime.fromisoformat(
                    published_raw.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )

            video = (
                db.query(YouTubeVideo)
                .filter(
                    YouTubeVideo.youtube_video_id
                    == video_id
                )
                .one_or_none()
            )

            if video is None:
                video = YouTubeVideo(
                    youtube_video_id=
                        video_id
                )

                db.add(video)

            # Only assign a release when MMI already
            # knows the relationship.
            if video_id in release_map:
                video.release_id = (
                    release_map[
                        video_id
                    ]
                )

            video.title = (
                data.get("title")
            )

            video.published_at = (
                published_at
            )

            video.thumbnail_url = (
                data.get(
                    "thumbnail_url"
                )
            )

            db.flush()

            start_date = (
                published_at.date()
            )

            end_date = date.today()

            try:
                daily_count = (
                    replace_daily_metrics(
                        db,
                        video,
                        start_date,
                        end_date,
                    )
                )

                discovery = (
                    replace_discovery(
                        db,
                        video,
                        start_date,
                        end_date,
                    )
                )

                db.commit()

                status = "ok"

            except Exception as exc:
                db.rollback()

                status = (
                    f"error: {exc}"
                )

                daily_count = 0
                discovery = {}

            result = {
                "video_id":
                    video_id,

                "title":
                    data.get("title"),

                "daily_rows":
                    daily_count,

                "discovery":
                    discovery,

                "status":
                    status,
            }

            results.append(
                result
            )

            print(
                f"[{index}/{len(video_ids)}] "
                f"{video_id} | "
                f"{data.get('title')} | "
                f"{status}"
            )

        return results

    finally:
        db.close()


if __name__ == "__main__":
    results = (
        import_channel_history()
    )

    ok = sum(
        1
        for item in results
        if item["status"] == "ok"
    )

    failed = (
        len(results)
        - ok
    )

    print()
    print(
        "=== YOUTUBE HISTORY IMPORT ==="
    )

    print(
        f"Videos: {len(results)}"
    )

    print(
        f"Imported: {ok}"
    )

    print(
        f"Failed: {failed}"
    )
