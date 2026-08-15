import json
from pathlib import Path

from openai import OpenAI


INPUT_FILE = Path("data/meta_interest_library.json")
OUTPUT_FILE = Path("data/meta_interest_scored.json")

client = OpenAI()


AUDIENCE_DESCRIPTIONS = {
    "African Roots": (
        "African roots, traditional African music, African folk, "
        "world music, acoustic African music, traditional instruments, "
        "regional African music traditions and adjacent audiences."
    ),
    "Afrobeats": (
        "Modern Afrobeats, Afropop, West African pop, African popular music, "
        "contemporary African mainstream music, dance-oriented African pop "
        "and adjacent audiences."
    ),
    "Afrohouse": (
        "Afro House, African electronic music, house music with African influences, "
        "South African electronic scenes, Afro-tech, soulful/organic/deep house, "
        "Amapiano-adjacent audiences, DJs, clubs, festivals and electronic music culture."
    ),
}


SYSTEM_PROMPT = """
You are evaluating Meta Ads interests for music marketing research.

Your job is to assess SEMANTIC RELEVANCE only.

Do NOT decide whether an interest is a good advertising target based on audience size.
Do NOT reward an interest just because it has a very large audience.
Do NOT assume that an interest is relevant simply because Meta returned it from a search.

Meta's targeting search is fuzzy and often returns unrelated results.

Examples of obvious false positives include:
- "Tea"
- "Coupons"
- "Insurance"
- "Technology"
- "House Beautiful"
when evaluating music audiences.

Evaluate whether each Meta interest is meaningfully related to the supplied
music audience family.

Use these labels:

relevant
    Strong and defensible relationship to the audience.

plausible
    Some meaningful overlap, but broader, adjacent, indirect, or uncertain.

irrelevant
    No useful relationship to this music audience.

Score relevance from 0 to 100.

Important:
- 90-100 = extremely strong/direct match
- 75-89 = strong
- 50-74 = plausible/adjacent
- 25-49 = weak
- 0-24 = irrelevant or essentially noise

Consider:
- genre fit
- artist or DJ fit
- label/collective fit
- scene/community fit
- festival/club/media/platform fit
- cultural relevance
- adjacent genre relevance

Be conservative.
A broad generic interest like "Music" should not receive a high score merely
because all music listeners are technically relevant.

Return valid JSON only.
"""


def build_prompt(
    audience_name: str,
    audience_description: str,
    interest: dict,
) -> str:
    discovery_terms = sorted(
        {
            item["query_term"]
            for item in interest["discovered_by"]
            if item["audience_family"] == audience_name
        }
    )

    discovery_text = "\n".join(
        f"- {term}"
        for term in discovery_terms
    )

    return f"""
AUDIENCE FAMILY

{audience_name}

AUDIENCE DESCRIPTION

{audience_description}

META INTEREST

Name:
{interest["name"]}

Meta ID:
{interest["meta_interest_id"]}

Meta path:
{interest.get("path")}

Meta topic:
{interest.get("topic")}

Meta description:
{interest.get("description")}

Audience size lower bound:
{interest.get("audience_size_lower_bound")}

Audience size upper bound:
{interest.get("audience_size_upper_bound")}

This Meta interest was discovered through these search terms:

{discovery_text}

Evaluate the semantic relevance of this Meta interest to the audience family.

Return exactly:

{{
  "label": "relevant",
  "relevance_score": 92,
  "reason": "One concise sentence."
}}
"""


def score_interest_for_audience(
    audience_name: str,
    interest: dict,
) -> dict:
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
                    audience_description=AUDIENCE_DESCRIPTIONS[
                        audience_name
                    ],
                    interest=interest,
                ),
            },
        ],
    )

    return json.loads(response.output_text)


def main():
    with INPUT_FILE.open(encoding="utf-8") as f:
        source = json.load(f)

    scored_interests = []

    total_pairs = sum(
        len(interest["audience_families"])
        for interest in source["interests"]
    )

    current = 0

    for interest in source["interests"]:
        audience_scores = {}

        for audience_name in interest["audience_families"]:
            current += 1

            print(
                f"[{current}/{total_pairs}] "
                f"{audience_name} -> {interest['name']}",
                end="",
                flush=True,
            )

            try:
                score = score_interest_for_audience(
                    audience_name,
                    interest,
                )

                audience_scores[audience_name] = score

                print(
                    f" -> "
                    f"{score['label']} "
                    f"{score['relevance_score']}"
                )

            except Exception as exc:
                print(f" -> ERROR: {exc}")

                audience_scores[audience_name] = {
                    "label": "error",
                    "relevance_score": None,
                    "reason": str(exc),
                }

        scored_interest = dict(interest)
        scored_interest["audience_scores"] = audience_scores

        scored_interests.append(scored_interest)

    output = {
        "source_file": str(INPUT_FILE),
        "interests": scored_interests,
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
    print("DONE")
    print("=" * 70)
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()