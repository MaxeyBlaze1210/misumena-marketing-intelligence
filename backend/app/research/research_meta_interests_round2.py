import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


GRAPH_API_VERSION = "v25.0"


RESEARCH_CONFIG = {
    "afrobeats": {
        "audience_family": "Afrobeats",
        "output_file": "data/meta_interest_afrobeats_round2.json",
        "search_groups": {
            "direct_genre": [
                "Afrobeat",
                "Afrobeats",
                "Afropop",
                "African popular music",
                "Music of Africa",
                "African music",
                "Nigerian music",
                "Ghanaian music",
            ],
            "artist": [
                "Tiwa Savage",
                "Burna Boy",
                "Wizkid",
                "Davido",
                "Tems",
                "Rema",
                "Ayra Starr",
                "Asake",
                "Omah Lay",
                "Fireboy DML",
                "Mr Eazi",
                "CKay",
                "Kizz Daniel",
                "Adekunle Gold",
                "Joeboy",
                "Oxlade",
                "Tekno",
                "Patoranking",
                "Stonebwoy",
                "King Promise",
                "Yemi Alade",
                "Flavour",
                "Simi",
                "Falz",
                "Sarz",
                "Young Jonn",
                "Victony",
                "BNXN",
                "Ruger",
            ],
        },
    },

    "roots": {
        "audience_family": "African Roots",
        "output_file": "data/meta_interest_roots_round2.json",
        "search_groups": {
            "direct_genre": [
                "World music",
                "Music of Africa",
                "African music",
                "African popular music",
                "African folk music",
                "Traditional African music",
                "Afrobeat",
                "Highlife",
                "Soukous",
                "Mbalax",
                "Desert blues",
                "Ethio-jazz",
                "Gnawa",
                "Griot",
                "Mandé music",
                "Kora",
            ],
            "artist": [
                "Fela Kuti",
                "Ali Farka Touré",
                "Vieux Farka Touré",
                "Salif Keita",
                "Youssou N'Dour",
                "Angélique Kidjo",
                "Fatoumata Diawara",
                "Oumou Sangaré",
                "Miriam Makeba",
                "Tinariwen",
                "Baaba Maal",
                "Rokia Traoré",
                "Amadou & Mariam",
                "Toumani Diabaté",
                "Ballaké Sissoko",
                "Bassekou Kouyaté",
                "Habib Koité",
                "Sona Jobarteh",
                "King Sunny Adé",
                "Mulatu Astatke",
                "Orchestra Baobab",
                "Ebo Taylor",
                "Pat Thomas",
                "Bombino",
                "Songhoy Blues",
            ],
        },
    },

    "afrohouse": {
        "audience_family": "Afrohouse",
        "output_file": "data/meta_interest_afrohouse_round2.json",
        "search_groups": {
            "direct_genre": [
                "Afro house",
                "Afrohouse",
                "House music",
                "Deep house",
                "Electronic music",
                "Electronic dance music",
                "Afro tech",
                "Afrotech",
                "Amapiano",
                "Gqom",
                "Kwaito",
                "Organic house",
                "Soulful house",
                "Progressive house",
            ],
            "artist_dj": [
                "Black Coffee",
                "Keinemusik",
                "&ME",
                "Rampa",
                "Adam Port",
                "Shimza",
                "THEMBA",
                "Caiiro",
                "Da Capo",
                "Culoe De Song",
                "Enoo Napa",
                "DJ Kent",
                "Lemon & Herb",
                "Zakes Bantwini",
                "Sun-El Musician",
                "Prince Kaybee",
                "MÖRDA",
                "AMÉMÉ",
                "Boddhi Satva",
                "Francis Mercier",
                "Nitefreak",
                "HUGEL",
                "Major League DJz",
                "Kabza De Small",
                "Kelvin Momo",
                "DBN Gogo",
                "Nkosazana Daughter",
            ],
            "scene_media": [
                "Boiler Room",
                "Mixmag",
                "Resident Advisor",
                "Beatport",
                "SoundCloud",
                "Tomorrowland",
                "Ibiza",
                "Nightclubs",
                "Electronic music festivals",
            ],
        },
    },
}


def get_access_token() -> str:
    token = os.environ.get("META_ACCESS_TOKEN")

    if not token:
        raise RuntimeError(
            "META_ACCESS_TOKEN is not configured. "
            "Load your .env first with: "
            "set -a; source .env; set +a"
        )

    return token


def search_meta_interest(
    term: str,
    access_token: str,
) -> list[dict]:
    url = (
        "https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/search"
    )

    params = {
        "type": "adinterest",
        "q": term,
        "locale": "en_US",
        "limit": 25,
        "access_token": access_token,
    }

    response = httpx.get(
        url,
        params=params,
        timeout=30.0,
    )

    response.raise_for_status()

    return response.json().get(
        "data",
        [],
    )


def normalize(
    text: str | None,
) -> str:
    if not text:
        return ""

    return text.strip().casefold()


