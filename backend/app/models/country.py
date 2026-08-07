from sqlalchemy import Column, Integer, String

from app.database.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    iso_code = Column(
        String(2),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )