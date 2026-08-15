from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


class MetaAdSetTargetingItem(Base):
    __tablename__ = "meta_adset_targeting_items"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    meta_adset_id = Column(
        Integer,
        ForeignKey("meta_adsets.id"),
        nullable=False,
        index=True,
    )

    item_type = Column(
        String,
        nullable=False,
        index=True,
    )

    meta_item_id = Column(
        String,
        nullable=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    adset = relationship(
        "MetaAdSet",
        back_populates="targeting_items",
    )
