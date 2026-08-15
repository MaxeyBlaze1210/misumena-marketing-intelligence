import re

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)
from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_metric import MetaAdSetMetric


NAME_PATTERN = re.compile(
    r"^\[intellijend\].*? - "
    r"(Broad|Interest: .+?) - "
    r"Ife Tutu Creative (\d+)$",
    re.IGNORECASE,
)


def parse_name(name: str):
    match = NAME_PATTERN.match(name)

    if match is None:
        return None

    audience_raw = match.group(1).strip()

    if audience_raw.casefold() == "broad":
        audience = "Broad"
    else:
        audience = (
            audience_raw
            .split(":", 1)[1]
            .strip()
        )

    creative = (
        f"Creative {int(match.group(2))}"
    )

    return audience, creative


def latest_metric(db, adset_id):
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


def main():
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
        actual_status = {}

        for adset in adsets:
            parsed = parse_name(adset.name)

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
                cpr = spend / results
            else:
                cpr = None

            # Important:
            # MMI independently evaluates every cell,
            # even if Intellijend has already paused it.
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
                    days_active=99,
                )
            )

            actual_status[
                (audience, creative)
            ] = (
                "PAUSED"
                if adset.effective_status == "PAUSED"
                else "RUN"
            )

    finally:
        db.close()

    engine = ExecutionEngine()

    decisions = engine.evaluate_cells(
        cells
    )

    mmi_status = {
        (
            item["audience"],
            item["creative"],
        ): (
            "PAUSE"
            if item["action"]
            == "pause_candidate"
            else "KEEP"
        )
        for item in decisions
    }

    aggregates = (
        engine.build_creative_aggregates(
            cells
        )
    )

    print()
    print("=" * 100)
    print("IFE TUTU — LIVE MMI vs META / INTELLIJEND")
    print("=" * 100)

    print()
    print(f"Cells loaded: {len(cells)}")

    actual_paused = sum(
        1
        for status
        in actual_status.values()
        if status == "PAUSED"
    )

    print(
        f"Actual paused: {actual_paused}"
        f" / {len(cells)}"
    )

    print()
    print("CREATIVE AGGREGATES")
    print("-" * 100)

    for item in sorted(
        aggregates.values(),
        key=lambda x:
            x["cost_per_result"]
            if x["cost_per_result"]
            is not None
            else float("inf"),
    ):
        cpr = (
            f"€{item['cost_per_result']:.3f}"
            if item["cost_per_result"]
            is not None
            else "N/A"
        )

        print(
            f"{item['creative']:<12}"
            f"{cpr:<10}"
            f"{item['results']:>5} results"
            f"   €{item['spend']:.2f}"
        )

    print()
    print(
        f"{'CELL':<43}"
        f"{'MMI':<12}"
        f"{'ACTUAL':<12}"
    )
    print("-" * 100)

    order = {
        "Broad": 1,
        "Afrobeat": 2,
        "African popular music": 3,
    }

    keys = sorted(
        actual_status,
        key=lambda key: (
            order.get(key[0], 99),
            int(key[1].split()[-1]),
        ),
    )

    agreements = 0

    for key in keys:
        audience, creative = key

        mmi = mmi_status.get(
            key,
            "?"
        )

        actual = actual_status[key]

        same = (
            (mmi == "PAUSE")
            == (actual == "PAUSED")
        )

        if same:
            agreements += 1

        marker = "✓" if same else "← DIFFER"

        print(
            f"{audience + ' × ' + creative:<43}"
            f"{mmi:<12}"
            f"{actual:<12}"
            f"{marker}"
        )

    print()
    print("=" * 100)
    print("DISAGREEMENTS")
    print("=" * 100)

    for key in keys:
        mmi = mmi_status.get(
            key,
            "?"
        )

        actual = actual_status[key]

        same = (
            (mmi == "PAUSE")
            == (actual == "PAUSED")
        )

        if same:
            continue

        print()
        print(
            f"{key[0]} × {key[1]}"
        )

        print(
            f"  MMI:    {mmi}"
        )

        print(
            f"  Actual: {actual}"
        )

        decision = next(
            item
            for item in decisions
            if (
                item["audience"],
                item["creative"],
            ) == key
        )

        print(
            f"  Reason: {decision['reason']}"
        )

    print()
    print(
        f"Agreement: {agreements}/{len(keys)} "
        f"({agreements / len(keys) * 100:.1f}%)"
    )
    print()


if __name__ == "__main__":
    main()
