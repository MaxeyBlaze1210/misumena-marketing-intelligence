import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


GRAPH_API_VERSION = "v25.0"

ACCESS_TOKEN = os.environ["META_ACCESS_TOKEN"]

INPUT_FILE = Path("data/meta_interest_candidates.json")
OUTPUT_FILE = Path("data/meta_interest_search_results.json")


def search_meta_interest(term: str):
    url = (
        f"https://graph.facebook.com/"
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

    return response.json().get("data", [])


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        source = json.load(f)

    output = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "graph_api_version": GRAPH_API_VERSION,
        "audiences": {},
    }

    total_queries = sum(
        len(content["candidates"])
        for content in source.values()
    )

    query_number = 0

    for audience_name, content in source.items():

        print()
        print("=" * 70)
        print(audience_name)
        print("=" * 70)

        audience_results = []

        for candidate in content["candidates"]:
            query_number += 1

            term = candidate["term"]

            print(
                f"[{query_number}/{total_queries}] "
                f"{term}",
                end="",
                flush=True,
            )

            try:
                matches = search_meta_interest(term)

                print(f" -> {len(matches)} matches")

                audience_results.append(
                    {
                        "query_term": term,
                        "query_category": candidate["category"],
                        "query_rationale": candidate["rationale"],
                        "query_relevance": candidate["relevance"],
                        "query_priority": candidate[
                            "search_priority"
                        ],
                        "matches": matches,
                    }
                )

            except httpx.HTTPStatusError as exc:
                print(f" -> ERROR {exc.response.status_code}")

                audience_results.append(
                    {
                        "query_term": term,
                        "query_category": candidate["category"],
                        "query_rationale": candidate["rationale"],
                        "query_relevance": candidate["relevance"],
                        "query_priority": candidate[
                            "search_priority"
                        ],
                        "matches": [],
                        "error": exc.response.text,
                    }
                )

            # Be polite to the API and make the annual
            # research job easier to debug.
            time.sleep(0.15)

        output["audiences"][audience_name] = audience_results

        # Save after every audience so we don't lose
        # everything if a later request fails.
        OUTPUT_FILE.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with OUTPUT_FILE.open(
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                output,
                f,
                ensure_ascii=False,
                indent=2,
            )

    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()