from datetime import date

from sqlalchemy.orm import Session

from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_campaign_cell import MetaCampaignCell
from app.services.meta_execution_diff_service import (
    build_execution_diff,
)
from app.services.meta_service import (
    update_adset_daily_budget,
    update_adset_status,
)
from app.services.meta_adset_launch_service import (
    read_meta_adset,
)


def apply_execution_plan(
    db: Session,
    campaign_plan_id: int,
) -> dict:
    """
    Apply the current MMI execution plan to Meta.

    Safety:
    - refuses execution before campaign start
    - refuses execution after campaign end
    - acts only on exact stored Meta ad-set IDs
    - updates budget before activation
    - reads every mutation back from Meta
    - persists local state only after successful readback
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

    if plan.start_date is None:
        return {
            "status": "blocked",
            "reason": "Campaign has no start date.",
            "meta_writes": 0,
        }

    today = date.today()

    if today < plan.start_date:
        return {
            "status": "blocked",
            "reason": (
                "Campaign is scheduled to start on "
                f"{plan.start_date.isoformat()}."
            ),
            "meta_writes": 0,
        }

    if (
        plan.end_date is not None
        and today > plan.end_date
    ):
        return {
            "status": "blocked",
            "reason": (
                "Campaign schedule ended on "
                f"{plan.end_date.isoformat()}."
            ),
            "meta_writes": 0,
        }

    campaign_day = (
        today
        - plan.start_date
    ).days + 1

    diff = build_execution_diff(
        db,
        campaign_plan_id=
            campaign_plan_id,
        preview_day=
            campaign_day,
    )

    results = []
    meta_writes = 0

    for row in diff["rows"]:

        cell_id = row["cell_id"]
        meta_adset_id = row[
            "meta_adset_id"
        ]

        if not cell_id:
            raise RuntimeError(
                "Execution row has no cell ID."
            )

        if not meta_adset_id:
            raise RuntimeError(
                f"Cell {cell_id} has no Meta ad-set ID."
            )

        cell = (
            db.query(MetaCampaignCell)
            .filter(
                MetaCampaignCell.id
                == cell_id
            )
            .one()
        )

        if str(
            cell.meta_adset_id
        ) != str(
            meta_adset_id
        ):
            raise RuntimeError(
                f"Safety failure for cell {cell_id}: "
                "execution Meta ID does not match "
                "stored campaign-cell Meta ID."
            )

        writes_for_cell = 0

        # ---------------------------------------------
        # Budget first
        # ---------------------------------------------

        proposed_budget = row[
            "proposed_daily_budget"
        ]

        if (
            row["budget_change"]
            and proposed_budget is not None
        ):
            update_adset_daily_budget(
                str(meta_adset_id),
                float(proposed_budget),
            )

            meta_writes += 1
            writes_for_cell += 1

            budget_readback = read_meta_adset(
                str(meta_adset_id)
            )

            actual_budget = (
                float(
                    budget_readback[
                        "daily_budget"
                    ]
                )
                / 100.0
            )

            if abs(
                actual_budget
                - float(proposed_budget)
            ) >= 0.01:
                raise RuntimeError(
                    f"Budget readback failed for "
                    f"cell {cell_id}: expected "
                    f"{proposed_budget}, got "
                    f"{actual_budget}."
                )

        # ---------------------------------------------
        # Status second
        # ---------------------------------------------

        proposed_status = row[
            "proposed_status"
        ]

        if row["status_change"]:
            update_adset_status(
                str(meta_adset_id),
                proposed_status,
            )

            meta_writes += 1
            writes_for_cell += 1

        # ---------------------------------------------
        # Final readback
        # ---------------------------------------------

        final = read_meta_adset(
            str(meta_adset_id)
        )

        final_status = final.get(
            "status"
        )

        if final_status != proposed_status:
            raise RuntimeError(
                f"Status readback failed for "
                f"cell {cell_id}: expected "
                f"{proposed_status}, got "
                f"{final_status}."
            )

        # ---------------------------------------------
        # Persist local execution state
        # ---------------------------------------------

        if proposed_status == "ACTIVE":
            cell.status = "active_by_mmi"

        else:
            cell.status = "paused_by_mmi"

        db.commit()

        results.append(
            {
                "cell_id":
                    cell_id,

                "meta_adset_id":
                    meta_adset_id,

                "status":
                    final_status,

                "effective_status":
                    final.get(
                        "effective_status"
                    ),

                "daily_budget":
                    (
                        float(
                            final["daily_budget"]
                        )
                        / 100.0
                        if final.get(
                            "daily_budget"
                        ) is not None
                        else None
                    ),

                "writes":
                    writes_for_cell,
            }
        )

    return {
        "status":
            "applied",

        "campaign_plan_id":
            campaign_plan_id,

        "campaign_day":
            campaign_day,

        "daily_target":
            diff["daily_target"],

        "meta_writes":
            meta_writes,

        "results":
            results,
    }
