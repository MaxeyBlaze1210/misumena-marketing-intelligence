import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)
from app.models.meta_adset import MetaAdSet
from app.research.benchmark_ife_tutu_live import (
    latest_metric,
    parse_name,
)


TOTAL_BUDGET = 478.80
DAY = 11


def load_cells():
    db = SessionLocal()

    try:
        adsets = (
            db.query(MetaAdSet)
            .filter(
                MetaAdSet.name.like(
                    "[intellijend] misumena - Ife Tutu%"
                )
            )
            .all()
        )

        cells = []
        actual = {}

        for adset in adsets:

            parsed = parse_name(
                adset.name
            )

            if parsed is None:
                continue

            audience, creative = parsed

            metric = latest_metric(
                db,
                adset.id,
            )

            if metric is None:
                continue

            results = int(
                metric.results or 0
            )

            spend = float(
                metric.spend or 0
            )

            if metric.cost_per_result is not None:
                cpr = float(
                    metric.cost_per_result
                )

            elif results > 0:
                cpr = (
                    spend / results
                )

            else:
                cpr = None

            # Independent benchmark:
            #
            # MMI is allowed to evaluate all 18 cells,
            # regardless of Intellijend's current status.
            cells.append(
                CampaignCell(
                    audience=audience,
                    creative=creative,
                    impressions=int(
                        metric.impressions or 0
                    ),
                    spend=spend,
                    results=results,
                    cost_per_result=cpr,
                    active=True,
                    days_active=DAY,
                )
            )

            actual[
                (
                    audience,
                    creative,
                )
            ] = (
                "PAUSED"
                if adset.effective_status
                == "PAUSED"
                else "RUN"
            )

        return (
            cells,
            actual,
        )

    finally:
        db.close()


def main():

    cells, actual = load_cells()

    spent_so_far = sum(
        cell.spend
        for cell in cells
    )

    engine = ExecutionEngine()

    proposal = engine.propose_day(
        total_budget=TOTAL_BUDGET,
        day=DAY,
        spent_so_far=spent_so_far,
        cells=cells,
        current_audience_shares={
            "Broad": 1 / 3,
            "Afrobeat": 1 / 3,
            "African popular music": 1 / 3,
        },
    )

    plan = proposal[
        "execution_plan"
    ]

    execution = plan[
        "execution"
    ]

    print()
    print("=" * 112)
    print(
        "IFE TUTU — LIVE BUDGET-PRESSURE BENCHMARK"
    )
    print("=" * 112)

    print()
    print(
        f"Day:                    {DAY}"
    )

    print(
        f"Spend captured:         "
        f"€{spent_so_far:.2f}"
    )

    print(
        f"Daily target:           "
        f"€{proposal['daily_target']:.2f}"
    )

    print(
        f"Cells before pruning:   "
        f"{plan['active_before']}"
    )

    print(
        f"Cells after pruning:    "
        f"{plan['active_after']}"
    )

    print(
        f"Paused for budget:      "
        f"{plan['paused_for_budget']}"
    )

    print()
    print("AUDIENCE CAPACITY")
    print("-" * 112)

    for allocation in proposal[
        "audience_allocations"
    ]:

        audience = allocation[
            "audience"
        ]

        rows = [
            item
            for item in execution
            if (
                item["audience"]
                == audience
                and item[
                    "execution_action"
                ]
                != "remain_paused"
            )
        ]

        capacity = (
            rows[0][
                "audience_capacity"
            ]
            if rows
            else 0
        )

        print(
            f"{audience:<28}"
            f"€{allocation['proposed_daily_budget']:.2f}/day"
            f"   capacity {capacity} cells"
        )

    print()
    print(
        f"{'CELL':<45}"
        f"{'SCORE':<9}"
        f"{'MMI':<12}"
        f"{'ACTUAL':<10}"
    )

    print("-" * 112)

    order = {
        "Broad": 1,
        "Afrobeat": 2,
        "African popular music": 3,
    }

    execution.sort(
        key=lambda item: (
            order.get(
                item["audience"],
                99,
            ),
            item.get(
                "rank_within_audience",
                99,
            ),
        )
    )

    agreements = 0
    compared = 0

    for item in execution:

        if (
            item["execution_action"]
            == "remain_paused"
        ):
            continue

        key = (
            item["audience"],
            item["creative"],
        )

        mmi = (
            "RUN"
            if item[
                "execution_action"
            ] == "run"
            else "PAUSE"
        )

        actual_state = actual[
            key
        ]

        # Normalize RUN/PAUSE versus RUN/PAUSED.
        same = (
            (mmi == "PAUSE")
            ==
            (actual_state == "PAUSED")
        )

        compared += 1

        if same:
            agreements += 1

        marker = (
            "✓"
            if same
            else "← DIFFER"
        )

        cell_name = (
            f"{item['audience']} × "
            f"{item['creative']}"
        )

        print(
            f"{cell_name:<45}"
            f"{item['pruning_priority']:<9.2f}"
            f"{mmi:<12}"
            f"{actual_state:<10}"
            f"{marker}"
        )

    print()
    print("=" * 112)
    print("MMI PROPOSED PAUSES")
    print("=" * 112)

    for item in execution:

        if (
            item["execution_action"]
            == "pause_budget_pressure"
        ):
            print(
                f"- {item['audience']} × "
                f"{item['creative']} "
                f"(score "
                f"{item['pruning_priority']:.2f})"
            )

    print()

    percentage = (
        agreements
        / compared
        * 100
        if compared
        else 0
    )

    print(
        "Agreement with current Meta state: "
        f"{agreements}/{compared} "
        f"({percentage:.1f}%)"
    )

    print()


if __name__ == "__main__":
    main()
