from datetime import date

from sqlalchemy.orm import Session

from app.models.meta_ad import MetaAd
from app.models.meta_campaign_cell import MetaCampaignCell
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.services.meta_adset_launch_service import read_meta_adset
from app.services.meta_service import (
    get_ad,
    get_campaign,
    update_ad_status,
    update_adset_status,
    update_campaign_status,
)


def start_stage_1(
    db: Session,
    campaign_plan_id: int,
    preflight_only: bool = False,
) -> dict:
    """
    Start the controlled Stage-1 exploration phase.

    Safety:
    - requires a valid campaign schedule
    - requires a configured Stage-1 cell budget
    - verifies every managed ad set exists
    - verifies every ad set still has the expected daily budget
    - requires exactly one mapped Meta Ad per active campaign cell
    - verifies campaign/ad/ad-set IDs before activation
    - performs readback after activation
    - does not invoke the adaptive execution engine
    """

    plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.id == campaign_plan_id
        )
        .one_or_none()
    )

    if plan is None:
        raise RuntimeError(
            "Campaign plan not found."
        )

    if plan.start_date is None:
        raise RuntimeError(
            "Campaign has no start date."
        )

    if plan.end_date is None:
        raise RuntimeError(
            "Campaign has no end date."
        )

    today = date.today()

    if today < plan.start_date:
        raise RuntimeError(
            "Campaign has not reached its start date."
        )

    if today > plan.end_date:
        raise RuntimeError(
            "Campaign schedule has ended."
        )

    if plan.stage_1_cell_budget is None:
        raise RuntimeError(
            "Stage-1 cell budget is not configured."
        )

    if plan.meta_campaign_record is None:
        raise RuntimeError(
            "Campaign has no mapped Meta campaign."
        )

    exploration_days = 2

    expected_daily_budget = round(
        float(plan.stage_1_cell_budget)
        / exploration_days,
        2,
    )

    cells = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.meta_campaign_plan_id
            == plan.id,
            MetaCampaignCell.status
            != "detached",
        )
        .order_by(
            MetaCampaignCell.id
        )
        .all()
    )

    if not cells:
        raise RuntimeError(
            "Campaign has no managed cells."
        )

    campaign = plan.meta_campaign_record
    campaign_id = str(
        campaign.meta_campaign_id
    )

    # -----------------------------------------------------
    # Preflight: campaign
    # -----------------------------------------------------

    meta_campaign = get_campaign(
        campaign_id
    )

    if str(meta_campaign.get("id")) != campaign_id:
        raise RuntimeError(
            "Meta campaign ID readback mismatch."
        )

    # -----------------------------------------------------
    # Preflight: all cells and ads
    # -----------------------------------------------------

    prepared = []

    for cell in cells:

        if not cell.meta_adset_id:
            raise RuntimeError(
                f"Cell {cell.id} has no Meta ad-set ID."
            )

        adset_id = str(
            cell.meta_adset_id
        )

        adset = read_meta_adset(
            adset_id
        )

        if str(adset.get("id")) != adset_id:
            raise RuntimeError(
                f"Cell {cell.id}: Meta ad-set ID mismatch."
            )

        raw_budget = adset.get(
            "daily_budget"
        )

        if raw_budget is None:
            raise RuntimeError(
                f"Cell {cell.id}: Meta ad set has no daily budget."
            )

        actual_budget = (
            float(raw_budget) / 100.0
        )

        if abs(
            actual_budget
            - expected_daily_budget
        ) >= 0.01:
            raise RuntimeError(
                f"Cell {cell.id}: expected daily budget "
                f"€{expected_daily_budget:.2f}, "
                f"got €{actual_budget:.2f}."
            )

        ads = (
            db.query(MetaAd)
            .filter(
                MetaAd.meta_adset_id
                == adset_id
            )
            .all()
        )

        if len(ads) != 1:
            raise RuntimeError(
                f"Cell {cell.id}: expected exactly "
                f"1 mapped Meta Ad, found {len(ads)}."
            )

        local_ad = ads[0]

        meta_ad = get_ad(
            str(local_ad.meta_ad_id)
        )

        returned_adset_id = (
            (
                meta_ad.get("adset")
                or {}
            ).get("id")
        )

        if str(returned_adset_id) != adset_id:
            raise RuntimeError(
                f"Cell {cell.id}: Meta Ad is mapped "
                "to the wrong ad set."
            )

        prepared.append(
            {
                "cell": cell,
                "adset_id": adset_id,
                "local_ad": local_ad,
            }
        )

    if preflight_only:
        return {
            "status": "preflight_ok",
            "campaign_plan_id": plan.id,
            "meta_campaign_id": campaign_id,
            "campaign_status":
                meta_campaign.get("status"),
            "cells": len(prepared),
            "daily_budget_per_cell":
                expected_daily_budget,
            "stage_1_cell_budget":
                float(
                    plan.stage_1_cell_budget
                ),
            "maximum_stage_1_spend":
                round(
                    float(
                        plan.stage_1_cell_budget
                    )
                    * len(prepared),
                    2,
                ),
            "meta_writes": 0,
        }

    # -----------------------------------------------------
    # Activation
    #
    # Campaign first, Ads second, Ad sets last.
    # Ad sets are activated last so delivery cannot begin
    # until the full hierarchy has been prepared.
    # -----------------------------------------------------

    update_campaign_status(
        campaign_id,
        "ACTIVE",
    )

    for item in prepared:
        update_ad_status(
            str(
                item[
                    "local_ad"
                ].meta_ad_id
            ),
            "ACTIVE",
        )

    for item in prepared:
        update_adset_status(
            item["adset_id"],
            "ACTIVE",
        )

    # -----------------------------------------------------
    # Final readback
    # -----------------------------------------------------

    final_campaign = get_campaign(
        campaign_id
    )

    if final_campaign.get("status") != "ACTIVE":
        raise RuntimeError(
            "Campaign activation readback failed."
        )

    results = []

    for item in prepared:

        cell = item["cell"]
        adset_id = item["adset_id"]
        local_ad = item["local_ad"]

        final_adset = read_meta_adset(
            adset_id
        )

        final_ad = get_ad(
            str(local_ad.meta_ad_id)
        )

        if final_adset.get("status") != "ACTIVE":
            raise RuntimeError(
                f"Cell {cell.id}: ad-set activation "
                "readback failed."
            )

        if final_ad.get("status") != "ACTIVE":
            raise RuntimeError(
                f"Cell {cell.id}: ad activation "
                "readback failed."
            )

        cell.status = "stage_1_active"
        local_ad.status = "ACTIVE"

        results.append(
            {
                "cell_id": cell.id,
                "meta_adset_id": adset_id,
                "meta_ad_id": str(
                    local_ad.meta_ad_id
                ),
                "daily_budget":
                    expected_daily_budget,
                "adset_status":
                    final_adset.get(
                        "status"
                    ),
                "ad_status":
                    final_ad.get(
                        "status"
                    ),
            }
        )

    campaign.status = "ACTIVE"
    plan.status = "live"

    db.commit()

    return {
        "status": "stage_1_active",
        "campaign_plan_id": plan.id,
        "meta_campaign_id": campaign_id,
        "cells": len(results),
        "daily_budget_per_cell":
            expected_daily_budget,
        "stage_1_cell_budget":
            float(
                plan.stage_1_cell_budget
            ),
        "maximum_stage_1_spend":
            round(
                float(
                    plan.stage_1_cell_budget
                )
                * len(results),
                2,
            ),
        "results": results,
    }
