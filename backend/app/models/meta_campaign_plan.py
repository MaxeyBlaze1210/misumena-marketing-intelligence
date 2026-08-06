from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaCampaignPlan(Base):
    __tablename__ = "meta_campaign_plans"

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

    meta_audience_id = Column(
        Integer,
        ForeignKey("audience_families.id"),
        nullable=False,
        index=True,
    )

    objective = Column(
        String,
        nullable=False,
        default="OUTCOME_SALES",
    )

    optimization_goal = Column(
        String,
        nullable=False,
       default="OFFSITE_CONVERSIONS",
    )

    conversion_event = Column(
        String,
        nullable=False,
        default="ViewContent",
    )

    country_preset = Column(String)

    daily_budget = Column(
        Numeric(10, 2),
    )

    status = Column(
        String,
        nullable=False,
        default="draft",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    release = relationship(
        "Release",
    )

    meta_audience = relationship(
        "MetaAudience",
    )