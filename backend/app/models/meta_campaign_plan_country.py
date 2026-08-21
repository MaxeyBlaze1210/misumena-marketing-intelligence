from sqlalchemy import Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaCampaignPlanCountry(Base):
    __tablename__ = "meta_campaign_plan_countries"

    id = Column(
        Integer,
        primary_key=True,
    )

    meta_campaign_plan_id = Column(
        Integer,
        ForeignKey("meta_campaign_plans.id"),
        nullable=False,
        index=True,
    )

    country_id = Column(
        Integer,
        ForeignKey("countries.id"),
        nullable=False,
        index=True,
    )

    meta_campaign_plan = relationship(
        "MetaCampaignPlan",
    )

    country = relationship(
        "Country",
    )

    __table_args__ = (
        UniqueConstraint(
            "meta_campaign_plan_id",
            "country_id",
            name="uq_meta_campaign_plan_country",
        ),
    )
