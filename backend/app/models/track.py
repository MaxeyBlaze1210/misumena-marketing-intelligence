from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    isrc = Column(String, unique=True)

    spotify_id = Column(String)

    duration_ms = Column(Integer)

    release_id = Column(Integer, ForeignKey("releases.id"))

    release = relationship("Release", back_populates="tracks")