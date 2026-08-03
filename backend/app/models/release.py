from sqlalchemy import Column, Date, Integer, String

from app.database.database import Base


class Release(Base):
    __tablename__ = "releases"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    release_date = Column(Date, nullable=False)