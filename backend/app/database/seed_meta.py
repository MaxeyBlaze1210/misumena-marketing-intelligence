from app.database.database import SessionLocal

from app.models.track import Track
from app.models.release import Release
from app.models.meta_creative import MetaCreative


db = SessionLocal()

try:
    db.add(
        MetaCreative(
            release_id=1,
            creative_name="Creative 1",
            spend=40,
            impressions=12000,
            clicks=520,
            ctr=4.3,
            results=120,
            cost_per_result=0.33,
        )
    )

    db.add(
        MetaCreative(
            release_id=1,
            creative_name="Creative 5",
            spend=82,
            impressions=21000,
            clicks=940,
            ctr=4.5,
            results=340,
            cost_per_result=0.24,
        )
    )

    db.add(
        MetaCreative(
            release_id=1,
            creative_name="Creative 6",
            spend=35,
            impressions=9500,
            clicks=180,
            ctr=1.9,
            results=30,
            cost_per_result=1.16,
        )
    )

    db.commit()
    print("Done")

except Exception:
    db.rollback()
    raise

finally:
    db.close()