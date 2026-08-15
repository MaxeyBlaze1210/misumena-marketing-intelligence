from collections import Counter, defaultdict

from app.models.youtube_video import YouTubeVideo
from app.models.youtube_metric import YouTubeMetric
from app.models.youtube_discovery_metric import (
    YouTubeDiscoveryMetric,
)
from app.models.youtube_recommendation import (
    YouTubeRecommendation,
)


ORGANIC_SOURCE_KEYS = {
    "YT_SEARCH": "Search",
    "RELATED_VIDEO": "Suggested",
    "PLAYLIST": "Playlists",
    "YT_CHANNEL": "Channel",
    "SUBSCRIBER": "Subscriber",
    "EXT_URL": "External",
    "YT_OTHER_PAGE": "Other YouTube",
    "NO_LINK_OTHER": "Direct / unknown",
    "NOTIFICATION": "Notifications",
}


def _dominant_source(source_counts):
    candidates = [
        (
            label,
            source_counts.get(key, 0),
        )
        for key, label
        in ORGANIC_SOURCE_KEYS.items()
    ]

    candidates.sort(
        key=lambda item: item[1],
        reverse=True,
    )

    if not candidates:
        return None

    label, views = candidates[0]

    if views <= 0:
        return None

    return {
        "label": label,
        "views": views,
    }


def build_youtube_research_intelligence(
    db,
):
    videos = (
        db.query(YouTubeVideo)
        .order_by(
            YouTubeVideo.published_at.asc()
        )
        .all()
    )

    video_rows = []

    recommendation_channel_counter = Counter()
    recommendation_video_counter = Counter()

    recommendation_channel_views = Counter()
    recommendation_video_views = Counter()

    recommendation_channel_sources = defaultdict(
        set
    )

    for video in videos:

        metrics = (
            db.query(YouTubeMetric)
            .filter(
                YouTubeMetric.video_id
                == video.id
            )
            .all()
        )

        total_views = sum(
            row.views or 0
            for row in metrics
        )

        discovery = (
            db.query(
                YouTubeDiscoveryMetric
            )
            .filter(
                YouTubeDiscoveryMetric.video_id
                == video.id,
                YouTubeDiscoveryMetric.category
                == "traffic_source",
            )
            .all()
        )

        source_counts = {
            row.key: row.views or 0
            for row in discovery
        }

        traffic_total = sum(
            source_counts.values()
        )

        paid_views = source_counts.get(
            "ADVERTISING",
            0,
        )

        organic_views = max(
            0,
            traffic_total - paid_views,
        )

        organic_share = (
            organic_views
            / traffic_total
            * 100
            if traffic_total > 0
            else 0.0
        )

        dominant_source = (
            _dominant_source(
                source_counts
            )
        )

        recommendations = (
            db.query(
                YouTubeRecommendation
            )
            .filter(
                YouTubeRecommendation.video_id
                == video.id
            )
            .all()
        )

        meaningful_recommendations = [
            item
            for item in recommendations
            if (item.views or 0) > 0
        ]

        for item in meaningful_recommendations:

            channel = (
                item.recommended_channel
                or "Unknown channel"
            )

            title = (
                item.recommended_title
                or item.recommended_video_id
                or "Unknown video"
            )

            video_key = (
                channel,
                title,
            )

            recommendation_channel_counter[
                channel
            ] += 1

            recommendation_channel_views[
                channel
            ] += (
                item.views or 0
            )

            recommendation_channel_sources[
                channel
            ].add(
                video.id
            )

            recommendation_video_counter[
                video_key
            ] += 1

            recommendation_video_views[
                video_key
            ] += (
                item.views or 0
            )

        suggested_views = source_counts.get(
            "RELATED_VIDEO",
            0,
        )

        search_views = source_counts.get(
            "YT_SEARCH",
            0,
        )

        playlist_views = source_counts.get(
            "PLAYLIST",
            0,
        )

        subscriber_views = source_counts.get(
            "SUBSCRIBER",
            0,
        )

        external_views = source_counts.get(
            "EXT_URL",
            0,
        )

        suggested_share_of_organic = (
            suggested_views
            / organic_views
            * 100
            if organic_views > 0
            else 0.0
        )

        video_rows.append(
            {
                "video_id":
                    video.id,

                "youtube_video_id":
                    video.youtube_video_id,

                "title":
                    video.title,

                "published_at":
                    video.published_at,

                "total_views":
                    total_views,

                "paid_views":
                    paid_views,

                "organic_views":
                    organic_views,

                "organic_share":
                    organic_share,

                "dominant_source":
                    dominant_source,

                "search_views":
                    search_views,

                "suggested_views":
                    suggested_views,

                "playlist_views":
                    playlist_views,

                "subscriber_views":
                    subscriber_views,

                "external_views":
                    external_views,

                "suggested_share_of_organic":
                    suggested_share_of_organic,

                "recommendation_count":
                    len(
                        meaningful_recommendations
                    ),
            }
        )

    organic_winners = sorted(
        video_rows,
        key=lambda item: (
            -item["organic_views"],
            -item["organic_share"],
        ),
    )

    suggested_winners = sorted(
        [
            item
            for item in video_rows
            if item["organic_views"] > 0
        ],
        key=lambda item: (
            -item["suggested_views"],
            -item[
                "suggested_share_of_organic"
            ],
        ),
    )

    recurring_channels = []

    for channel, appearances in (
        recommendation_channel_counter.items()
    ):
        distinct_source_videos = len(
            recommendation_channel_sources[
                channel
            ]
        )

        if distinct_source_videos < 2:
            continue

        recurring_channels.append(
            {
                "channel":
                    channel,

                "source_video_count":
                    distinct_source_videos,

                "recommendation_rows":
                    appearances,

                "views":
                    recommendation_channel_views[
                        channel
                    ],
            }
        )

    recurring_channels.sort(
        key=lambda item: (
            -item["source_video_count"],
            -item["views"],
            item["channel"].lower(),
        )
    )

    recurring_videos = []

    for (
        channel,
        title,
    ), appearances in (
        recommendation_video_counter.items()
    ):
        if appearances < 2:
            continue

        recurring_videos.append(
            {
                "channel":
                    channel,

                "title":
                    title,

                "appearances":
                    appearances,

                "views":
                    recommendation_video_views[
                        (
                            channel,
                            title,
                        )
                    ],
            }
        )

    recurring_videos.sort(
        key=lambda item: (
            -item["appearances"],
            -item["views"],
        )
    )

    total_organic = sum(
        item["organic_views"]
        for item in video_rows
    )

    total_paid = sum(
        item["paid_views"]
        for item in video_rows
    )

    total_traffic = (
        total_organic
        + total_paid
    )

    return {
        "summary": {
            "video_count":
                len(video_rows),

            "organic_views":
                total_organic,

            "paid_views":
                total_paid,

            "organic_share":
                (
                    total_organic
                    / total_traffic
                    * 100
                    if total_traffic > 0
                    else 0.0
                ),
        },

        "organic_winners":
            organic_winners,

        "suggested_winners":
            suggested_winners,

        "recurring_channels":
            recurring_channels,

        "recurring_videos":
            recurring_videos,
    }
