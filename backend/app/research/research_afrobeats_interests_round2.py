import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


GRAPH_API_VERSION = "v25.0"
ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]

OUTPUT_FILE = Path(
    "data/meta_interest_afrobeats_round2.json"
)


# ---------------------------------------------------------
# Curated Round-2 search vocabulary
#
# This is deliberately NOT LLM-generated.
# We want to answer a concrete question:
#
# Which useful Afrobeats-related interests actually exist
# in Meta's ad-interest search?
# ---------------------------------------------------------

SEARCH_GROUPS = {
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
}


def search_meta_interest(term: str) -> list[dict]:
    url = (
        "https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/search"
    )

    params = {
        "type": "adinterest",
        "q": term,
        "locale": "en_US",
        "limit": 25,
        "access_token": ACCESS_TOKEN,
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


def normalize(text: str | None) -> str:
    if not text:
        return ""

    return (
        text
        .strip()
        .casefold()
    )


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

        if normalize(
            match.get("name")
        ) == normalized_term:
            exact.append(enriched)
        else:
            other.append(enriched)

    return exact, other


def print_exact_match(
    match: dict,
):
    size = format_size(
        match.get(
            "audience_size_midpoint"
        )
    )

    print(
        f"      EXACT: "
        f"{match.get('name')} "
        f"| {size} "
        f"| ID {match.get('id')}"
    )


def print_other_match(
    match: dict,
):
    size = format_size(
        match.get(
            "audience_size_midpoint"
        )
    )

    print(
        f"      other: "
        f"{match.get('name')} "
        f"| {size} "
        f"| ID {match.get('id')}"
    )


def main():
    output = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "graph_api_version":
            GRAPH_API_VERSION,

        "research_round": 2,

        "audience_family":
            "Afrobeats",

        "results": [],
    }

    all_queries = [
        (category, term)
        for category, terms
        in SEARCH_GROUPS.items()
        for term in terms
    ]

    total = len(all_queries)

    exact_count = 0
    no_exact_count = 0

    print()
    print("=" * 72)
    print(
        "AFROBEATS META INTEREST RESEARCH — ROUND 2"
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
                term
            )

            exact, other = classify_matches(
                term,
                matches,
            )

            result["exact_matches"] = exact
            result["other_matches"] = other

            if exact:
                exact_count += 1

                for match in exact:
                    print_exact_match(match)

            else:
                no_exact_count += 1

                print(
                    "      NO EXACT META INTEREST"
                )

            # Show up to five fuzzy results.
            #
            # These are NOT automatically accepted.
            # They are useful for discovering things
            # such as naming differences.
            for match in other[:5]:
                print_other_match(match)

        except httpx.HTTPStatusError as exc:
            result["error"] = (
                exc.response.text
            )

            print(
                "      API ERROR: "
                f"{exc.response.status_code}"
            )

        except Exception as exc:
            result["error"] = str(exc)

            print(
                f"      ERROR: {exc}"
            )

        output["results"].append(
            result
        )

        # Keep the research run gentle on
        # the Graph API.
        time.sleep(0.15)

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
    print("=" * 72)
    print("ROUND 2 COMPLETE")
    print("=" * 72)

    print(
        f"Queries:             {total}"
    )

    print(
        f"Exact interests:     {exact_count}"
    )

    print(
        f"No exact interest:   {no_exact_count}"
    )

    print(
        f"Saved to:            {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
