import json
import re
from datetime import date
from collections import defaultdict

from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_metric import MetaAdSetMetric
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_campaign_cell import MetaCampaignCell
from app.models.meta_campaign_variant import MetaCampaignVariant
from app.models.asset import Asset
from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)


IFE_TUTU_PATTERN = re.compile(
    r"^\[intellijend\].*? - "
    r"(Broad|Interest: .+?) - "
    r"Ife Tutu Creative (\d+)$",
    re.IGNORECASE,
)


def evidence_level(
    results: float | None,
) -> str:
    if results is None:
        return "none"

    if results >= 100:
        return "strong"

    if results >= 30:
        return "moderate"

    return "low"


def get_primary_metric(
    adset: MetaAdSet,
):
    if not adset.metrics:
        return None

    return sorted(
        adset.metrics,
        key=lambda metric: (
            metric.date_stop,
            metric.date_start,
        ),
        reverse=True,
    )[0]


def get_recipe_signature(
    adset: MetaAdSet,
) -> tuple:
    items = sorted(
        (
            item.item_type,
            item.meta_item_id or "",
            item.name,
        )
        for item in adset.targeting_items
    )

    countries = tuple(
        sorted(
            adset.countries
        )
    )

    return (
        tuple(items),
        adset.age_min,
        adset.age_max,
        countries,
        adset.advantage_audience,
    )


def build_historical_audience_evidence(
    db,
) -> list[dict]:
    adsets = (
        db.query(MetaAdSet)
        .order_by(
            MetaAdSet.created_time
        )
        .all()
    )

    groups = {}

    for adset in adsets:

        # The current Ife Tutu experiment gets its
        # own controlled-experiment section.
        if adset.name.startswith(
            "[intellijend]"
        ):
            continue

        signature = get_recipe_signature(
            adset
        )

        if signature not in groups:
            interest_items = [
                item
                for item
                in adset.targeting_items
                if item.item_type
                == "interest"
            ]

            employer_items = [
                item
                for item
                in adset.targeting_items
                if item.item_type
                == "work_employer"
            ]

            position_items = [
                item
                for item
                in adset.targeting_items
                if item.item_type
                == "work_position"
            ]

            groups[signature] = {
                "names": set(),
                "adset_count": 0,
                "total_spend": 0.0,
                "total_results": 0.0,
                "has_results": False,

                "interest_count":
                    len(interest_items),

                "employer_count":
                    len(employer_items),

                "position_count":
                    len(position_items),

                "interests": sorted(
                    item.name
                    for item
                    in interest_items
                ),

                "employers": sorted(
                    item.name
                    for item
                    in employer_items
                ),

                "positions": sorted(
                    item.name
                    for item
                    in position_items
                ),

                "age_min":
                    adset.age_min,

                "age_max":
                    adset.age_max,

                "countries":
                    adset.countries,

                "advantage_audience":
                    adset.advantage_audience,

                "adsets": [],
            }

        group = groups[signature]

        group["names"].add(
            adset.name
        )

        group["adset_count"] += 1

        metric = get_primary_metric(
            adset
        )

        adset_row = {
            "name": adset.name,
            "meta_adset_id":
                adset.meta_adset_id,
            "spend": None,
            "results": None,
            "cost_per_result": None,
        }

        if metric is not None:
            spend = metric.spend or 0
            results = metric.results

            group["total_spend"] += (
                spend
            )

            if results is not None:
                group["total_results"] += (
                    results
                )

                group["has_results"] = True

            adset_row["spend"] = (
                metric.spend
            )

            adset_row["results"] = (
                metric.results
            )

            adset_row[
                "cost_per_result"
            ] = metric.cost_per_result

        group["adsets"].append(
            adset_row
        )

    evidence = []

    for group in groups.values():

        if (
            group["has_results"]
            and group["total_results"] > 0
        ):
            aggregate_cpr = (
                group["total_spend"]
                / group["total_results"]
            )
        else:
            aggregate_cpr = None

        names = sorted(
            group["names"]
        )

        evidence.append(
            {
                **group,
                "names": names,
                "display_name": (
                    names[0]
                    if len(names) == 1
                    else " / ".join(names)
                ),
                "aggregate_cpr":
                    aggregate_cpr,
                "evidence_level":
                    evidence_level(
                        group["total_results"]
                        if group["has_results"]
                        else None
                    ),
            }
        )

    evidence.sort(
        key=lambda item: (
            item["aggregate_cpr"]
            is None,
            item["aggregate_cpr"]
            if item[
                "aggregate_cpr"
            ] is not None
            else float("inf"),
        )
    )

    return evidence


