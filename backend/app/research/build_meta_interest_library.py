import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


INPUT_FILE = Path("data/meta_interest_search_results.json")
OUTPUT_FILE = Path("data/meta_interest_library.json")


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        source = json.load(f)

    interests = {}

    total_matches = 0

    for audience_name, query_results in source["audiences"].items():

        for query_result in query_results:

            query_term = query_result["query_term"]
            query_category = query_result["query_category"]
            query_priority = query_result["query_priority"]

            for match in query_result.get("matches", []):
                total_matches += 1

                meta_id = str(match["id"])

                if meta_id not in interests:
                    interests[meta_id] = {
                        "meta_interest_id": meta_id,
                        "name": match.get("name"),
                        "audience_size_lower_bound":
                            match.get("audience_size_lower_bound"),
                        "audience_size_upper_bound":
                            match.get("audience_size_upper_bound"),
                        "path": match.get("path"),
                        "description": match.get("description"),
                        "topic": match.get("topic"),

                        "audience_families": set(),
                        "discovered_by": [],
                    }

                interest = interests[meta_id]

                interest["audience_families"].add(
                    audience_name
                )

                interest["discovered_by"].append(
                    {
                        "audience_family": audience_name,
                        "query_term": query_term,
                        "query_category": query_category,
                        "query_priority": query_priority,
                    }
                )

    # Convert sets to sorted lists so JSON can serialize them.
    library = []

    for interest in interests.values():

        interest["audience_families"] = sorted(
            interest["audience_families"]
        )

        # Useful derived value for later ranking.
        lower = interest["audience_size_lower_bound"]
        upper = interest["audience_size_upper_bound"]

        if lower is not None and upper is not None:
            interest["audience_size_midpoint"] = round(
                (lower + upper) / 2
            )
        else:
            interest["audience_size_midpoint"] = None

        interest["discovery_count"] = len(
            interest["discovered_by"]
        )

        library.append(interest)

    # Sort largest audiences first for now.
    # This is NOT a quality ranking.
    library.sort(
        key=lambda x: (
            x["audience_size_midpoint"] is not None,
            x["audience_size_midpoint"] or 0,
        ),
        reverse=True,
    )

    output = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "source_file": str(INPUT_FILE),

        "summary": {
            "raw_meta_matches": total_matches,
            "unique_meta_interests": len(library),
        },

        "interests": library,
    }

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
    print("META INTEREST LIBRARY")
    print("=" * 70)
    print(f"Raw Meta matches:      {total_matches}")
    print(f"Unique Meta interests: {len(library)}")
    print(f"Saved to:              {OUTPUT_FILE}")
    print()

    print("Top 30 by audience size")
    print("-" * 70)

    for interest in library[:30]:

        midpoint = interest["audience_size_midpoint"]

        if midpoint is None:
            size = "unknown"
        elif midpoint >= 1_000_000_000:
            size = f"{midpoint / 1_000_000_000:.2f}B"
        elif midpoint >= 1_000_000:
            size = f"{midpoint / 1_000_000:.1f}M"
        elif midpoint >= 1_000:
            size = f"{midpoint / 1_000:.1f}K"
        else:
            size = str(midpoint)

        families = ", ".join(
            interest["audience_families"]
        )

        print(
            f"{size:>8} | "
            f"{interest['name']:<35} | "
            f"{families}"
        )


if __name__ == "__main__":
    main()