from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaCampaign(Base):
    __tablename__ = "meta_campaigns"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(
        Integer,
        ForeignKey("releases.id"),
        nullable=True,
    )

    meta_campaign_id = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    status = Column(String)
    objective = Column(String)

    ads = relationship(
        "MetaAd",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )