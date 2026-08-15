from urllib.parse import urlencode
from app.services.meta_ad_launch_service import (
    launch_all_ads_for_plan,
)
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import RedirectResponse

from app.database.database import SessionLocal
from app.models.meta_audience import MetaAudience
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_campaign_variant import MetaCampaignVariant
from app.models.meta_campaign_variant_interest import (
    MetaCampaignVariantInterest,
)
from app.models.meta_interest import MetaInterest
from app.models.asset import Asset
from app.models.meta_campaign_plan_asset import MetaCampaignPlanAsset
from app.models.meta_campaign_cell import MetaCampaignCell

router = APIRouter(
    prefix="/workspace",
    tags=["Campaign Builder"],
)


# ---------------------------------------------------------
# Base platforms
# ---------------------------------------------------------

SPOTIFY_ID = 138
APPLE_MUSIC_ID = 14

BASE_PLATFORM_IDS = {
    SPOTIFY_ID,
    APPLE_MUSIC_ID,
}


# ---------------------------------------------------------
# Compound audience recipes
# ---------------------------------------------------------

ECO_CONSCIOUS_AFRICAN_MUSIC = {
    "key": "recipe:eco_conscious_african_music",
    "name": "Eco-conscious African Music",
    "interests": [
        ("6002868910910", "Biokost"),
        ("6003020834693", "Music"),
        ("6003023077356", "African popular music"),
        ("6003158995475", "African dance"),
        ("6003226755338", "World music"),
        ("6003288328927", "Ethical consumption"),
        ("6003290182925", "Folk music"),
        ("6003316366191", "Afrocentrism"),
        ("6003349837605", "Fair Trade label"),
        ("6003359282604", "Music of Africa"),
        ("6003379668581", "Sustainable fashion"),
        ("6003426884712", "Fair Trade"),
        ("6003484812986", "Afrobeat"),
        ("6003647529746", "Africa"),
        ("6003735423104", "Kenya"),
        ("6003780190452", "Natural foods"),
        ("6004002883706", "Organic products"),
        ("6790608003312", "Travel content and inspiration"),
    ],
}


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def promotion_redirect(
    release_id: int,
) -> RedirectResponse:
    return RedirectResponse(
        url=f"/workspace/releases/{release_id}/promotion",
        status_code=303,
    )


def get_campaign_plan(
    db,
    release_id: int,
) -> MetaCampaignPlan:
    campaign_plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.release_id == release_id
        )
        .one_or_none()
    )

    if campaign_plan is None:
        raise HTTPException(
            status_code=404,
            detail="Campaign plan not found.",
        )

    return campaign_plan


def sync_campaign_cells(
    db,
    campaign_plan: MetaCampaignPlan,
) -> dict:
    """
    Synchronize enabled campaign variants × selected
    creative assets into planned campaign cells.

    Cells with live Meta IDs are never automatically deleted.
    """

    variants = (
        db.query(MetaCampaignVariant)
        .filter(
            MetaCampaignVariant.meta_campaign_plan_id
            == campaign_plan.id,
            MetaCampaignVariant.enabled.is_(True),
            MetaCampaignVariant.name != "Not selected",
        )
        .all()
    )

    asset_links = (
        db.query(MetaCampaignPlanAsset)
        .filter(
            MetaCampaignPlanAsset.meta_campaign_plan_id
            == campaign_plan.id
        )
        .all()
    )

    desired = {
        (
            variant.id,
            link.asset_id,
        )
        for variant in variants
        for link in asset_links
    }

    existing_cells = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.meta_campaign_plan_id
            == campaign_plan.id
        )
        .all()
    )

    existing = {
        (
            cell.meta_campaign_variant_id,
            cell.asset_id,
        ): cell
        for cell in existing_cells
    }

    created = 0
    removed = 0
    preserved_live = 0

    for variant_id, asset_id in desired:
        key = (
            variant_id,
            asset_id,
        )

        if key in existing:
            continue

        db.add(
            MetaCampaignCell(
                meta_campaign_plan_id=
                    campaign_plan.id,
                meta_campaign_variant_id=
                    variant_id,
                asset_id=
                    asset_id,
                status=
                    "planned",
            )
        )

        created += 1

    for key, cell in existing.items():
        if key in desired:
            continue

        has_live_meta_identity = (
            cell.meta_campaign_id is not None
            or cell.meta_adset_id is not None
        )

        if has_live_meta_identity:
            cell.status = "detached"
            preserved_live += 1
            continue

        db.delete(cell)
        removed += 1

    db.flush()

    return {
        "desired_cells": len(desired),
        "created": created,
        "removed": removed,
        "preserved_live": preserved_live,
    }


