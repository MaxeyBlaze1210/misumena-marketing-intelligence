from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)


TOTAL_BUDGET = 478.80
DAY = 10
SPENT_SO_FAR = 380.78


CURRENT_DAILY_BUDGETS = {
    "Broad": 4.16,
    "Afrobeat": 3.99,
    "African popular music": 3.82,
}


# Day-10 snapshot copied from Intellijend.
#
# IMPORTANT:
# active=True is intentional.
#
# We want MMI to independently evaluate all 18 cells
# from their accumulated evidence, rather than inheriting
# Intellijend's pause decisions.
DAY10_DATA = {
    "Broad": {
        1: (2.99, 5, 0.60),
        2: (3.81, 9, 0.42),
        3: (4.28, 1, 4.28),
        4: (1.05, 6, 0.18),
        5: (82.26, 278, 0.30),
        6: (31.59, 39, 0.81),
    },

    "Afrobeat": {
        1: (2.82, 11, 0.26),
        2: (12.04, 20, 0.60),
        3: (0.48, 0, None),
        4: (6.17, 20, 0.31),
        5: (68.65, 242, 0.28),
        6: (31.65, 37, 0.86),
    },

    "African popular music": {
        1: (94.36, 264, 0.36),
        2: (6.03, 7, 0.86),
        3: (3.28, 3, 1.09),
        4: (11.52, 24, 0.48),
        5: (9.53, 34, 0.28),
        6: (8.27, 5, 1.65),
    },
}


# We don't have refreshed Day-10 impressions because the
# Meta token expired. Use the last locally imported
# impression counts.
#
# Spend/results/CPR are the Day-10 values above.
LAST_KNOWN_IMPRESSIONS = {
    "Broad": {
        1: 522,
        2: 535,
        3: 599,
        4: 159,
        5: 25546,
        6: 8511,
    },

    "Afrobeat": {
        1: 603,
        2: 1973,
        3: 64,
        4: 1209,
        5: 19509,
        6: 8698,
    },

    "African popular music": {
        1: 23513,
        2: 1032,
        3: 557,
        4: 2204,
        5: 2227,
        6: 2131,
    },
}


INTELLIJEND_DAY10_PAUSED = {
    ("Broad", "Creative 1"),
    ("Broad", "Creative 3"),

    ("Afrobeat", "Creative 2"),
    ("Afrobeat", "Creative 4"),

    ("African popular music", "Creative 2"),
    ("African popular music", "Creative 3"),
    ("African popular music", "Creative 6"),
}


MMI_DAY8_PAUSED = {
    ("Broad", "Creative 2"),
    ("Broad", "Creative 6"),

    ("Afrobeat", "Creative 2"),
    ("Afrobeat", "Creative 6"),

    ("African popular music", "Creative 2"),
    ("African popular music", "Creative 6"),
}


def build_cells():
    cells = []

    for audience, creatives in DAY10_DATA.items():
        for number, values in creatives.items():

            spend, results, cpr = values

            cells.append(
                CampaignCell(
                    audience=audience,
                    creative=f"Creative {number}",
                    impressions=(
                        LAST_KNOWN_IMPRESSIONS[
                            audience
                        ][number]
                    ),
                    spend=spend,
                    results=results,
                    cost_per_result=cpr,
                    active=True,
                    days_active=DAY,
                )
            )

    return cells


def build_current_shares():
    total = sum(
        CURRENT_DAILY_BUDGETS.values()
    )

    return {
        audience: budget / total
        for audience, budget
        in CURRENT_DAILY_BUDGETS.items()
    }


def format_cpr(value):
    if value is None:
        return "N/A"

    return f"€{value:.3f}"


def print_creatives(
    engine,
    cells,
):
    aggregates = (
        engine.build_creative_aggregates(
            cells
        )
    )

    print()
    print("=" * 100)
    print("DAY-10 CROSS-AUDIENCE CREATIVE EVIDENCE")
    print("=" * 100)
    print()

    ordered = sorted(
        aggregates.values(),
        key=lambda item: (
            item["cost_per_result"] is None,
            item["cost_per_result"]
            if item["cost_per_result"] is not None
            else float("inf"),
        ),
    )

    for item in ordered:
        print(
            f"{item['creative']:<12}"
            f"{format_cpr(item['cost_per_result']):<12}"
            f"{item['results']:>5} results"
            f"   €{item['spend']:.2f} spend"
        )


