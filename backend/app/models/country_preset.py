from sqlalchemy import Column, Integer, String

from app.database.database import Base


class CountryPreset(Base):
    __tablename__ = "country_presets"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    description = Column(String)