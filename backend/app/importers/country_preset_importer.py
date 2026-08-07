import json
from pathlib import Path

from app.database.database import SessionLocal
from app.models.country import Country
from app.models.country_preset import CountryPreset
from app.models.country_preset_country import CountryPresetCountry


DATA_FILE = Path("data/country_presets.json")


def import_country_presets():

    with DATA_FILE.open("r", encoding="utf-8") as f:
        presets = json.load(f)

    db = SessionLocal()

    try:

        for preset_name, preset_data in presets.items():

            preset = (
                db.query(CountryPreset)
                .filter(CountryPreset.name == preset_name)
                .one_or_none()
            )

            if preset is None:

                preset = CountryPreset(
                    name=preset_name,
                    description=preset_data["description"],
                )

                db.add(preset)
                db.flush()

                print(f"[ADD PRESET] {preset.name}")

            for country_data in preset_data["countries"]:

                country = (
                    db.query(Country)
                    .filter(
                        Country.iso_code == country_data["iso_code"]
                    )
                    .one_or_none()
                )

                if country is None:

                    country = Country(
                        iso_code=country_data["iso_code"],
                        name=country_data["name"],
                    )

                    db.add(country)
                    db.flush()

                    print(f"[ADD COUNTRY] {country.name}")

                existing = (
                    db.query(CountryPresetCountry)
                    .filter(
                        CountryPresetCountry.country_preset_id == preset.id,
                        CountryPresetCountry.country_id == country.id,
                    )
                    .one_or_none()
                )

                if existing is None:

                    db.add(
                        CountryPresetCountry(
                            country_preset_id=preset.id,
                            country_id=country.id,
                        )
                    )

                    print(
                        f"[LINK] {preset.name} → {country.name}"
                    )

        db.commit()

        print("Country presets imported.")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_country_presets()