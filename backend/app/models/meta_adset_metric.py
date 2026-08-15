from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAdSetMetric(Base):
    __tablename__ = "meta_adset_metrics"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    adset_id = Column(
        Integer,
        ForeignKey("meta_adsets.id"),
        nullable=False,
        index=True,
    )

    date_start = Column(
        Date,
        nullable=False,
    )

    date_stop = Column(
        Date,
        nullable=False,
    )

    spend = Column(Float)
    impressions = Column(Integer)
    reach = Column(Integer)

    results = Column(Float)
    result_type = Column(String)

    cost_per_result = Column(Float)

    raw_insights_json = Column(Text)

    adset = relationship(
        "MetaAdSet",
        back_populates="metrics",
    )
