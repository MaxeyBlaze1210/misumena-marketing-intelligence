from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaCampaignPlanAsset(Base):
    __tablename__ = "meta_campaign_plan_assets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meta_campaign_plan_id = Column(
        Integer,
        ForeignKey("meta_campaign_plans.id"),
        nullable=False,
        index=True,
    )

    asset_id = Column(
        Integer,
        ForeignKey("assets.id"),
        nullable=False,
        index=True,
    )

    primary_text = Column(
        Text,
        nullable=True,
    )

    meta_video_id = Column(
        String,
        nullable=True,
        index=True,
    )

    meta_creative_id = Column(
        String,
        nullable=True,
        index=True,
    )

    campaign_plan = relationship(
        "MetaCampaignPlan",
    )

    asset = relationship(
        "Asset",
        back_populates="campaign_plan_links",
    )