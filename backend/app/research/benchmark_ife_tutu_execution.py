import re

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)
from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_metric import MetaAdSetMetric


TOTAL_BUDGET = 478.80
DAY = 8
SPENT_SO_FAR = 348.25


# Current Intellijend audience budgets from Day 8.
CURRENT_DAILY_BUDGETS = {
    "Broad": 5.83,
    "Afrobeat": 5.58,
    "African popular music": 5.34,
}


NAME_PATTERN = re.compile(
    r"^\[intellijend\].*? - "
    r"(Broad|Interest: .+?) - "
    r"Ife Tutu Creative (\d+)$",
    re.IGNORECASE,
)


def parse_name(
    name: str,
):
    match = NAME_PATTERN.match(
        name
    )

    if match is None:
        return None

    audience_raw = (
        match.group(1)
        .strip()
    )

    creative_number = int(
        match.group(2)
    )

    if audience_raw.casefold() == "broad":
        audience = "Broad"
    else:
        audience = (
            audience_raw
            .split(":", 1)[1]
            .strip()
        )

    return {
        "audience": audience,
        "creative": (
            f"Creative {creative_number}"
        ),
        "creative_number":
            creative_number,
    }


def get_latest_metric(
    db,
    adset_id: int,
):
    return (
        db.query(MetaAdSetMetric)
        .filter(
            MetaAdSetMetric.adset_id
            == adset_id
        )
        .order_by(
            MetaAdSetMetric.date_stop.desc(),
            MetaAdSetMetric.date_start.desc(),
        )
        .first()
    )


def build_cells(
    db,
) -> list[CampaignCell]:

    adsets = (
        db.query(MetaAdSet)
        .filter(
            MetaAdSet.name.like(
                "[intellijend]%"
            )
        )
        .all()
    )

    cells = []

    for adset in adsets:

        parsed = parse_name(
            adset.name
        )

        if parsed is None:
            continue

        metric = get_latest_metric(
            db,
            adset.id,
        )

        if metric is None:
            continue

        results = (
            int(metric.results)
            if metric.results is not None
            else 0
        )

        spend = float(
            metric.spend or 0
        )

        if (
            metric.cost_per_result
            is not None
        ):
            cpr = float(
                metric.cost_per_result
            )

        elif results > 0:
            cpr = (
                spend / results
            )

        else:
            cpr = None

        # IMPORTANT:
        #
        # We intentionally set active=True for every cell,
        # including cells Intellijend already paused.
        #
        # This lets us independently ask what MMI would
        # recommend from the accumulated evidence.
        cells.append(
            CampaignCell(
                audience=parsed[
                    "audience"
                ],

                creative=parsed[
                    "creative"
                ],

                impressions=int(
                    metric.impressions or 0
                ),

                spend=spend,

                results=results,

                cost_per_result=cpr,

                active=True,

                # Day 8 means all cells have passed
                # the initial exploration protection.
                days_active=DAY,
            )
        )

    return cells


def build_current_shares():
    total = sum(
        CURRENT_DAILY_BUDGETS.values()
    )

    return {
        audience:
            budget / total

        for audience, budget
        in CURRENT_DAILY_BUDGETS.items()
    }


def print_creative_aggregates(
    engine,
    cells,
):
    aggregates = (
        engine.build_creative_aggregates(
            cells
        )
    )

    print()
    print("=" * 88)
    print("CROSS-AUDIENCE CREATIVE PERFORMANCE")
    print("=" * 88)
    print()

    ordered = sorted(
        aggregates.values(),
        key=lambda item: (
            item["cost_per_result"]
            is None,
            item["cost_per_result"]
            if item[
                "cost_per_result"
            ] is not None
            else float("inf"),
        ),
    )

    for item in ordered:

        if (
            item["cost_per_result"]
            is not None
        ):
            cpr_text = (
                f"€"
                f"{item['cost_per_result']:.3f}"
            )
        else:
            cpr_text = "N/A"

        print(
            f"{item['creative']:<12} "
            f"{cpr_text:<10} "
            f"{item['results']:>5} results "
            f"| €{item['spend']:.2f} spend "
            f"| {item['impressions']} impressions"
        )


