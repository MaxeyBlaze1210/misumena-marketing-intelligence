import json
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text

from app.database.database import Base


class MetaInterest(Base):
    __tablename__ = "meta_interests"

    id = Column(Integer, primary_key=True, index=True)

    meta_interest_id = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
        index=True,
    )

    topic = Column(String)
    description = Column(Text)
    disambiguation_category = Column(String)

    audience_size_lower_bound = Column(BigInteger)
    audience_size_upper_bound = Column(BigInteger)

    path = Column(Text)
    search_query = Column(String)

    last_verified_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def path_string(self) -> str:
        if not self.path:
            return ""

        return " → ".join(json.loads(self.path))