def print_comparison(
    decisions,
):
    mmi_day10_paused = {
        (
            item["audience"],
            item["creative"],
        )
        for item in decisions
        if item["action"] == "pause_candidate"
    }

    all_cells = []

    for audience in DAY10_DATA:
        for number in DAY10_DATA[audience]:
            all_cells.append(
                (
                    audience,
                    f"Creative {number}",
                )
            )

    print()
    print("=" * 100)
    print("DAY-8 MMI vs DAY-10 MMI vs DAY-10 INTELLIJEND")
    print("=" * 100)
    print()

    print(
        f"{'CELL':<43}"
        f"{'MMI D8':<12}"
        f"{'MMI D10':<12}"
        f"{'INT D10':<12}"
    )

    print("-" * 100)

    for audience, creative in all_cells:

        key = (
            audience,
            creative,
        )

        d8 = (
            "PAUSE"
            if key in MMI_DAY8_PAUSED
            else "KEEP"
        )

        d10 = (
            "PAUSE"
            if key in mmi_day10_paused
            else "KEEP"
        )

        intellijend = (
            "PAUSE"
            if key in INTELLIJEND_DAY10_PAUSED
            else "RUN"
        )

        marker = ""

        if (
            (d10 == "PAUSE")
            == (intellijend == "PAUSE")
        ):
            marker = "✓"
        else:
            marker = "← DIFFER"

        cell_name = (
            f"{audience} × {creative}"
        )

        print(
            f"{cell_name:<43}"
            f"{d8:<12}"
            f"{d10:<12}"
            f"{intellijend:<12}"
            f"{marker}"
        )

    overlap = (
        mmi_day10_paused
        & INTELLIJEND_DAY10_PAUSED
    )

    mmi_only = (
        mmi_day10_paused
        - INTELLIJEND_DAY10_PAUSED
    )

    intellijend_only = (
        INTELLIJEND_DAY10_PAUSED
        - mmi_day10_paused
    )

    print()
    print("=" * 100)
    print("COMPARISON SUMMARY")
    print("=" * 100)

    print()
    print(
        f"MMI Day-10 pauses:          "
        f"{len(mmi_day10_paused)}"
    )

    print(
        f"Intellijend Day-10 pauses:  "
        f"{len(INTELLIJEND_DAY10_PAUSED)}"
    )

    print(
        f"Same pause decisions:       "
        f"{len(overlap)}"
    )

    print()

    print("BOTH PAUSE")
    print("-" * 100)

    for audience, creative in sorted(overlap):
        print(
            f"- {audience} × {creative}"
        )

    print()
    print("MMI PAUSES / INTELLIJEND RUNS")
    print("-" * 100)

    if not mmi_only:
        print("- None")

    for audience, creative in sorted(mmi_only):
        print(
            f"- {audience} × {creative}"
        )

    print()
    print("INTELLIJEND PAUSES / MMI KEEPS")
    print("-" * 100)

    if not intellijend_only:
        print("- None")

    for audience, creative in sorted(
        intellijend_only
    ):
        print(
            f"- {audience} × {creative}"
        )


def main():
    cells = build_cells()

    engine = ExecutionEngine()

    print()
    print("=" * 100)
    print("IFE TUTU — MMI DAY-10 EXECUTION BENCHMARK")
    print("=" * 100)

    print()
    print(
        f"Cells:             {len(cells)}"
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

    print_creatives(
        engine,
        cells,
    )

    proposal = engine.propose_day(
        total_budget=TOTAL_BUDGET,
        day=DAY,
        spent_so_far=SPENT_SO_FAR,
        cells=cells,
        current_audience_shares=
            build_current_shares(),
    )

    print_comparison(
        proposal["cell_decisions"]
    )

    print()
    print("=" * 100)
    print("MMI DAY-10 AUDIENCE ALLOCATION")
    print("=" * 100)
    print()

    print(
        f"Daily target: "
        f"€{proposal['daily_target']:.2f}"
    )

    for item in proposal[
        "audience_allocations"
    ]:
        print(
            f"{item['audience']:<28}"
            f"{item['share'] * 100:>6.1f}%"
            f"   "
            f"€{item['proposed_daily_budget']:.2f}/day"
            f"   CPR "
            f"{format_cpr(item['cost_per_result'])}"
        )

    if proposal["warnings"]:
        print()
        print("WARNINGS")

        for warning in proposal[
            "warnings"
        ]:
            print(
                f"- {warning}"
            )

    print()


if __name__ == "__main__":
    main()
