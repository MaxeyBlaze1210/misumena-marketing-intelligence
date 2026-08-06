import json
from pathlib import Path

from app.database.database import SessionLocal
from app.models.meta_audience import MetaAudience
from app.models.meta_audience_interest import MetaAudienceInterest
from app.models.meta_interest import MetaInterest


DATA_FILE = Path("data/meta_audiences.json")


def import_meta_audiences() -> None:
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Audience configuration not found: {DATA_FILE}"
        )

    with DATA_FILE.open("r", encoding="utf-8") as file:
        audience_config = json.load(file)

    db = SessionLocal()

    try:
        for audience_name, configured_interests in audience_config.items():
            audience = (
                db.query(MetaAudience)
                .filter(MetaAudience.name == audience_name)
                .one_or_none()
            )

            if audience is None:
                print(
                    f"[SKIP] Meta audience not found: "
                    f"{audience_name}"
                )
                continue

            for configured_interest in configured_interests:
                if isinstance(configured_interest, str):
                    interest_name = configured_interest
                    role = "trusted"
                    notes = None
                else:
                    interest_name = configured_interest["name"]
                    role = configured_interest.get(
                        "role",
                        "trusted",
                    )
                    notes = configured_interest.get("notes")

                meta_interest = (
                    db.query(MetaInterest)
                    .filter(MetaInterest.name == interest_name)
                    .one_or_none()
                )

                if meta_interest is None:
                    print(
                        f"[MISSING] Meta interest not found: "
                        f"{interest_name}"
                    )
                    continue

                existing_link = (
                    db.query(MetaAudienceInterest)
                    .filter(
                        MetaAudienceInterest.meta_audience_id
                        == audience.id,
                        MetaAudienceInterest.meta_interest_id
                        == meta_interest.id,
                    )
                    .one_or_none()
                )

                if existing_link is not None:
                    existing_link.role = role
                    existing_link.notes = notes

                    print(
                        f"[UPDATE] {audience.name} → "
                        f"{meta_interest.name}"
                    )
                    continue

                db.add(
                    MetaAudienceInterest(
                        meta_audience_id=audience.id,
                        meta_interest_id=meta_interest.id,
                        role=role,
                        notes=notes,
                    )
                )

                print(
                    f"[ADD] {audience.name} → "
                    f"{meta_interest.name}"
                )

        db.commit()
        print("Meta audience interests imported.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_meta_audiences()