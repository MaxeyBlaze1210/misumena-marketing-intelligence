import sys

# Important:
# importing init_db registers all SQLAlchemy models and relationships
# before we start querying.
import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.services.asset_sync_service import (
    sync_dropbox_creatives,
)


RELEASE_ID = 1


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.research.sync_dropbox_assets "
            "<dropbox-folder-url>"
        )
        raise SystemExit(1)

    folder_url = sys.argv[1]

    db = SessionLocal()

    try:
        result = sync_dropbox_creatives(
            db=db,
            release_id=RELEASE_ID,
            shared_folder_url=folder_url,
        )

        print()
        print("=" * 60)
        print("DROPBOX ASSET SYNC")
        print("=" * 60)

        print(f"Found:   {result['found']}")
        print(f"Created: {result['created']}")
        print(f"Updated: {result['updated']}")

        print()

        for asset in result["assets"]:
            print(
                asset.id,
                "|",
                asset.source_id,
                "|",
                asset.file_name,
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()