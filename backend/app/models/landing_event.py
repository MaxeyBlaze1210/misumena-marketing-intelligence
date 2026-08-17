from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.sql import func

from app.database.database import Base


class LandingEvent(Base):
    __tablename__ = "landing_events"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    release_id = Column(
        Integer,
        ForeignKey("releases.id"),
        nullable=False,
        index=True,
    )

    event_type = Column(
        String,
        nullable=False,
        index=True,
    )

    platform = Column(
        String,
        nullable=True,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
