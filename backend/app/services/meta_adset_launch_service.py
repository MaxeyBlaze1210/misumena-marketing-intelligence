import requests

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.asset import Asset
from app.models.country import Country
from app.models.meta_campaign_plan_country import (
    MetaCampaignPlanCountry,
)
from app.models.meta_campaign_cell import (
    MetaCampaignCell,
)
from app.models.meta_campaign_plan import (
    MetaCampaignPlan,
)
from app.models.meta_campaign_variant import (
    MetaCampaignVariant,
)
from app.services.meta_service import (
    create_paused_adset,
)


def read_meta_adset(
    meta_adset_id: str,
) -> dict:
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{meta_adset_id}"
    )

    params = {
        "fields": (
            "id,"
            "name,"
            "campaign_id,"
            "status,"
            "effective_status,"
            "daily_budget,"
            "optimization_goal,"
            "billing_event,"
            "promoted_object"
        ),
    }

    headers = {
        "Authorization":
            f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30,
    )

    if not response.ok:
        try:
            detail = response.json()
        except ValueError:
            detail = response.text

        raise RuntimeError(
            "Meta ad-set readback failed: "
            f"{response.status_code}: {detail}"
        )

    return response.json()


def build_targeting(
    db: Session,
    plan: MetaCampaignPlan,
    variant: MetaCampaignVariant,
) -> dict:
    countries = [
        row.iso_code
        for row in (
            db.query(Country)
            .join(
                MetaCampaignPlanCountry,
                MetaCampaignPlanCountry.country_id
                == Country.id,
            )
            .filter(
                MetaCampaignPlanCountry.meta_campaign_plan_id
                == plan.id
            )
            .order_by(
                Country.iso_code
            )
            .all()
        )
    ]

    interests = [
        {
            "id":
                link.meta_interest.meta_interest_id,

            "name":
                link.meta_interest.name,
        }
        for link in variant.interests
    ]

    if not countries:
        raise RuntimeError(
            "Campaign plan has no countries configured."
        )

    if not interests:
        raise RuntimeError(
            "Campaign variant has no interests configured."
        )

    return {
        "age_min":
            plan.age_min,

        "age_max":
            plan.age_max,

        "genders":
            [1, 2],

        "geo_locations":
            {
                "countries":
                    countries,

                "location_types":
                    [
                        "home",
                        "recent",
                    ],
            },

        "flexible_spec":
            [
                {
                    "interests":
                        interests,
                }
            ],

        "targeting_automation":
            {
                "advantage_audience":
                    0,
            },

        "publisher_platforms":
            ["instagram"],

        "instagram_positions":
            [
                "stream",
                "story",
                "reels",
            ],

        "device_platforms":
            [
                "mobile",
                "desktop",
            ],
    }


def launch_or_reconcile_adset(
    db: Session,
    cell_id: int,
    daily_budget: float = 5.76,
) -> dict:
    cell = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.id == cell_id
        )
        .one_or_none()
    )

    if cell is None:
        raise RuntimeError(
            f"Campaign cell {cell_id} not found."
        )

    plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.id
            == cell.meta_campaign_plan_id
        )
        .one()
    )

    variant = (
        db.query(MetaCampaignVariant)
        .filter(
            MetaCampaignVariant.id
            == cell.meta_campaign_variant_id
        )
        .one()
    )

    asset = (
        db.query(Asset)
        .filter(
            Asset.id == cell.asset_id
        )
        .one()
    )

    if plan.meta_campaign_record is None:
        raise RuntimeError(
            "Campaign plan has no managed Meta campaign."
        )

    campaign_id = str(
        plan.meta_campaign_record.meta_campaign_id
    )

    # -----------------------------------------------------
    # Existing mapping: reconcile only
    # -----------------------------------------------------

    if cell.meta_adset_id is not None:
        readback = read_meta_adset(
            str(cell.meta_adset_id)
        )

        if str(
            readback.get("campaign_id")
        ) != campaign_id:
            raise RuntimeError(
                "Stored Meta ad set belongs to the "
                "wrong campaign."
            )

        cell.status = (
            "created_paused"
            if readback.get("status") == "PAUSED"
            else str(
                readback.get("status")
                or cell.status
            ).lower()
        )

        db.flush()

        return {
            "action":
                "reconciled",

            "cell_id":
                cell.id,

            "meta_adset_id":
                cell.meta_adset_id,

            "status":
                readback.get("status"),

            "effective_status":
                readback.get("effective_status"),

            "name":
                readback.get("name"),
        }

    # -----------------------------------------------------
    # Create new PAUSED ad set
    # -----------------------------------------------------

    if not plan.meta_pixel_id:
        raise RuntimeError(
            "Campaign plan has no Meta pixel configured."
        )

    targeting = build_targeting(
        db,
        plan,
        variant,
    )

    name = (
        f"[MMI] {variant.name} - "
        f"{asset.name}"
    )

    created = create_paused_adset(
        campaign_id=
            campaign_id,

        name=
            name,

        daily_budget=
            daily_budget,

        optimization_goal=
            plan.optimization_goal,

        pixel_id=
            plan.meta_pixel_id,

        custom_event_type=
            "CONTENT_VIEW",

        targeting=
            targeting,
    )

    adset_id = str(
        created["id"]
    )

    readback = read_meta_adset(
        adset_id
    )

    if readback.get("status") != "PAUSED":
        raise RuntimeError(
            "Safety check failed: newly created "
            "ad set is not PAUSED."
        )

    if str(
        readback.get("campaign_id")
    ) != campaign_id:
        raise RuntimeError(
            "Safety check failed: newly created "
            "ad set belongs to the wrong campaign."
        )

    cell.meta_campaign_id = (
        campaign_id
    )

    cell.meta_adset_id = (
        adset_id
    )

    cell.status = (
        "created_paused"
    )

    db.flush()

    return {
        "action":
            "created",

        "cell_id":
            cell.id,

        "meta_adset_id":
            adset_id,

        "status":
            readback.get("status"),

        "effective_status":
            readback.get("effective_status"),

        "name":
            readback.get("name"),
    }


def launch_all_planned_adsets(
    db: Session,
    campaign_plan_id: int,
    daily_budget: float = 5.76,
) -> dict:
    """
    Create or reconcile every current campaign cell
    belonging to a campaign plan.

    Safety:
    - New Meta ad sets are created PAUSED.
    - Existing Meta ad sets are reconciled.
    - No Meta object is activated here.
    - Processing stops immediately on failure.
    """

    cells = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.meta_campaign_plan_id
            == campaign_plan_id,
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
            f"Campaign plan {campaign_plan_id} "
            "has no campaign cells."
        )

    results = []

    created = 0
    reconciled = 0

    for cell in cells:
        try:
            result = launch_or_reconcile_adset(
                db,
                cell.id,
                daily_budget=daily_budget,
            )

        except Exception as exc:
            # Keep the database transaction clean.
            db.rollback()

            raise RuntimeError(
                "Campaign-plan ad-set launch stopped "
                f"at cell {cell.id}: {exc}"
            ) from exc

        action = result.get(
            "action"
        )

        if action == "created":
            created += 1

        elif action == "reconciled":
            reconciled += 1

        results.append(
            result
        )

        # Persist each successfully reconciled mapping
        # before moving to the next external Meta write.
        #
        # This matters because Meta creation cannot be
        # rolled back by our local database transaction.
        db.commit()

    return {
        "campaign_plan_id":
            campaign_plan_id,

        "total":
            len(results),

        "created":
            created,

        "reconciled":
            reconciled,

        "failed":
            0,

        "results":
            results,
    }
