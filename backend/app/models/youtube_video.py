from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class YouTubeVideo(Base):
    __tablename__ = "youtube_videos"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(
        Integer,
        ForeignKey("releases.id")
    )

    youtube_video_id = Column(
        String,
        unique=True
    )

    title = Column(String)

    published_at = Column(DateTime)

    thumbnail_url = Column(String)

    release = relationship(
        "Release"
    )