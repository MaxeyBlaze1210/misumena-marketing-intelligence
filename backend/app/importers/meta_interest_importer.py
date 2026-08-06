from time import sleep

from app.database.database import SessionLocal
from app.services.meta_interest_service import save_meta_interests
from app.services.meta_service import search_interests


SEARCH_GROUPS = {
    "historic_roots_and_chill": [
        "organic food",
        "music",
        "african popular music",
        "african dance",
        "world music",
        "ethical consumption",
        "folk music",
        "afrocentrism",
        "fair trade certification",
        "traditional african music",
        "sustainable fashion",
        "fair trade",
        "afrobeat",
        "africa",
        "kenya",
        "natural foods",
        "organic products",
        "travel inspiration",
    ],
    "historic_dance_groove_repeat": [
        "burning man",
        "spotify",
        "boiler room",
        "african popular music",
        "ultra music festival",
        "dj",
        "african dance",
        "dance music",
        "keinemusik",
        "mixmag",
        "world music",
        "tomorrowland",
        "african culture",
        "skrillex",
        "travel the world",
        "lollapalooza",
        "house music",
        "afrobeat",
        "deep house",
        "africa",
        "coachella",
        "electronic music",
        "travel",
        "electric forest festival",
        "nts radio",
        "radio music",
        "music news",
        "dj mag",
        "music producer",
    ],
    "afro_roots_exploration": [
        "kora",
        "griot",
        "west african music",
        "malian music",
        "gambian music",
        "acoustic music",
        "traditional music",
        "cultural tourism",
        "ecotourism",
        "nature photography",
        "environmentalism",
        "meditation",
        "yoga",
        "folklore",
    ],
    "afro_house_exploration": [
        "afro house",
        "amapiano",
        "south african music",
        "house music",
        "deep house",
        "electronic music",
        "dance music",
        "tribal house",
        "progressive house",
        "organic house",
        "club culture",
        "nightlife",
        "music festivals",
        "boiler room",
        "cercle",
    ],
    "latin_house_exploration": [
        "latin house",
        "latin music",
        "afro latin music",
        "latin dance",
        "salsa",
        "cumbia",
        "house music",
        "deep house",
        "electronic music",
        "world music",
    ],
    "afrobeats_exploration": [
        "afrobeat",
        "afrobeats",
        "afropop",
        "african popular music",
        "west african music",
        "nigerian music",
        "ghanaian music",
        "highlife",
        "azonto",
        "spotify",
        "music streaming",
    ],
    "lifestyle_exploration": [
        "yoga",
        "meditation",
        "mindfulness",
        "nature",
        "nature photography",
        "ecotourism",
        "fair trade",
        "organic food",
        "ethical consumption",
        "sustainable fashion",
        "sustainable agriculture",
        "environmentalism",
        "conservation",
        "hiking",
        "cultural tourism",
    ],
}


def iter_unique_queries():
    seen = set()

    for group, queries in SEARCH_GROUPS.items():
        for query in queries:
            normalized = query.strip().lower()

            if normalized in seen:
                continue

            seen.add(normalized)
            yield group, query


def import_meta_interests() -> None:
    db = SessionLocal()

    try:
        for group, query in iter_unique_queries():
            try:
                response = search_interests(query)
                interests = response.get("data", [])

                save_meta_interests(
                    db=db,
                    search_query=query,
                    interests=interests,
                )

                print(
                    f"[{group}] {query}: "
                    f"{len(interests)} result(s)"
                )

                # Be gentle with the API.
                sleep(0.3)

            except Exception as exc:
                db.rollback()
                print(f"[ERROR] {query}: {exc}")

    finally:
        db.close()


if __name__ == "__main__":
    import_meta_interests()