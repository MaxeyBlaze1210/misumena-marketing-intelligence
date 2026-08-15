from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base

class MetaCampaignVariant(Base):
    __tablename__ = "meta_campaign_variants"

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

    name = Column(
        String,
        nullable=False,
    )

    campaign_type = Column(
        String,
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
    )

    meta_interest_id = Column(
        Integer,
        ForeignKey("meta_interests.id"),
        nullable=True,
    )

    status = Column(
        String,
        nullable=False,
        default="draft",
    )

    meta_campaign_plan = relationship(
        "MetaCampaignPlan",
    )

    meta_interest = relationship(
        "MetaInterest",
    )

    interests = relationship(
        "MetaCampaignVariantInterest",
        back_populates="campaign_variant",
        cascade="all, delete-orphan",
    )

    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )
