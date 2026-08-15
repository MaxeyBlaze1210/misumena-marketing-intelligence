import argparse
import csv
from pathlib import Path

from app.database.database import SessionLocal

# Register the complete SQLAlchemy model graph before querying.
# Several existing MMI models use relationship("ClassName") references.
import app.database.init_db  # noqa: F401

from app.models.contact import Contact


TYPE_PREFIXES = {
    "spoty": "spotify_curator",
    "radio": "radio",
    "dj": "dj",
    "blog": "blog",
}


def clean(value):
    return (value or "").strip()


def infer_type(first_name):
    value = clean(first_name)
    first_word = value.split()[0].lower() if value else ""
    return TYPE_PREFIXES.get(first_word)


def clean_name(first_name, last_name):
    first = clean(first_name)
    last = clean(last_name)

    parts = first.split(maxsplit=1)

    if parts and parts[0].lower() in TYPE_PREFIXES:
        first = parts[1] if len(parts) > 1 else ""

    return " ".join(
        value for value in [first, last] if value
    ).strip() or None


def email_columns(row):
    for key, value in row.items():
        if "mail" not in key.lower():
            continue

        value = clean(value)

        if "@" in value:
            yield value.lower()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually insert contacts. Default is dry run.",
    )

    args = parser.parse_args()
    path = Path(args.csv_file).expanduser()

    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    db = SessionLocal()

    discovered = {}
    skipped_uncategorized = []

    try:
        with path.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as f:
            reader = csv.DictReader(f)

            for row in reader:
                first = clean(row.get("First Name"))
                last = clean(row.get("Last Name"))

                contact_type = infer_type(first)
                name = clean_name(first, last)

                emails = list(email_columns(row))

                if not contact_type:
                    if emails:
                        skipped_uncategorized.append(
                            (name, emails)
                        )
                    continue

                for email in emails:
                    discovered[email] = {
                        "name": name,
                        "email": email,
                        "contact_type": contact_type,
                    }

        existing = {
            contact.email.lower(): contact
            for contact in db.query(Contact).all()
            if contact.email
        }

        new_contacts = [
            data
            for email, data in discovered.items()
            if email not in existing
        ]

        already_present = [
            data
            for email, data in discovered.items()
            if email in existing
        ]

        print()
        print("=== OUTLOOK PROMO CONTACT IMPORT ===")
        print()
        print(f"Promo addresses found:    {len(discovered)}")
        print(f"New contacts:             {len(new_contacts)}")
        print(f"Already in MMI:           {len(already_present)}")
        print(
            f"Uncategorised contacts:   "
            f"{len(skipped_uncategorized)}"
        )

        counts = {}

        for data in new_contacts:
            contact_type = data["contact_type"]
            counts[contact_type] = (
                counts.get(contact_type, 0) + 1
            )

        if counts:
            print()
            print("New contacts by type:")

            for contact_type, count in sorted(counts.items()):
                print(f"  {contact_type}: {count}")

        print()
        print("Contacts to import:")

        for data in new_contacts:
            print(
                f"  [{data['contact_type']}] "
                f"{data['name'] or '(no name)'} "
                f"<{data['email']}>"
            )

        if skipped_uncategorized:
            print()
            print("Skipped uncategorised contacts:")

            for name, emails in skipped_uncategorized:
                print(
                    f"  {name or '(no name)'} — "
                    f"{', '.join(emails)}"
                )

        if not args.apply:
            print()
            print("DRY RUN — database unchanged.")
            return

        for data in new_contacts:
            db.add(
                Contact(
                    name=data["name"],
                    email=data["email"],
                    contact_type=data["contact_type"],
                    source="outlook_contacts_export",
                    do_not_contact=False,
                )
            )

        db.commit()

        print()
        print(f"✓ Imported {len(new_contacts)} contacts.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
