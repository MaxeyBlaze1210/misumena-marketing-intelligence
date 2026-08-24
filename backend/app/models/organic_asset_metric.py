from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from app.database.database import Base


class OrganicAssetMetric(Base):
    """
    Organic social-platform observation for a creative asset.

    Multiple observations may exist for the same asset/platform
    so engagement can be tracked over time.
    """

    __tablename__ = "organic_asset_metrics"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    platform = Column(
        String,
        nullable=False,
        index=True,
    )

    platform_post_id = Column(
        String,
        nullable=True,
        index=True,
    )

    post_url = Column(
        String,
        nullable=True,
    )

    views = Column(
        Integer,
        nullable=True,
    )

    likes = Column(
        Integer,
        nullable=True,
    )

    comments = Column(
        Integer,
        nullable=True,
    )

    saves = Column(
        Integer,
        nullable=True,
    )

    shares = Column(
        Integer,
        nullable=True,
    )

    observed_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
