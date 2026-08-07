from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.database.database import Base


class CountryPresetCountry(Base):
    __tablename__ = "country_preset_countries"

    id = Column(
        Integer,
        primary_key=True,
    )

    country_preset_id = Column(
        Integer,
        ForeignKey("country_presets.id"),
        nullable=False,
    )

    country_id = Column(
        Integer,
        ForeignKey("countries.id"),
        nullable=False,
    )

    country_preset = relationship(
        "CountryPreset",
    )

    country = relationship(
        "Country",
    )