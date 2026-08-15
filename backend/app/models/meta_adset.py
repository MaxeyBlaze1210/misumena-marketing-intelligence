import json
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAdSet(Base):
    __tablename__ = "meta_adsets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meta_adset_id = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    meta_campaign_id = Column(
        String,
        nullable=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    status = Column(String)
    effective_status = Column(String)

    created_time = Column(DateTime)
    start_time = Column(DateTime)
    end_time = Column(DateTime)

    daily_budget = Column(
        Numeric(12, 2),
        nullable=True,
    )

    lifetime_budget = Column(
        Numeric(12, 2),
        nullable=True,
    )

    optimization_goal = Column(String)
    billing_event = Column(String)

    age_min = Column(Integer)
    age_max = Column(Integer)

    advantage_audience = Column(
        Boolean,
        nullable=True,
    )

    countries_json = Column(Text)
    targeting_json = Column(Text)

    last_imported_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    targeting_items = relationship(
        "MetaAdSetTargetingItem",
        back_populates="adset",
        cascade="all, delete-orphan",
    )

    metrics = relationship(
        "MetaAdSetMetric",
        back_populates="adset",
        cascade="all, delete-orphan",
    )

    @property
    def countries(self) -> list[str]:
        if not self.countries_json:
            return []

        return json.loads(
            self.countries_json
        )
