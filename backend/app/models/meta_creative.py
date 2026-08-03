from sqlalchemy import Column, Float, ForeignKey, Integer, String

from app.database.database import Base


class MetaCreative(Base):
    __tablename__ = "meta_creatives"

    id = Column(Integer, primary_key=True, index=True)

    release_id = Column(Integer, ForeignKey("releases.id"))

    campaign = Column(String)
    audience = Column(String)

    creative_name = Column(String)

    spend = Column(Float)

    impressions = Column(Integer)

    clicks = Column(Integer)

    ctr = Column(Float)

    cpc = Column(Float)

    results = Column(Integer)

    cost_per_result = Column(Float)