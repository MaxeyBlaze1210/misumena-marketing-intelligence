from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    release_id = Column(
        Integer,
        ForeignKey("releases.id"),
        nullable=False,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    asset_type = Column(
        String,
        nullable=False,
        index=True,
    )

    source = Column(
        String,
        nullable=True,
    )

    source_id = Column(
        String,
        nullable=True,
        index=True,
    )

    source_url = Column(
        String,
        nullable=True,
    )

    file_name = Column(
        String,
        nullable=True,
    )

    mime_type = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    release = relationship(
        "Release",
    )

    campaign_plan_links = relationship(
        "MetaCampaignPlanAsset",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
