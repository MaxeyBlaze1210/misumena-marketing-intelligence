from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
)

from app.database.database import Base


class BandcampSale(Base):
    __tablename__ = "bandcamp_sales"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    sale_date = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    transaction_id = Column(
        String,
        index=True,
    )

    item_type = Column(
        String,
    )

    item_name = Column(
        String,
        index=True,
    )

    artist = Column(
        String,
    )

    currency = Column(
        String,
    )

    item_price = Column(
        Float,
    )

    quantity = Column(
        Integer,
    )

    fan_contribution = Column(
        Float,
    )

    amount_received = Column(
        Float,
    )

    net_amount = Column(
        Float,
    )

    package = Column(
        String,
    )

    item_url = Column(
        String,
    )

    isrc = Column(
        String,
        index=True,
    )

    buyer_id = Column(
        String,
        nullable=True,
        index=True,
    )

    buyer_country_code = Column(
        String,
        index=True,
    )

    buyer_country_name = Column(
        String,
    )
