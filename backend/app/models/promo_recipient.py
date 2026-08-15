from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class PromoRecipient(Base):
    __tablename__ = "promo_recipients"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("promo_campaigns.id"),
        nullable=False,
        index=True,
    )

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id"),
        nullable=False,
        index=True,
    )

    status = Column(
        String,
        nullable=False,
        default="draft",
    )

    personalized_subject = Column(String)
    personalized_body = Column(Text)

    sent_at = Column(DateTime)

    # Tracking
    tracking_token = Column(
        String,
        unique=True,
        index=True,
        nullable=True,
    )

    first_opened_at = Column(
        DateTime,
        nullable=True,
    )

    last_opened_at = Column(
        DateTime,
        nullable=True,
    )

    open_count = Column(
        Integer,
        nullable=False,
        default=0,
    )

    error_message = Column(Text)

    campaign = relationship(
        "PromoCampaign",
        back_populates="recipients",
    )

    contact = relationship(
        "Contact",
    )
