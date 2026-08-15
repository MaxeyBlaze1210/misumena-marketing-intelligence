from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Date,
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

    meta_pixel_id = Column(
        String,
        nullable=True,
    )

    destination_url = Column(
        String,
        nullable=True,
    )

    call_to_action = Column(
        String,
        nullable=False,
        default="LISTEN_NOW",
    )

    country_preset = Column(String)

    total_budget = Column(
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

    meta_campaign_record_id = Column(
        Integer,
        ForeignKey("meta_campaigns.id"),
        nullable=True,
        unique=True,
    )

    meta_campaign_record = relationship(
        "MetaCampaign",
    )

    meta_audience = relationship(
        "MetaAudience",
    )

    country_preset_id = Column(
        Integer,
        ForeignKey("country_presets.id"),
        nullable=True,
    )

    country_preset_relation = relationship(
        "CountryPreset",
    )   

    age_min = Column(
        Integer,
        nullable=False,
        default=18,
    )

    age_max = Column(
        Integer,
        nullable=False,
        default=64,
    )    

    campaign_type = Column(
        String,
        nullable=False,
        default="interest",
    )

    start_date = Column(
        Date,
        nullable=True,
    )

    end_date = Column(
        Date,
        nullable=True,
    )     