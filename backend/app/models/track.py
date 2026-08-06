from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    isrc = Column(String, unique=True)

    spotify_track_id = Column(String, unique=True)

    duration_ms = Column(Integer)

    track_number = Column(Integer)

    release_id = Column(Integer, ForeignKey("releases.id"))

    release = relationship(
        "Release",
        back_populates="tracks",
    )