import json
from pathlib import Path

from openai import OpenAI


OUTPUT_FILE = Path("data/meta_interest_candidates.json")

client = OpenAI()


AUDIENCES = {
    "African Roots": {
        "description": (
            "African roots music, traditional African music, African folk, "
            "acoustic African music, kora, traditional instruments, "
            "Afro-folk, cultural music, world music and adjacent audiences."
        ),
        "existing_interests": [
            "Weltmusik",
            "Traditionelle afrikanische Musik",
            "Fairer Handel",
            "Fair-Trade-Siegel",
        ],
    },
    "Afrobeats": {
        "description": (
            "Modern Afrobeats, Afropop, West African pop, African popular music, "
            "danceable contemporary African music and adjacent mainstream audiences."
        ),
        "existing_interests": [
            "Afrobeat (Musik)",
            "Afrikanische Popularmusik",
            "Spotify (Streaming-Dienst)",
            "Weltmusik",
        ],
    },
    "Afrohouse": {
        "description": (
            "Afro House, African electronic music, house music with African influences, "
            "South African dance music, Amapiano-adjacent audiences, DJs, "
            "clubs, festivals and electronic music culture."
        ),
        "existing_interests": [
            "House (Musik)",
            "Deep House",
            "Spotify (Streaming-Dienst)",
            "Boiler Room",
            "Elektronische Musik (Musik)",
        ],
    },
}


SYSTEM_PROMPT = """
You are a research assistant helping build a candidate vocabulary
for Meta Ads interest discovery.

Your task is NOT to decide which advertising interests are best.

Your task is to generate a large, diverse, structured collection of
SEARCH TERMS that can later be submitted to Meta's interest-search API.

Important:

1. A generated term is only a SEARCH CANDIDATE.
2. Never claim that Meta actually supports or targets the term.
3. Do not invent fictional artists, festivals, labels, genres or brands.
4. Prefer entities that plausibly have meaningful public recognition.
5. Include both obvious and less obvious but defensible candidates.
6. Avoid trivial spelling variants and near-duplicates.
7. Think beyond genres.

Search systematically across:

- genres
- subgenres
- artists
- DJs
- labels
- collectives
- festivals
- clubs
- music media
- radio
- streaming/music platforms
- dance styles
- musical instruments
- countries and regions
- cities associated with scenes
- cultural movements
- adjacent genres
- nightlife / club culture
- lifestyle and cultural interests
- music-related brands or institutions

The goal is high recall:
generate enough plausible search terms that the Meta API,
not you, can later determine which ones actually exist.

Return valid JSON only.
"""


def build_prompt(
    audience_name: str,
    description: str,
    existing_interests: list[str],
) -> str:
    existing = "\n".join(
        f"- {interest}"
        for interest in existing_interests
    )

    return f"""
AUDIENCE FAMILY

{audience_name}

DESCRIPTION

{description}

ALREADY KNOWN / CURATED INTERESTS

{existing}

Generate approximately 100 additional candidate search terms.

Do not merely rephrase the existing interests.

Aim for diversity across these categories:

- genre
- subgenre
- artist
- dj
- label
- collective
- festival
- club
- media
- radio
- platform
- dance
- instrument
- geography
- city_scene
- culture
- adjacent_genre
- lifestyle
- other

For every candidate return:

term
    Exact search phrase we should later send to Meta.

category
    One category from the list above.

rationale
    One concise sentence describing why this term might overlap
    with the {audience_name} audience.

relevance
    high, medium, or exploratory.

search_priority
    Integer from 1 to 5.
    5 = definitely query Meta.
    1 = speculative but potentially useful.

Do NOT estimate audience size.
Do NOT claim the term exists on Meta.
Do NOT recommend spending advertising money on it.

Return exactly:

{{
  "audience": "{audience_name}",
  "candidates": [
    {{
      "term": "example",
      "category": "artist",
      "rationale": "Short explanation.",
      "relevance": "high",
      "search_priority": 5
    }}
  ]
}}
"""


def generate_for_audience(
    audience_name: str,
    config: dict,
) -> list[dict]:
    print(f"Generating candidates for {audience_name}...")

    response = client.responses.create(
        model="gpt-5.6",
        input=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": build_prompt(
                    audience_name=audience_name,
                    description=config["description"],
                    existing_interests=config["existing_interests"],
                ),
            },
        ],
    )

    raw_text = response.output_text

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON returned for {audience_name}")
        print(raw_text)
        raise exc

    return result["candidates"]


def deduplicate_candidates(
    candidates: list[dict],
) -> list[dict]:
    seen = set()
    unique = []

    for candidate in candidates:
        term = candidate["term"].strip()
        key = term.casefold()

        if key in seen:
            continue

        seen.add(key)
        candidate["term"] = term
        unique.append(candidate)

    return unique


def main():
    output = {}

    for audience_name, config in AUDIENCES.items():
        candidates = generate_for_audience(
            audience_name,
            config,
        )

        candidates = deduplicate_candidates(candidates)

        candidates.sort(
            key=lambda x: (
                -x["search_priority"],
                x["category"],
                x["term"].casefold(),
            )
        )

        output[audience_name] = {
            "existing_interests": config["existing_interests"],
            "candidates": candidates,
        }

        print(
            f"{audience_name}: "
            f"{len(candidates)} unique candidates"
        )

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()