def parse_ife_tutu_adset_name(
    name: str,
):
    match = IFE_TUTU_PATTERN.match(
        name
    )

    if match is None:
        return None

    arm_raw = match.group(1)
    creative_number = int(
        match.group(2)
    )

    if arm_raw.casefold() == "broad":
        arm = "Broad"
    else:
        arm = (
            arm_raw
            .split(
                ":",
                1,
            )[1]
            .strip()
        )

    return {
        "arm": arm,
        "creative_number":
            creative_number,
        "creative_name":
            f"Creative {creative_number}",
    }


def build_ife_tutu_experiment(
    db,
) -> dict:
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
    arms = set()
    creatives = set()

    for adset in adsets:
        parsed = (
            parse_ife_tutu_adset_name(
                adset.name
            )
        )

        if parsed is None:
            continue

        metric = get_primary_metric(
            adset
        )

        arms.add(
            parsed["arm"]
        )

        creatives.add(
            parsed[
                "creative_number"
            ]
        )

        cell = {
            **parsed,

            "meta_adset_id":
                adset.meta_adset_id,

            "status":
                adset.effective_status,

            "spend":
                None,

            "impressions":
                None,

            "results":
                None,

            "cost_per_result":
                None,

            "evidence_level":
                "none",
        }

        if metric is not None:
            cell["spend"] = (
                metric.spend
            )

            cell["impressions"] = (
                metric.impressions
            )

            cell["results"] = (
                metric.results
            )

            cell[
                "cost_per_result"
            ] = metric.cost_per_result

            cell[
                "evidence_level"
            ] = evidence_level(
                metric.results
            )

        cells.append(
            cell
        )

    preferred_arm_order = [
        "Broad",
        "Afrobeat",
        "African popular music",
    ]

    arm_order = [
        arm
        for arm
        in preferred_arm_order
        if arm in arms
    ]

    arm_order.extend(
        sorted(
            arms
            - set(
                arm_order
            )
        )
    )

    matrix_lookup = {
        (
            cell[
                "creative_number"
            ],
            cell["arm"],
        ): cell
        for cell in cells
    }

    rows = []

    for creative_number in sorted(
        creatives
    ):
        row = {
            "creative_number":
                creative_number,

            "creative_name":
                f"Creative {creative_number}",

            "cells": [],
        }

        for arm in arm_order:
            row["cells"].append(
                matrix_lookup.get(
                    (
                        creative_number,
                        arm,
                    )
                )
            )

        rows.append(
            row
        )

    arm_summary = []

    for arm in arm_order:
        arm_cells = [
            cell
            for cell in cells
            if cell["arm"] == arm
        ]

        spend = sum(
            cell["spend"] or 0
            for cell in arm_cells
        )

        results = sum(
            cell["results"] or 0
            for cell in arm_cells
        )

        if results > 0:
            cpr = spend / results
        else:
            cpr = None

        arm_summary.append(
            {
                "arm": arm,
                "spend": spend,
                "results": results,
                "cost_per_result": cpr,
                "evidence_level":
                    evidence_level(
                        results
                    ),
            }
        )

    return {
        "arms": arm_order,
        "rows": rows,
        "cells": cells,
        "arm_summary":
            arm_summary,
    }


def build_managed_execution_observations(
    db,
    campaign_plan: MetaCampaignPlan | None,
) -> dict:
    """
    Build production execution observations from
    MMI-managed campaign cells.

    Cell identity comes from MetaCampaignCell and
    external Meta IDs, never from name parsing.
    """

    if campaign_plan is None:
        return {
            "arms": [],
            "cells": [],
        }

    campaign_cells = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.meta_campaign_plan_id
            == campaign_plan.id,
            MetaCampaignCell.status
            != "detached",
        )
        .order_by(
            MetaCampaignCell.id
        )
        .all()
    )

    observations = []
    arms = set()

    for campaign_cell in campaign_cells:

        variant = (
            db.query(MetaCampaignVariant)
            .filter(
                MetaCampaignVariant.id
                == campaign_cell.meta_campaign_variant_id
            )
            .one()
        )

        asset = (
            db.query(Asset)
            .filter(
                Asset.id
                == campaign_cell.asset_id
            )
            .one()
        )

        arms.add(
            variant.name
        )

        adset = None
        metric = None

        if campaign_cell.meta_adset_id:

            adset = (
                db.query(MetaAdSet)
                .filter(
                    MetaAdSet.meta_adset_id
                    == campaign_cell.meta_adset_id
                )
                .one_or_none()
            )

            if adset is not None:
                metric = get_primary_metric(
                    adset
                )

        spend = 0.0
        impressions = 0
        results = 0.0
        cpr = None

        if metric is not None:

            spend = float(
                metric.spend or 0
            )

            impressions = int(
                metric.impressions or 0
            )

            results = float(
                metric.results or 0
            )

            if metric.cost_per_result is not None:
                cpr = float(
                    metric.cost_per_result
                )

            elif results > 0:
                cpr = (
                    spend
                    / results
                )

        active = (
            campaign_cell.status
            not in {
                "detached",
                "paused_by_mmi",
            }
        )

        observations.append(
            {
                "cell_id":
                    campaign_cell.id,

                "meta_adset_id":
                    campaign_cell.meta_adset_id,

                "arm":
                    variant.name,

                "creative_name":
                    asset.name,

                "status":
                    campaign_cell.status,

                "meta_status":
                    (
                        adset.effective_status
                        if adset is not None
                        else None
                    ),

                "spend":
                    spend,

                "impressions":
                    impressions,

                "results":
                    results,

                "cost_per_result":
                    cpr,

                "active":
                    active,

                "has_imported_metrics":
                    metric is not None,
            }
        )

    return {
        "arms": sorted(
            arms
        ),
        "cells":
            observations,
    }


