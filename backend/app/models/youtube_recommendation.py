from sqlalchemy import Column, Integer, Float, String, Date, ForeignKey

from app.database.database import Base


class YouTubeRecommendation(Base):
    __tablename__ = "youtube_recommendations"

    id = Column(Integer, primary_key=True, index=True)

    video_id = Column(
        Integer,
        ForeignKey("youtube_videos.id")
    )

    date = Column(Date, nullable=False)

    recommended_video_id = Column(String)

    recommended_title = Column(String)

    recommended_channel = Column(String)

    views = Column(Integer)

    percentage = Column(Float)