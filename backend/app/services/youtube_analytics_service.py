from googleapiclient.discovery import build

from app.services.youtube_auth import get_youtube_credentials


def get_youtube_analytics_client():
    credentials = get_youtube_credentials()

    return build(
        "youtubeAnalytics",
        "v2",
        credentials=credentials,
    )


def get_video_metrics():
    youtube_analytics = get_youtube_analytics_client()

    response = youtube_analytics.reports().query(
        ids="channel==UC4hon_Z9MXtkvLkNsw7aELQ",
        startDate="2025-01-01",
        endDate="2026-08-04",
        metrics=(
            "views,"
            "estimatedMinutesWatched,"
            "averageViewDuration,"
            "averageViewPercentage,"
            "subscribersGained"
        ),
        dimensions="day",
        sort="day",
    ).execute()

    return response