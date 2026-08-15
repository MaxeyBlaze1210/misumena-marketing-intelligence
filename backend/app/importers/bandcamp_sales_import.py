import csv
import hashlib
import sys
from datetime import datetime
from pathlib import Path

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.models.bandcamp_sale import BandcampSale


def clean(value):
    if value is None:
        return None

    value = value.strip()

    return value or None


def as_float(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return float(
            value.replace(",", ".")
        )
    except ValueError:
        return None


def as_int(value):
    value = clean(value)

    if value is None:
        return None

    try:
        return int(
            float(value)
        )
    except ValueError:
        return None


def buyer_hash(email):
    email = clean(email)

    if not email:
        return None

    normalized = email.lower()

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def parse_date(value):
    value = clean(value)

    if not value:
        raise ValueError(
            "Bandcamp row has no date."
        )

    return datetime.strptime(
        value,
        "%m/%d/%y %I:%M%p",
    )


def import_bandcamp_sales(
    file_path,
):
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            path
        )

    db = SessionLocal()

    try:

        with path.open(
            "r",
            encoding="utf-16",
            newline="",
        ) as handle:

            sample = handle.read(4096)
            handle.seek(0)

            delimiter = (
                "\t"
                if "\t" in sample
                else ","
            )

            reader = csv.DictReader(
                handle,
                delimiter=delimiter,
            )

            # Manual snapshot import:
            # replace the previous snapshot so rerunning
            # this importer remains idempotent.
            db.query(
                BandcampSale
            ).delete(
                synchronize_session=False
            )

            imported = 0
            skipped_payouts = 0
            skipped_other = 0

            for row in reader:

                item_type = clean(
                    row.get("item type")
                )

                # Accounting payouts are not fan purchases.
                if item_type == "payout":
                    skipped_payouts += 1
                    continue

                # We currently want actual merchandise /
                # digital purchase rows with an item.
                item_name = clean(
                    row.get("item name")
                )

                if not item_name:
                    skipped_other += 1
                    continue

                sale = BandcampSale(
                    sale_date=
                        parse_date(
                            row.get("date")
                        ),

                    transaction_id=
                        clean(
                            row.get(
                                "bandcamp transaction id"
                            )
                        ),

                    item_type=
                        item_type,

                    item_name=
                        item_name,

                    artist=
                        clean(
                            row.get("artist")
                        ),

                    currency=
                        clean(
                            row.get("currency")
                        ),

                    item_price=
                        as_float(
                            row.get("item price")
                        ),

                    quantity=
                        as_int(
                            row.get("quantity")
                        ),

                    fan_contribution=
                        as_float(
                            row.get(
                                "additional fan contribution"
                            )
                        ),

                    amount_received=
                        as_float(
                            row.get(
                                "amount you received"
                            )
                        ),

                    net_amount=
                        as_float(
                            row.get("net amount")
                        ),

                    package=
                        clean(
                            row.get("package")
                        ),

                    item_url=
                        clean(
                            row.get("item url")
                        ),

                    isrc=
                        clean(
                            row.get("isrc")
                        ),

                    buyer_id=
                        buyer_hash(
                            row.get("buyer email")
                        ),

                    buyer_country_code=
                        clean(
                            row.get(
                                "buyer country code"
                            )
                        ),

                    buyer_country_name=
                        clean(
                            row.get(
                                "buyer country name"
                            )
                        ),
                )

                db.add(sale)
                imported += 1

            db.commit()

            return {
                "imported":
                    imported,

                "skipped_payouts":
                    skipped_payouts,

                "skipped_other":
                    skipped_other,
            }

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":

    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python -m "
            "app.importers.bandcamp_sales_import "
            "data/bandcamp_sales.csv"
        )

    result = import_bandcamp_sales(
        sys.argv[1]
    )

    print()
    print(
        "=== BANDCAMP SALES IMPORT ==="
    )

    print(
        f'Imported purchases: '
        f'{result["imported"]}'
    )

    print(
        f'Skipped payouts: '
        f'{result["skipped_payouts"]}'
    )

    print(
        f'Skipped other rows: '
        f'{result["skipped_other"]}'
    )
