import app.database.init_db

from app.database.database import SessionLocal
from app.models.country import Country


AFRICAN_COUNTRIES = [
    ("DZ", "Algeria"),
    ("AO", "Angola"),
    ("BJ", "Benin"),
    ("BW", "Botswana"),
    ("BF", "Burkina Faso"),
    ("BI", "Burundi"),
    ("CV", "Cabo Verde"),
    ("CM", "Cameroon"),
    ("CF", "Central African Republic"),
    ("TD", "Chad"),
    ("KM", "Comoros"),
    ("CG", "Congo"),
    ("CD", "Democratic Republic of the Congo"),
    ("CI", "Côte d’Ivoire"),
    ("DJ", "Djibouti"),
    ("EG", "Egypt"),
    ("GQ", "Equatorial Guinea"),
    ("ER", "Eritrea"),
    ("SZ", "Eswatini"),
    ("ET", "Ethiopia"),
    ("GA", "Gabon"),
    ("GM", "Gambia"),
    ("GH", "Ghana"),
    ("GN", "Guinea"),
    ("GW", "Guinea-Bissau"),
    ("KE", "Kenya"),
    ("LS", "Lesotho"),
    ("LR", "Liberia"),
    ("LY", "Libya"),
    ("MG", "Madagascar"),
    ("MW", "Malawi"),
    ("ML", "Mali"),
    ("MR", "Mauritania"),
    ("MU", "Mauritius"),
    ("MA", "Morocco"),
    ("MZ", "Mozambique"),
    ("NA", "Namibia"),
    ("NE", "Niger"),
    ("NG", "Nigeria"),
    ("RW", "Rwanda"),
    ("ST", "São Tomé and Príncipe"),
    ("SN", "Senegal"),
    ("SC", "Seychelles"),
    ("SL", "Sierra Leone"),
    ("SO", "Somalia"),
    ("ZA", "South Africa"),
    ("SS", "South Sudan"),
    ("SD", "Sudan"),
    ("TZ", "Tanzania"),
    ("TG", "Togo"),
    ("TN", "Tunisia"),
    ("UG", "Uganda"),
    ("ZM", "Zambia"),
    ("ZW", "Zimbabwe"),
]


def import_african_countries():
    db = SessionLocal()

    try:
        created = 0
        existing = 0

        for iso_code, name in AFRICAN_COUNTRIES:
            country = (
                db.query(Country)
                .filter(
                    Country.iso_code == iso_code
                )
                .one_or_none()
            )

            if country is None:
                db.add(
                    Country(
                        iso_code=iso_code,
                        name=name,
                    )
                )
                created += 1
            else:
                existing += 1

        db.commit()

        print("Created:", created)
        print("Already present:", existing)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_african_countries()
