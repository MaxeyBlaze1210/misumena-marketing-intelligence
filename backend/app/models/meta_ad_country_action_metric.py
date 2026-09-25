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


class MetaAdCountryActionMetric(Base):
    __tablename__ = "meta_ad_country_action_metrics"

    __table_args__ = (
        UniqueConstraint(
            "ad_id",
            "date_start",
            "date_stop",
            "country",
            "action_type",
            name="uq_meta_ad_country_action_metric",
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

    action_type = Column(
        String,
        nullable=False,
    )

    value = Column(Float)
    cost_per_action = Column(Float)
