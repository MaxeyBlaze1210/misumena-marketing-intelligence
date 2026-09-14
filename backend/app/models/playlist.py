from sqlalchemy import Column, Integer, String, Text

from app.database.database import Base


class Playlist(Base):
    __tablename__ = "playlists"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)
    platform = Column(String, nullable=False, default="Spotify")

    spotify_playlist_id = Column(
        String,
        unique=True,
        nullable=True,
        index=True,
    )

    spotify_url = Column(String, nullable=True)
    artwork_url = Column(String, nullable=True)

    description = Column(Text, nullable=True)
    playlist_type = Column(String, nullable=False, default="artist_catalog")
