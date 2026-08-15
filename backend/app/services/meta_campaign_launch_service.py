from sqlalchemy.orm import Session

from app.models.meta_campaign import MetaCampaign
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.release import Release
from app.services.meta_service import (
    create_paused_campaign,
    get_campaigns,
)


def launch_or_reconcile_campaign(
    db: Session,
    release_id: int,
) -> dict:
    """
    Create the release's Meta campaign once, always PAUSED.

    If MMI already has a Meta campaign for the release,
    reconcile it against Meta instead of creating another one.
    """

    plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.release_id
            == release_id
        )
        .one_or_none()
    )

    if plan is None:
        raise RuntimeError(
            "Campaign plan not found."
        )

    release = (
        db.query(Release)
        .filter(
            Release.id == release_id
        )
        .one_or_none()
    )

    if release is None:
        raise RuntimeError(
            "Release not found."
        )

    existing = (
        plan.meta_campaign_record
    )

    campaigns = get_campaigns().get(
        "data",
        [],
    )

    # -----------------------------------------------------
    # Existing local campaign: reconcile only
    # -----------------------------------------------------

    if existing is not None:

        match = next(
            (
                item
                for item in campaigns
                if str(item.get("id"))
                == str(
                    existing.meta_campaign_id
                )
            ),
            None,
        )

        if match is None:
            return {
                "action":
                    "reconciliation_failed",

                "meta_campaign_id":
                    existing.meta_campaign_id,

                "message":
                    (
                        "MMI has a stored Meta campaign ID, "
                        "but it was not found in the current "
                        "Meta campaign list."
                    ),
            }

        existing.name = (
            match.get("name")
            or existing.name
        )

        existing.status = (
            match.get("status")
        )

        existing.objective = (
            match.get("objective")
        )

        db.flush()

        return {
            "action":
                "reconciled",

            "meta_campaign_id":
                existing.meta_campaign_id,

            "name":
                existing.name,

            "status":
                existing.status,

            "objective":
                existing.objective,
        }

    # -----------------------------------------------------
    # Create exactly one new PAUSED campaign
    # -----------------------------------------------------

    name = (
        f"[MMI] {release.artist} - "
        f"{release.title}"
    )

    created = create_paused_campaign(
        name=name,
        objective=plan.objective,
    )

    campaign_id = str(
        created["id"]
    )

    # Read back immediately before persisting.
    campaigns = get_campaigns().get(
        "data",
        [],
    )

    match = next(
        (
            item
            for item in campaigns
            if str(item.get("id"))
            == campaign_id
        ),
        None,
    )

    if match is None:
        raise RuntimeError(
            "Campaign was created in Meta but "
            "could not be reconciled."
        )

    if match.get("status") != "PAUSED":
        raise RuntimeError(
            "Safety check failed: new campaign "
            "is not PAUSED."
        )

    local = MetaCampaign(
        release_id=
            release_id,

        meta_campaign_id=
            campaign_id,

        name=
            match.get("name") or name,

        status=
            match.get("status"),

        objective=
            match.get("objective")
            or plan.objective,
    )

    db.add(
        local
    )

    db.flush()

    plan.meta_campaign_record_id = (
        local.id
    )

    db.flush()

    return {
        "action":
            "created",

        "meta_campaign_id":
            campaign_id,

        "name":
            local.name,

        "status":
            local.status,

        "objective":
            local.objective,
    }
