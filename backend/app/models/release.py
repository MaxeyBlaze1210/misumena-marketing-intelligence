from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class Release(Base):
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    release_date = Column(Date, nullable=False)

    spotify_album_id = Column(String, unique=True)

    # Reusable release data
    artwork_url = Column(String)
    landing_slug = Column(String, unique=True, index=True)
    landing_description = Column(Text)

    spotify_url = Column(String)
    apple_music_url = Column(String)
    youtube_url = Column(String)
    bandcamp_url = Column(String)

    promo_folder_url = Column(String)

    meta_audience_id = Column(
        "audience_family_id",
        Integer,
        ForeignKey("audience_families.id"),
    )

    meta_audience = relationship(
        "MetaAudience",
    )

    tracks = relationship(
        "Track",
        back_populates="release",
        cascade="all, delete-orphan",
    )