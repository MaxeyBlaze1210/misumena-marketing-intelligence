import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.meta_interest import MetaInterest

def save_meta_interests(
    db: Session,
    search_query: str,
    interests: list,
):
    for item in interests:

        existing = (
            db.query(MetaInterest)
            .filter(
                MetaInterest.meta_interest_id == item["id"]
            )
            .one_or_none()
        )

        if existing:

            existing.name = item.get("name")
            existing.topic = item.get("topic")
            existing.description = item.get("description")
            existing.disambiguation_category = item.get(
                "disambiguation_category"
            )

            existing.audience_size_lower_bound = item.get(
                "audience_size_lower_bound"
            )

            existing.audience_size_upper_bound = item.get(
                "audience_size_upper_bound"
            )

            existing.path = json.dumps(
                item.get("path", [])
            )

            existing.search_query = search_query

            existing.last_verified_at = (
                datetime.now(timezone.utc)
            )

        else:

            db.add(
                MetaInterest(
                    meta_interest_id=item["id"],
                    name=item.get("name"),
                    topic=item.get("topic"),
                    description=item.get("description"),
                    disambiguation_category=item.get(
                        "disambiguation_category"
                    ),
                    audience_size_lower_bound=item.get(
                        "audience_size_lower_bound"
                    ),
                    audience_size_upper_bound=item.get(
                        "audience_size_upper_bound"
                    ),
                    path=json.dumps(
                        item.get("path", [])
                    ),
                    search_query=search_query,
                )
            )

    db.commit()

    