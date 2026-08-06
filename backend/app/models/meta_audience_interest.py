from sqlalchemy import Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAudienceInterest(Base):
    __tablename__ = "meta_audience_interests"

    id = Column(
        Integer,
        primary_key=True,
    )

    meta_audience_id = Column(
        Integer,
        ForeignKey("audience_families.id"),
        nullable=False,
    )

    meta_interest_id = Column(
        Integer,
        ForeignKey("meta_interests.id"),
        nullable=False,
    )

    role = Column(
        String,
        nullable=False,
        default="trusted",
    )

    notes = Column(Text)

    meta_interest = relationship(
        "MetaInterest",
    )

    meta_audience = relationship(
        "MetaAudience",
    )