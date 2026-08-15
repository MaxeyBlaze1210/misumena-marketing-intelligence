from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
)

from app.database.database import Base


class YouTubeDiscoveryMetric(Base):
    __tablename__ = "youtube_discovery_metrics"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    video_id = Column(
        Integer,
        ForeignKey("youtube_videos.id"),
        nullable=False,
        index=True,
    )

    snapshot_date = Column(
        Date,
        nullable=False,
        index=True,
    )

    category = Column(
        String,
        nullable=False,
        index=True,
    )

    key = Column(
        String,
        nullable=True,
    )

    label = Column(
        String,
        nullable=True,
    )

    views = Column(
        Integer,
        nullable=True,
    )

    percentage = Column(
        Float,
        nullable=True,
    )
