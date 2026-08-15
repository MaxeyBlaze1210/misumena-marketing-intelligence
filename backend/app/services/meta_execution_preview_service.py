from datetime import date

from sqlalchemy.orm import Session

from app.intelligence.execution_engine import (
    CampaignCell,
    ExecutionEngine,
)
from app.intelligence.rules import META_RULES
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.services.intelligence_reporting_service import (
    build_managed_execution_observations,
)


def preview_execution_plan(
    db: Session,
    campaign_plan_id: int,
    preview_day: int = 1,
) -> dict:
    """
    Preview MMI execution without writing anything to Meta.

    This deliberately bypasses the production schedule gate
    for simulation only.
    """

    plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.id
            == campaign_plan_id
        )
        .one_or_none()
    )

    if plan is None:
        raise RuntimeError(
            "Campaign plan not found."
        )

    if plan.total_budget is None:
        raise RuntimeError(
            "Campaign plan has no total budget."
        )

    observations = (
        build_managed_execution_observations(
            db,
            plan,
        )
    )

    if not observations["cells"]:
        raise RuntimeError(
            "Campaign plan has no managed cells."
        )

    cells = []

    for item in observations["cells"]:

        cells.append(
            CampaignCell(
                audience=
                    item["arm"],

                creative=
                    item["creative_name"],

                impressions=
                    int(
                        item["impressions"]
                        or 0
                    ),

                spend=
                    float(
                        item["spend"]
                        or 0
                    ),

                results=
                    int(
                        item["results"]
                        or 0
                    ),

                cost_per_result=
                    item[
                        "cost_per_result"
                    ],

                active=
                    item.get(
                        "active",
                        True,
                    ),

                days_active=
                    preview_day,

                cell_id=
                    item["cell_id"],

                meta_adset_id=
                    item[
                        "meta_adset_id"
                    ],
            )
        )

    spent_so_far = sum(
        cell.spend
        for cell in cells
    )

    arms = observations[
        "arms"
    ]

    current_audience_shares = {
        arm:
            1.0 / len(arms)

        for arm in arms
    }

    engine = ExecutionEngine()

    proposal = engine.propose_day(
        total_budget=
            float(
                plan.total_budget
            ),

        day=
            preview_day,

        spent_so_far=
            spent_so_far,

        cells=
            cells,

        current_audience_shares=
            current_audience_shares,
    )

    execution = (
        proposal.get(
            "execution_plan"
        )
        or {}
    )

    rows = []

    for item in execution.get(
        "execution",
        [],
    ):

        action = item[
            "execution_action"
        ]

        audience_budget = float(
            item.get(
                "audience_daily_budget"
            )
            or 0
        )

        capacity = int(
            item.get(
                "audience_capacity"
            )
            or 0
        )

        if (
            action == "run"
            and capacity > 0
        ):
            proposed_budget = round(
                audience_budget
                / capacity,
                2,
            )
        else:
            proposed_budget = None

        rows.append(
            {
                "cell_id":
                    item.get(
                        "cell_id"
                    ),

                "meta_adset_id":
                    item.get(
                        "meta_adset_id"
                    ),

                "audience":
                    item["audience"],

                "creative":
                    item["creative"],

                "execution_action":
                    action,

                "proposed_status":
                    (
                        "ACTIVE"
                        if action == "run"
                        else "PAUSED"
                    ),

                "proposed_daily_budget":
                    proposed_budget,

                "pruning_priority":
                    item.get(
                        "pruning_priority"
                    ),

                "reason":
                    item.get(
                        "reason"
                    ),
            }
        )

    return {
        "mode":
            "dry_run",

        "campaign_plan_id":
            campaign_plan_id,

        "preview_day":
            preview_day,

        "daily_target":
            proposal.get(
                "daily_target"
            ),

        "rows":
            rows,

        "meta_writes":
            0,
    }
