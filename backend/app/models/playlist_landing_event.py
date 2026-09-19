from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database.database import Base


class PlaylistLandingEvent(Base):
    __tablename__ = "playlist_landing_events"

    id = Column(Integer, primary_key=True, index=True)

    playlist_id = Column(
        Integer,
        ForeignKey("playlists.id"),
        nullable=False,
        index=True,
    )

    event_type = Column(String, nullable=False, index=True)

    platform = Column(String, nullable=True, index=True)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
    )