# ---------------------------------------------------------
# Meta Audience
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/"
    "meta-audience/{meta_audience_id}"
)
def set_meta_audience(
    release_id: int,
    meta_audience_id: int,
):
    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        audience = (
            db.query(MetaAudience)
            .filter(
                MetaAudience.id == meta_audience_id
            )
            .one_or_none()
        )

        if audience is None:
            raise HTTPException(
                status_code=404,
                detail="Meta audience not found.",
            )

        campaign_plan.meta_audience_id = audience.id

        # Changing the Meta Audience invalidates the
        # comparator interests.
        #
        # The base platform remains unchanged.
        comparator_variants = (
            db.query(MetaCampaignVariant)
            .filter(
                MetaCampaignVariant.meta_campaign_plan_id
                == campaign_plan.id,
                MetaCampaignVariant.role.in_(
                    [
                        "comparator_1",
                        "comparator_2",
                    ]
                ),
            )
            .all()
        )

        for variant in comparator_variants:

            for link in list(variant.interests):
                if link.meta_interest.id not in BASE_PLATFORM_IDS:
                    db.delete(link)

            variant.name = "Not selected"

        db.flush()

        sync_campaign_cells(
            db,
            campaign_plan,
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Comparator interests
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/"
    "campaign-comparator/{role}/{meta_interest_id}"
)
def set_comparator_interest(
    release_id: int,
    role: str,
    meta_interest_id: str,
):
    if role not in {
        "comparator_1",
        "comparator_2",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid comparator role.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        variant = (
            db.query(MetaCampaignVariant)
            .filter(
                MetaCampaignVariant.meta_campaign_plan_id
                == campaign_plan.id,
                MetaCampaignVariant.role == role,
            )
            .one_or_none()
        )

        if variant is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign variant not found.",
            )

        # Remove the previous comparator targeting.
        #
        # Keep Spotify or Apple Music as the
        # shared base platform.
        for link in list(variant.interests):
            if link.meta_interest.id not in BASE_PLATFORM_IDS:
                db.delete(link)

        db.flush()

        # -------------------------------------------------
        # Misumena identity recipe
        # -------------------------------------------------

        if (
            meta_interest_id
            == ECO_CONSCIOUS_AFRICAN_MUSIC["key"]
        ):
            for (
                recipe_meta_id,
                recipe_name,
            ) in ECO_CONSCIOUS_AFRICAN_MUSIC["interests"]:

                interest = (
                    db.query(MetaInterest)
                    .filter(
                        MetaInterest.meta_interest_id
                        == recipe_meta_id
                    )
                    .one_or_none()
                )

                # Historical Meta targeting gives us the
                # stable Meta IDs. If an interest is not yet
                # in the local library, preserve it locally.
                if interest is None:
                    interest = MetaInterest(
                        meta_interest_id=recipe_meta_id,
                        name=recipe_name,
                    )

                    db.add(interest)
                    db.flush()

                db.add(
                    MetaCampaignVariantInterest(
                        meta_campaign_variant_id=variant.id,
                        meta_interest_id=interest.id,
                    )
                )

            variant.name = (
                ECO_CONSCIOUS_AFRICAN_MUSIC["name"]
            )

        # -------------------------------------------------
        # Single-interest comparator
        # -------------------------------------------------

        else:
            interest = (
                db.query(MetaInterest)
                .filter(
                    MetaInterest.meta_interest_id
                    == meta_interest_id
                )
                .one_or_none()
            )

            if interest is None:
                raise HTTPException(
                    status_code=404,
                    detail="Meta interest not found.",
                )

            db.add(
                MetaCampaignVariantInterest(
                    meta_campaign_variant_id=variant.id,
                    meta_interest_id=interest.id,
                )
            )

            variant.name = interest.name

        db.flush()

        sync_campaign_cells(
            db,
            campaign_plan,
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Base platform
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/"
    "base-platform/{interest_id}"
)
def set_base_platform(
    release_id: int,
    interest_id: int,
):
    if interest_id not in BASE_PLATFORM_IDS:
        raise HTTPException(
            status_code=400,
            detail="Invalid base platform.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        platform_interest = (
            db.query(MetaInterest)
            .filter(
                MetaInterest.id == interest_id
            )
            .one_or_none()
        )

        if platform_interest is None:
            raise HTTPException(
                status_code=404,
                detail="Platform interest not found.",
            )

        variants = (
            db.query(MetaCampaignVariant)
            .filter(
                MetaCampaignVariant.meta_campaign_plan_id
                == campaign_plan.id
            )
            .all()
        )

        for variant in variants:

            # Remove whichever base platform is
            # currently present.
            for link in list(variant.interests):
                if link.meta_interest.id in BASE_PLATFORM_IDS:
                    db.delete(link)

            db.flush()

            # Add the new base platform to every arm.
            db.add(
                MetaCampaignVariantInterest(
                    meta_campaign_variant_id=variant.id,
                    meta_interest_id=platform_interest.id,
                )
            )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Age
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/age"
)
def set_age(
    release_id: int,
    age_min: int = Form(...),
    age_max: int = Form(...),
):
    if age_min < 18:
        raise HTTPException(
            status_code=400,
            detail="Minimum age must be at least 18.",
        )

    if age_max > 65:
        raise HTTPException(
            status_code=400,
            detail="Maximum age cannot exceed 65.",
        )

    if age_min > age_max:
        raise HTTPException(
            status_code=400,
            detail="Minimum age cannot exceed maximum age.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        campaign_plan.age_min = age_min
        campaign_plan.age_max = age_max

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Daily budget
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/budget"
)
def set_budget(
    release_id: int,
    total_budget: Decimal = Form(...),
):
    if total_budget <= 0:
        raise HTTPException(
            status_code=400,
            detail="Budget must be greater than zero.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        campaign_plan.total_budget = total_budget

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Schedule
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/schedule"
)
def set_schedule(
    release_id: int,
    start_date: date | None = Form(None),
    end_date: date | None = Form(None),
):
    if (
        start_date is not None
        and end_date is not None
        and end_date < start_date
    ):
        raise HTTPException(
            status_code=400,
            detail="End date cannot be before start date.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        campaign_plan.start_date = start_date
        campaign_plan.end_date = end_date

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

@router.post(
    "/releases/{release_id}/promotion/"
    "creative/{asset_id}/toggle"
)
def toggle_campaign_creative(
    release_id: int,
    asset_id: int,
):
    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        asset = (
            db.query(Asset)
            .filter(
                Asset.id == asset_id,
                Asset.release_id == release_id,
                Asset.asset_type == "short_form_video",
            )
            .one_or_none()
        )

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail="Creative asset not found.",
            )

        existing_link = (
            db.query(MetaCampaignPlanAsset)
            .filter(
                MetaCampaignPlanAsset.meta_campaign_plan_id
                == campaign_plan.id,
                MetaCampaignPlanAsset.asset_id
                == asset.id,
            )
            .one_or_none()
        )

        if existing_link is None:
            db.add(
                MetaCampaignPlanAsset(
                    meta_campaign_plan_id=campaign_plan.id,
                    asset_id=asset.id,
                )
            )
        else:
            db.delete(existing_link)

        db.flush()

        sync_campaign_cells(
            db,
            campaign_plan,
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/promotion/"
    "creatives/select-all"
)
def select_all_campaign_creatives(
    release_id: int,
):
    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        assets = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id,
                Asset.asset_type == "short_form_video",
            )
            .all()
        )

        selected_ids = {
            link.asset_id
            for link in (
                db.query(MetaCampaignPlanAsset)
                .filter(
                    MetaCampaignPlanAsset.meta_campaign_plan_id
                    == campaign_plan.id
                )
                .all()
            )
        }

        for asset in assets:
            if asset.id not in selected_ids:
                db.add(
                    MetaCampaignPlanAsset(
                        meta_campaign_plan_id=campaign_plan.id,
                        asset_id=asset.id,
                    )
                )

        db.flush()

        sync_campaign_cells(
            db,
            campaign_plan,
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()        

# ---------------------------------------------------------
# Ad delivery settings
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/ad-settings"
)
def set_ad_settings(
    release_id: int,
    destination_url: str = Form(...),
    call_to_action: str = Form("LISTEN_NOW"),
):
    destination_url = destination_url.strip()

    if not destination_url:
        raise HTTPException(
            status_code=400,
            detail="Destination URL is required.",
        )

    allowed_ctas = {
        "LISTEN_NOW",
    }

    if call_to_action not in allowed_ctas:
        raise HTTPException(
            status_code=400,
            detail="Invalid call to action.",
        )

    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        campaign_plan.destination_url = (
            destination_url
        )

        campaign_plan.call_to_action = (
            call_to_action
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Creative primary text
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/"
    "creative/{asset_id}/copy"
)
def set_creative_primary_text(
    release_id: int,
    asset_id: int,
    primary_text: str = Form(""),
):
    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        link = (
            db.query(MetaCampaignPlanAsset)
            .filter(
                MetaCampaignPlanAsset.meta_campaign_plan_id
                == campaign_plan.id,
                MetaCampaignPlanAsset.asset_id
                == asset_id,
            )
            .one_or_none()
        )

        if link is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Creative is not selected "
                    "for this campaign."
                ),
            )

        primary_text = primary_text.strip()

        link.primary_text = (
            primary_text
            if primary_text
            else None
        )

        db.commit()

        return promotion_redirect(
            release_id
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


# ---------------------------------------------------------
# Build / reconcile Meta Ads
# ---------------------------------------------------------

@router.post(
    "/releases/{release_id}/promotion/meta-build"
)
def build_meta_campaign_ads(
    release_id: int,
):
    db = SessionLocal()

    try:
        campaign_plan = get_campaign_plan(
            db,
            release_id,
        )

        result = launch_all_ads_for_plan(
            db,
            campaign_plan.id,
        )

        status = (
            "success"
            if result["failed"] == 0
            else "error"
        )

        message = (
            f"{result['created']} created, "
            f"{result['reconciled']} reconciled, "
            f"{result['skipped']} skipped, "
            f"{result['failed']} failed."
        )

        params = urlencode(
            {
                "meta_build_status":
                    status,
                "meta_build_message":
                    message,
            }
        )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release_id}/promotion?"
                f"{params}"
            ),
            status_code=303,
        )

    except Exception as exc:
        db.rollback()

        params = urlencode(
            {
                "meta_build_status":
                    "error",
                "meta_build_message":
                    str(exc),
            }
        )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release_id}/promotion?"
                f"{params}"
            ),
            status_code=303,
        )

    finally:
        db.close()
