from sqlalchemy import Column, Date, Float, ForeignKey, Integer

from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAdMetric(Base):
    __tablename__ = "meta_ad_metrics"

    id = Column(Integer, primary_key=True, index=True)

    ad_id = Column(
        Integer,
        ForeignKey("meta_ads.id"),
        nullable=False,
    )

    date_start = Column(Date, nullable=False)
    date_stop = Column(Date, nullable=False)

    spend = Column(Float)
    impressions = Column(Integer)
    reach = Column(Integer)
    clicks = Column(Integer)

    ctr = Column(Float)
    cpc = Column(Float)

    landing_page_views = Column(Integer)
    cost_per_landing_page_view = Column(Float)

    results = Column(Integer)
    cost_per_result = Column(Float)

    video_views = Column(Integer)

    ad = relationship(
        "MetaAd",
        back_populates="metrics",
    )