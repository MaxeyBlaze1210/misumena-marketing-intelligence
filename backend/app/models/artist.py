from sqlalchemy import Column, Integer, String

from app.database.database import Base


class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    spotify_artist_id = Column(String, unique=True, nullable=True)
    image_url = Column(String, nullable=True)