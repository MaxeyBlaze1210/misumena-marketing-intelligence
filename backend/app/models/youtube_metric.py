from sqlalchemy import Column, Integer, Float, Date, ForeignKey

from app.database.database import Base


class YouTubeMetric(Base):
    __tablename__ = "youtube_metrics"

    id = Column(Integer, primary_key=True, index=True)

    video_id = Column(
        Integer,
        ForeignKey("youtube_videos.id")
    )

    date = Column(Date, nullable=False)

    views = Column(Integer)

    watch_time_hours = Column(Float)

    average_view_duration_seconds = Column(Integer)

    impressions = Column(Integer)

    ctr = Column(Float)

    subscribers_gained = Column(Integer)