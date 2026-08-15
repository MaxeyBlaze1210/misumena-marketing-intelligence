from sqlalchemy.orm import Session

from app.services.meta_adset_launch_service import (
    read_meta_adset,
)
from app.services.meta_execution_preview_service import (
    preview_execution_plan,
)


def build_execution_diff(
    db: Session,
    campaign_plan_id: int,
    preview_day: int = 1,
) -> dict:
    """
    Compare an MMI execution preview with the current
    live Meta state.

    READ ONLY. Performs no Meta mutations.
    """

    preview = preview_execution_plan(
        db,
        campaign_plan_id=campaign_plan_id,
        preview_day=preview_day,
    )

    rows = []

    status_changes = 0
    budget_changes = 0

    for proposed in preview["rows"]:

        meta_adset_id = proposed[
            "meta_adset_id"
        ]

        if not meta_adset_id:
            raise RuntimeError(
                f"Cell {proposed['cell_id']} "
                "has no Meta ad-set ID."
            )

        current = read_meta_adset(
            str(meta_adset_id)
        )

        current_status = (
            current.get("status")
        )

        raw_budget = current.get(
            "daily_budget"
        )

        current_budget = (
            float(raw_budget) / 100.0
            if raw_budget is not None
            else None
        )

        proposed_status = proposed[
            "proposed_status"
        ]

        proposed_budget = proposed[
            "proposed_daily_budget"
        ]

        status_change = (
            current_status
            != proposed_status
        )

        budget_change = (
            proposed_budget is not None
            and (
                current_budget is None
                or abs(
                    current_budget
                    - proposed_budget
                ) >= 0.005
            )
        )

        if status_change:
            status_changes += 1

        if budget_change:
            budget_changes += 1

        rows.append(
            {
                **proposed,

                "current_status":
                    current_status,

                "current_daily_budget":
                    current_budget,

                "effective_status":
                    current.get(
                        "effective_status"
                    ),

                "status_change":
                    status_change,

                "budget_change":
                    budget_change,
            }
        )

    return {
        "mode":
            "diff",

        "campaign_plan_id":
            campaign_plan_id,

        "preview_day":
            preview_day,

        "daily_target":
            preview["daily_target"],

        "status_changes":
            status_changes,

        "budget_changes":
            budget_changes,

        "rows":
            rows,

        "meta_writes":
            0,
    }
