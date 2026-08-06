from sqlalchemy import Column, Integer, ForeignKey

from app.database.database import Base


class ReleaseArtist(Base):
    __tablename__ = "release_artists"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(
        Integer,
        ForeignKey("releases.id")
    )

    artist_id = Column(
        Integer,
        ForeignKey("artists.id")
    )