from app.intelligence.rules import META_RULES
from app.intelligence.execution_engine import (
    ExecutionEngine,
)

from app.research.benchmark_ife_tutu_budget_pressure import (
    DAY,
    TOTAL_BUDGET,
    load_cells,
)


FLOORS = [
    1.00,
    1.05,
    1.10,
    1.15,
    1.20,
    1.25,
    1.30,
    1.35,
    1.40,
    1.50,
]


def main():

    cells, actual = load_cells()

    spent_so_far = sum(
        cell.spend
        for cell in cells
    )

    original_floor = META_RULES[
        "min_daily_budget_per_active_cell"
    ]

    print()
    print("=" * 100)
    print(
        "IFE TUTU — MINIMUM CELL BUDGET SWEEP"
    )
    print("=" * 100)

    print()
    print(
        f"{'FLOOR':<10}"
        f"{'ACTIVE':<10}"
        f"{'PAUSED':<10}"
        f"{'AGREE':<12}"
        f"{'CAPACITY BY AUDIENCE'}"
    )

    print("-" * 100)

    try:

        for floor in FLOORS:

            META_RULES[
                "min_daily_budget_per_active_cell"
            ] = floor

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

            agreements = 0
            compared = 0

            capacities = {}

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

                mmi_paused = (
                    item["execution_action"]
                    == "pause_budget_pressure"
                )

                actual_paused = (
                    actual[key]
                    == "PAUSED"
                )

                if (
                    mmi_paused
                    == actual_paused
                ):
                    agreements += 1

                compared += 1

                capacities[
                    item["audience"]
                ] = item[
                    "audience_capacity"
                ]

            capacity_text = (
                f"Broad {capacities.get('Broad', 0)} · "
                f"Afrobeat {capacities.get('Afrobeat', 0)} · "
                f"African Pop "
                f"{capacities.get('African popular music', 0)}"
            )

            percentage = (
                agreements
                / compared
                * 100
                if compared
                else 0.0
            )

            print(
                f"€{floor:<9.2f}"
                f"{plan['active_after']:<10}"
                f"{plan['paused_for_budget']:<10}"
                f"{agreements}/{compared} "
                f"({percentage:>5.1f}%)   "
                f"{capacity_text}"
            )

    finally:

        META_RULES[
            "min_daily_budget_per_active_cell"
        ] = original_floor

    print()


if __name__ == "__main__":
    main()
