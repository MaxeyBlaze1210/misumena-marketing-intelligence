from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String)
    greeting_name = Column(String)
    email = Column(String, nullable=False, unique=True, index=True)

    organization = Column(String)
    contact_type = Column(String)
    country = Column(String)

    notes = Column(Text)

    do_not_contact = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    source = Column(String)

    created_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