def build_execution_plan(
    experiment: dict,
    campaign_plan: MetaCampaignPlan | None,
) -> dict:
    """
    Build the current MMI execution proposal using the
    selected release's campaign configuration.

    Campaign budget and campaign day come from the
    release-specific MetaCampaignPlan.
    """

    if campaign_plan is None:
        return {
            "available": False,
            "message": (
                "No Meta campaign plan exists "
                "for this release yet."
            ),
        }

    if campaign_plan.total_budget is None:
        return {
            "available": False,
            "message": (
                "Set the campaign's total budget "
                "before execution planning."
            ),
        }

    if campaign_plan.start_date is None:
        return {
            "available": False,
            "message": (
                "Set the campaign start date "
                "before execution planning."
            ),
        }

    if not experiment["cells"]:
        return {
            "available": False,
            "message": (
                "No campaign performance cells "
                "are available yet."
            ),
        }

    total_budget = float(
        campaign_plan.total_budget
    )

    today = date.today()

    # -------------------------------------------------
    # Campaign schedule safety gate
    # -------------------------------------------------

    if today < campaign_plan.start_date:
        return {
            "available": False,
            "message": (
                "Campaign is scheduled to start on "
                f"{campaign_plan.start_date.isoformat()}."
            ),
            "start_date":
                campaign_plan.start_date,
            "end_date":
                campaign_plan.end_date,
        }

    if (
        campaign_plan.end_date is not None
        and today > campaign_plan.end_date
    ):
        return {
            "available": False,
            "message": (
                "Campaign schedule ended on "
                f"{campaign_plan.end_date.isoformat()}."
            ),
            "start_date":
                campaign_plan.start_date,
            "end_date":
                campaign_plan.end_date,
        }

    day = (
        today
        - campaign_plan.start_date
    ).days + 1

    cells = []

    for item in experiment["cells"]:

        results = int(
            item["results"] or 0
        )

        spend = float(
            item["spend"] or 0
        )

        cpr = item[
            "cost_per_result"
        ]

        if cpr is not None:
            cpr = float(cpr)

        elif results > 0:
            cpr = (
                spend
                / results
            )

        cells.append(
            CampaignCell(
                audience=item["arm"],
                creative=item[
                    "creative_name"
                ],
                impressions=int(
                    item["impressions"]
                    or 0
                ),
                spend=spend,
                results=results,
                cost_per_result=cpr,
                active=item.get(
                "active",
                True,
            ),
                days_active=day,
            cell_id=item.get(
                "cell_id"
            ),
            meta_adset_id=item.get(
                "meta_adset_id"
            ),
            )
        )

    spent_so_far = sum(
        cell.spend
        for cell in cells
    )

    arms = experiment[
        "arms"
    ]

    if not arms:
        return {
            "available": False,
            "message": (
                "No campaign audiences "
                "are available yet."
            ),
        }

    equal_share = (
        1.0
        / len(arms)
    )

    current_audience_shares = {
        arm: equal_share
        for arm in arms
    }

    engine = ExecutionEngine()

    proposal = engine.propose_day(
        total_budget=
            total_budget,
        day=
            day,
        spent_so_far=
            spent_so_far,
        cells=
            cells,
        current_audience_shares=
            current_audience_shares,
    )

    return {
        "available": True,
        "day": day,
        "total_budget":
            total_budget,
        "start_date":
            campaign_plan.start_date,
        "end_date":
            campaign_plan.end_date,
        "spent_so_far":
            spent_so_far,
        "proposal":
            proposal,
    }


def build_intelligence_report(
    db,
    release_id: int,
) -> dict:

    experiment = build_ife_tutu_experiment(
        db
    )

    campaign_plan = (
        db.query(
            MetaCampaignPlan
        )
        .filter(
            MetaCampaignPlan.release_id
            == release_id
        )
        .one_or_none()
    )

    managed_execution = (
        build_managed_execution_observations(
            db,
            campaign_plan,
        )
    )

    return {
        "historical_evidence":
            build_historical_audience_evidence(
                db
            ),

        "ife_tutu_experiment":
            experiment,

        "execution_plan":
            build_execution_plan(
                managed_execution,
                campaign_plan,
            ),
    }