def audience_midpoint(
    match: dict,
) -> int | None:
    lower = match.get(
        "audience_size_lower_bound"
    )

    upper = match.get(
        "audience_size_upper_bound"
    )

    if lower is None or upper is None:
        return None

    return round(
        (lower + upper) / 2
    )


def format_size(
    value: int | None,
) -> str:
    if value is None:
        return "unknown"

    if value >= 1_000_000_000:
        return (
            f"{value / 1_000_000_000:.2f}B"
        )

    if value >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f}M"
        )

    if value >= 1_000:
        return (
            f"{value / 1_000:.1f}K"
        )

    return str(value)


def classify_matches(
    term: str,
    matches: list[dict],
) -> tuple[list[dict], list[dict]]:
    normalized_term = normalize(term)

    exact = []
    other = []

    for match in matches:
        enriched = dict(match)

        enriched["audience_size_midpoint"] = (
            audience_midpoint(match)
        )

        if (
            normalize(match.get("name"))
            == normalized_term
        ):
            exact.append(enriched)
        else:
            other.append(enriched)

    return exact, other


def print_match(
    label: str,
    match: dict,
):
    size = format_size(
        match.get(
            "audience_size_midpoint"
        )
    )

    print(
        f"      {label}: "
        f"{match.get('name')} "
        f"| {size} "
        f"| ID {match.get('id')}"
    )


def run_research(
    key: str,
    config: dict,
):
    access_token = get_access_token()

    output_file = Path(
        config["output_file"]
    )

    search_groups = (
        config["search_groups"]
    )

    audience_family = (
        config["audience_family"]
    )

    output = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "graph_api_version":
            GRAPH_API_VERSION,
        "research_round": 2,
        "research_key": key,
        "audience_family":
            audience_family,
        "results": [],
    }

    all_queries = [
        (category, term)
        for category, terms
        in search_groups.items()
        for term in terms
    ]

    total = len(all_queries)

    exact_query_count = 0
    exact_match_count = 0
    no_exact_count = 0
    error_count = 0

    print()
    print("=" * 72)
    print(
        f"{audience_family.upper()} "
        "META INTEREST RESEARCH — ROUND 2"
    )
    print("=" * 72)
    print()

    for index, (
        category,
        term,
    ) in enumerate(
        all_queries,
        start=1,
    ):
        print(
            f"[{index}/{total}] "
            f"{category}: {term}"
        )

        result = {
            "query_term": term,
            "category": category,
            "exact_matches": [],
            "other_matches": [],
        }

        try:
            matches = search_meta_interest(
                term,
                access_token,
            )

            exact, other = classify_matches(
                term,
                matches,
            )

            result["exact_matches"] = exact
            result["other_matches"] = other

            if exact:
                exact_query_count += 1
                exact_match_count += len(
                    exact
                )

                for match in exact:
                    print_match(
                        "EXACT",
                        match,
                    )

            else:
                no_exact_count += 1

                print(
                    "      "
                    "NO EXACT META INTEREST"
                )

            # Fuzzy results are shown only
            # as research leads.
            #
            # They are NOT automatically
            # accepted as valid targets.
            for match in other[:5]:
                print_match(
                    "other",
                    match,
                )

        except httpx.HTTPStatusError as exc:
            error_count += 1

            result["error"] = (
                exc.response.text
            )

            print(
                "      API ERROR: "
                f"{exc.response.status_code}"
            )

            print(
                "      "
                f"{exc.response.text}"
            )

        except Exception as exc:
            error_count += 1

            result["error"] = str(exc)

            print(
                f"      ERROR: {exc}"
            )

        output["results"].append(
            result
        )

        time.sleep(0.15)

    output["summary"] = {
        "queries": total,
        "queries_with_exact_match":
            exact_query_count,
        "exact_matches":
            exact_match_count,
        "queries_without_exact_match":
            no_exact_count,
        "errors":
            error_count,
    }

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_file.open(
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
    print("=" * 72)
    print("ROUND 2 COMPLETE")
    print("=" * 72)

    print(
        f"Queries:             {total}"
    )

    print(
        "Queries with exact:  "
        f"{exact_query_count}"
    )

    print(
        "Exact interests:     "
        f"{exact_match_count}"
    )

    print(
        "No exact interest:   "
        f"{no_exact_count}"
    )

    print(
        f"Errors:              {error_count}"
    )

    print(
        f"Saved to:            {output_file}"
    )


def main():
    if len(sys.argv) != 2:
        print()
        print(
            "Usage:"
        )
        print(
            "  python -m "
            "app.research."
            "research_meta_interests_round2 "
            "<audience>"
        )
        print()
        print(
            "Available audiences:"
        )

        for key in RESEARCH_CONFIG:
            print(
                f"  - {key}"
            )

        raise SystemExit(1)

    key = (
        sys.argv[1]
        .strip()
        .casefold()
    )

    config = RESEARCH_CONFIG.get(
        key
    )

    if config is None:
        print(
            f"Unknown audience: {key}"
        )

        print(
            "Choose one of: "
            + ", ".join(
                RESEARCH_CONFIG
            )
        )

        raise SystemExit(1)

    run_research(
        key,
        config,
    )


if __name__ == "__main__":
    main()
