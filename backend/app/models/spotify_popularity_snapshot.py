from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from app.database.database import Base


class SpotifyPopularitySnapshot(Base):
    __tablename__ = "spotify_popularity_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(
        Integer,
        ForeignKey("releases.id"),
        nullable=False,
        index=True,
    )

    observed_at = Column(
        Date,
        nullable=False,
        index=True,
    )

    track_popularity = Column(
        Integer,
        nullable=False,
    )

    track_streams = Column(
        Integer,
        nullable=True,
    )

    artist_popularity = Column(
        Integer,
        nullable=True,
    )

    source = Column(
        String,
        nullable=False,
        default="SubmitHub",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
