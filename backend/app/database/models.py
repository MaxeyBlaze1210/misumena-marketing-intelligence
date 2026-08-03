from sqlalchemy import Column, Integer, String

from .database import Base


class Release(Base):
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    artists = Column(String)

    release_year = Column(Integer)

    isrc = Column(String)

    youtube_video_id = Column(String)

    spotify_uri = Column(String)