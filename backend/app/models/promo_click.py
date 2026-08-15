from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.database import Base


class PromoClick(Base):
    __tablename__ = "promo_clicks"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    recipient_id = Column(
        Integer,
        ForeignKey("promo_recipients.id"),
        nullable=False,
        index=True,
    )

    link_type = Column(
        String,
        nullable=False,
        index=True,
    )

    clicked_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
