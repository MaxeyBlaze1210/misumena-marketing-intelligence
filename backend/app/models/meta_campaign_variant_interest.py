from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaCampaignVariantInterest(Base):
    __tablename__ = "meta_campaign_variant_interests"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meta_campaign_variant_id = Column(
        Integer,
        ForeignKey("meta_campaign_variants.id"),
        nullable=False,
        index=True,
    )

    meta_interest_id = Column(
        Integer,
        ForeignKey("meta_interests.id"),
        nullable=False,
        index=True,
    )

    campaign_variant = relationship(
        "MetaCampaignVariant",
        back_populates="interests",
    )

    meta_interest = relationship(
        "MetaInterest",
    )