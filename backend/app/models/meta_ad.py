from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAd(Base):
    __tablename__ = "meta_ads"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("meta_campaigns.id"),
        nullable=False,
    )

    meta_ad_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    meta_adset_id = Column(String)
    meta_creative_id = Column(String)

    name = Column(String, nullable=False)
    status = Column(String)

    campaign = relationship(
        "MetaCampaign",
        back_populates="ads",
    )

    metrics = relationship(
        "MetaAdMetric",
        back_populates="ad",
        cascade="all, delete-orphan",
    )