from sqlalchemy import (
    Column,
    Date,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)

from app.database.database import Base


class MetaAdCountryMetric(Base):
    __tablename__ = "meta_ad_country_metrics"

    __table_args__ = (
        UniqueConstraint(
            "ad_id",
            "date_start",
            "date_stop",
            "country",
            name="uq_meta_ad_country_metric",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    ad_id = Column(
        Integer,
        ForeignKey("meta_ads.id"),
        nullable=False,
    )

    date_start = Column(
        Date,
        nullable=False,
    )

    date_stop = Column(
        Date,
        nullable=False,
    )

    country = Column(
        String,
        nullable=False,
    )

    spend = Column(Float)
    impressions = Column(Integer)

    # Meta's broad click metric.
    clicks = Column(Integer)

    # Actual Meta inline link clicks.
    link_clicks = Column(Integer)
