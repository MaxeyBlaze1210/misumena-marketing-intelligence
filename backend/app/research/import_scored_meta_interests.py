import json
from pathlib import Path

from app.database.database import SessionLocal
from app.models.meta_interest import MetaInterest


INPUT_FILE = Path("data/meta_interest_scored.json")


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        data = json.load(f)

    db = SessionLocal()

    created = 0
    updated = 0

    try:
        for item in data["interests"]:
            meta_interest_id = str(
                item["meta_interest_id"]
            )

            interest = (
                db.query(MetaInterest)
                .filter(
                    MetaInterest.meta_interest_id
                    == meta_interest_id
                )
                .one_or_none()
            )

            if interest is None:
                interest = MetaInterest(
                    meta_interest_id=meta_interest_id,
                    name=item["name"],
                )

                db.add(interest)
                created += 1

            else:
                updated += 1

            # Synchronize Meta reference data.
            interest.name = item["name"]
            interest.topic = item.get("topic")
            interest.description = item.get("description")

            interest.audience_size_lower_bound = (
                item.get("audience_size_lower_bound")
            )

            interest.audience_size_upper_bound = (
                item.get("audience_size_upper_bound")
            )

            path = item.get("path")

            if path:
                interest.path = json.dumps(
                    path,
                    ensure_ascii=False,
                )
            else:
                interest.path = None

        db.commit()

        print()
        print("=" * 70)
        print("META INTEREST IMPORT")
        print("=" * 70)
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"Total:   {created + updated}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()