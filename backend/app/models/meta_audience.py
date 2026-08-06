from sqlalchemy import Column, Integer, String

from app.database.database import Base


class MetaAudience(Base):
    __tablename__ = "audience_families"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
        unique=True,
    )

    description = Column(String)