def print_cell_decisions(
    decisions,
):
    print()
    print("=" * 88)
    print("CELL DECISIONS")
    print("=" * 88)

    audience_order = [
        "Broad",
        "Afrobeat",
        "African popular music",
    ]

    for audience in audience_order:

        print()
        print(audience.upper())
        print("-" * 88)

        audience_rows = [
            item
            for item in decisions
            if item["audience"]
            == audience
        ]

        audience_rows.sort(
            key=lambda item:
                int(
                    item["creative"]
                    .split()[-1]
                )
        )

        for item in audience_rows:

            cpr = (
                f"€{item['cost_per_result']:.3f}"
                if item[
                    "cost_per_result"
                ] is not None
                else "N/A"
            )

            aggregate = (
                item[
                    "creative_aggregate"
                ]
            )

            aggregate_cpr = (
                aggregate[
                    "cost_per_result"
                ]
            )

            aggregate_text = (
                f"€{aggregate_cpr:.3f}"
                if aggregate_cpr
                is not None
                else "N/A"
            )

            replication = (
                item["replication"]
            )

            print()
            print(
                f"{item['creative']}"
            )

            print(
                f"  Cell:       "
                f"{cpr} CPR | "
                f"{item['results']} results | "
                f"€{item['spend']:.2f} spend | "
                f"{item['impressions']} impressions"
            )

            print(
                f"  Creative:   "
                f"{aggregate_text} combined CPR | "
                f"{aggregate['results']} results"
            )

            if (
                replication[
                    "comparisons"
                ] > 0
            ):
                print(
                    f"  Replication:"
                    f" trails best creative in "
                    f"{replication['worse_count']}/"
                    f"{replication['comparisons']} "
                    f"audiences"
                )

            print(
                f"  Decision:   "
                f"{item['action'].upper()}"
            )

            print(
                f"  Reason:     "
                f"{item['reason']}"
            )


def print_pause_summary(
    decisions,
):
    pause_candidates = [
        item
        for item in decisions
        if item["action"]
        == "pause_candidate"
    ]

    print()
    print("=" * 88)
    print("MMI PAUSE CANDIDATES")
    print("=" * 88)
    print()

    if not pause_candidates:
        print(
            "None."
        )
    else:
        for item in pause_candidates:
            print(
                f"- {item['audience']} × "
                f"{item['creative']}"
            )

    print()
    print("ACTUAL INTELLIJEND PAUSES")
    print("-" * 88)

    print(
        "- Afrobeat × Creative 2"
    )

    print(
        "- African popular music × Creative 2"
    )


def print_audience_allocation(
    proposal,
):
    print()
    print("=" * 88)
    print("AUDIENCE ALLOCATION")
    print("=" * 88)
    print()

    print(
        f"Day {proposal['day']}"
        f" | mode: {proposal['mode']}"
    )

    print(
        f"Daily target: "
        f"€{proposal['daily_target']:.2f}"
    )

    print()

    for item in proposal[
        "audience_allocations"
    ]:

        print(
            f"{item['audience']:<26}"
            f"{item['share'] * 100:>6.1f}%"
            f"   "
            f"€{item['proposed_daily_budget']:.2f}/day"
            f"   "
            f"CPR "
            f"{'€' + format(item['cost_per_result'], '.3f') if item['cost_per_result'] is not None else 'N/A'}"
        )


def main():
    db = SessionLocal()

    try:
        cells = build_cells(
            db
        )

    finally:
        db.close()

    print()
    print("=" * 88)
    print("IFE TUTU — MMI DAY 8 EXECUTION BENCHMARK")
    print("=" * 88)

    print()
    print(
        f"Cells loaded:      {len(cells)}"
    )

    print(
        f"Total budget:      €{TOTAL_BUDGET:.2f}"
    )

    print(
        f"Spent so far:      €{SPENT_SO_FAR:.2f}"
    )

    print(
        f"Campaign day:      {DAY}"
    )

    if len(cells) != 18:
        print()
        print(
            "WARNING: expected 18 Ife Tutu cells."
        )

    engine = ExecutionEngine()

    print_creative_aggregates(
        engine,
        cells,
    )

    proposal = engine.propose_day(
        total_budget=
            TOTAL_BUDGET,

        day=
            DAY,

        spent_so_far=
            SPENT_SO_FAR,

        cells=
            cells,

        current_audience_shares=
            build_current_shares(),
    )

    print_cell_decisions(
        proposal[
            "cell_decisions"
        ]
    )

    print_pause_summary(
        proposal[
            "cell_decisions"
        ]
    )

    print_audience_allocation(
        proposal
    )

    if proposal["warnings"]:
        print()
        print("=" * 88)
        print("WARNINGS")
        print("=" * 88)

        for warning in proposal[
            "warnings"
        ]:
            print(
                f"- {warning}"
            )

    print()


if __name__ == "__main__":
    main()
