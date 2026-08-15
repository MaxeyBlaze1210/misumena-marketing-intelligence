from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class PromoCampaign(Base):
    __tablename__ = "promo_campaigns"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(
        Integer,
        ForeignKey("releases.id"),
        nullable=False,
        index=True,
    )

    name = Column(String)
    subject = Column(String)
    body = Column(Text)

    status = Column(
        String,
        nullable=False,
        default="draft",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    recipients = relationship(
        "PromoRecipient",
        back_populates="campaign",
        cascade="all, delete-orphan",
    )
