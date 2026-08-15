from app.database.database import SessionLocal
from app.models.meta_interest import MetaInterest


CURATED_INTERESTS = {
    "Afrobeats": [
        "6005722523404",  # Tiwa Savage
        "6003023077356",  # African popular music
        "6003484812986",  # Afrobeat
        "6003359282604",  # Music of Africa
    ],

    "African Roots": [
        "6003226755338",  # World music
        "6003484812986",  # Afrobeat
        "6003359282604",  # Music of Africa
        "6003023077356",  # African popular music
        "6003290182925",  # Folk music
    ],

    "Afrohouse": [
        "6003479860669",  # House music
        "6003596378473",  # Deep house
        "6003182953366",  # Mixmag
        "6003009781819",  # Boiler Room
        "6003179570015",  # KEINEMUSIK
        "6003289429270",  # Tomorrowland (festival)
        "6808891387078",  # Electronic music festivals
        "6003253526111",  # SoundCloud
    ],
}


AUDIENCE_NAME_MAP = {
    "Afro Roots": "African Roots",
    "African Roots": "African Roots",

    "Afrobeats": "Afrobeats",

    "Electronic": "Afrohouse",
    "Afrohouse": "Afrohouse",
}


CURATED_RELEVANCE = {
    "Afrobeats": {
        "6005722523404": 98,
        "6003023077356": 94,
        "6003484812986": 92,
        "6003359282604": 88,
    },

    "African Roots": {
        "6003226755338": 96,
        "6003359282604": 94,
        "6003023077356": 90,
        "6003484812986": 88,
        "6003290182925": 82,
    },

    "Afrohouse": {
        "6003479860669": 96,
        "6003596378473": 94,
        "6003182953366": 90,
        "6003009781819": 90,
        "6003179570015": 88,
        "6003289429270": 86,
        "6808891387078": 82,
        "6003253526111": 78,
    },
}


def get_audience_size(
    interest: MetaInterest,
) -> int | None:
    lower = (
        interest.audience_size_lower_bound
    )

    upper = (
        interest.audience_size_upper_bound
    )

    if lower is None and upper is None:
        return None

    if lower is None:
        return int(upper)

    if upper is None:
        return int(lower)

    return round(
        (lower + upper) / 2
    )


def get_candidate_interests_for_audience(
    audience_name: str,
    minimum_relevance: int = 0,
    minimum_audience_size: int = 0,
):
    audience_name = (
        AUDIENCE_NAME_MAP.get(
            audience_name,
            audience_name,
        )
    )

    meta_interest_ids = (
        CURATED_INTERESTS.get(
            audience_name,
            [],
        )
    )

    if not meta_interest_ids:
        return []

    db = SessionLocal()

    try:
        interests = (
            db.query(MetaInterest)
            .filter(
                MetaInterest.meta_interest_id.in_(
                    meta_interest_ids
                )
            )
            .all()
        )

        interest_by_meta_id = {
            interest.meta_interest_id:
                interest
            for interest in interests
        }

        candidates = []

        relevance_map = (
            CURATED_RELEVANCE.get(
                audience_name,
                {},
            )
        )

        for meta_interest_id in meta_interest_ids:

            interest = (
                interest_by_meta_id.get(
                    meta_interest_id
                )
            )

            if interest is None:
                continue

            audience_size = (
                get_audience_size(
                    interest
                )
            )

            relevance_score = (
                relevance_map.get(
                    meta_interest_id,
                    0,
                )
            )

            if (
                relevance_score
                < minimum_relevance
            ):
                continue

            if (
                audience_size is not None
                and audience_size
                < minimum_audience_size
            ):
                continue

            candidates.append(
                {
                    "meta_interest_id":
                        interest.meta_interest_id,

                    "name":
                        interest.name,

                    "audience_size":
                        audience_size or 0,

                    "relevance_score":
                        relevance_score,

                    "label":
                        "curated",

                    "reason":
                        "Validated and curated "
                        "for this audience family.",
                }
            )

        return candidates

    finally:
        db.close()
