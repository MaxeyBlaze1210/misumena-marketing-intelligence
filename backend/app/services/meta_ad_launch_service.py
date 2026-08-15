import os
import tempfile
import time

from app.core.config import settings

from app.models.asset import Asset
from app.models.meta_ad import MetaAd
from app.models.meta_campaign import MetaCampaign
from app.models.meta_campaign_cell import (
    MetaCampaignCell,
)
from app.models.meta_campaign_plan import (
    MetaCampaignPlan,
)
from app.models.meta_campaign_plan_asset import (
    MetaCampaignPlanAsset,
)

from app.services.dropbox_service import (
    get_dropbox_client,
)

from app.services.meta_service import (
    create_paused_ad,
    create_video_ad_creative,
    get_ad,
    get_ad_creative,
    get_ad_video,
    get_preferred_ad_video_thumbnail,
    upload_ad_video,
)


VIDEO_READY_TIMEOUT_SECONDS = 180
VIDEO_READY_POLL_SECONDS = 5


def wait_for_ad_video_ready(
    video_id: str,
) -> dict:
    """
    Wait for an uploaded Meta video to finish processing.
    """

    deadline = (
        time.time()
        + VIDEO_READY_TIMEOUT_SECONDS
    )

    while time.time() < deadline:

        video = get_ad_video(
            video_id
        )

        status = (
            video.get("status")
            or {}
        )

        video_status = status.get(
            "video_status"
        )

        if video_status == "ready":
            return video

        if video_status in {
            "error",
            "failed",
        }:
            raise RuntimeError(
                "Meta video processing failed: "
                f"{video}"
            )

        time.sleep(
            VIDEO_READY_POLL_SECONDS
        )

    raise RuntimeError(
        "Timed out waiting for Meta video "
        f"{video_id} to become ready."
    )


def upload_asset_video(
    asset: Asset,
) -> str:
    """
    Download one Dropbox-backed Asset and upload it
    to the Meta ad-account video library.
    """

    if asset.source != "dropbox":
        raise RuntimeError(
            "Only Dropbox-backed creative assets "
            "are currently supported."
        )

    if not asset.source_id:
        raise RuntimeError(
            "Asset has no Dropbox source ID."
        )

    file_name = (
        asset.file_name
        or asset.name
    )

    suffix = os.path.splitext(
        file_name
    )[1] or ".mp4"

    with tempfile.NamedTemporaryFile(
        suffix=suffix,
        delete=False,
    ) as temp:
        local_path = temp.name

    try:
        dbx = get_dropbox_client()

        metadata, response = (
            dbx.files_download(
                asset.source_id
            )
        )

        try:
            with open(
                local_path,
                "wb",
            ) as handle:
                handle.write(
                    response.content
                )
        finally:
            response.close()

        size = os.path.getsize(
            local_path
        )

        if size <= 0:
            raise RuntimeError(
                "Downloaded Dropbox video "
                "is empty."
            )

        upload = upload_ad_video(
            file_path=local_path,
            title=(
                "[MMI] "
                + file_name
            ),
        )

        video_id = upload.get(
            "id"
        )

        if not video_id:
            raise RuntimeError(
                "Meta did not return a video ID."
            )

        wait_for_ad_video_ready(
            video_id
        )

        return str(
            video_id
        )

    finally:
        if os.path.exists(
            local_path
        ):
            os.unlink(
                local_path
            )


def launch_or_reconcile_ad(
    db,
    cell_id: int,
) -> dict:
    """
    Build or reconcile the complete Meta ad-object
    chain for one MMI campaign cell.

    Existing Meta video, creative and ad mappings are
    reused. New Ads are always created PAUSED.
    """

    cell = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.id
            == cell_id
        )
        .one_or_none()
    )

    if cell is None:
        raise RuntimeError(
            f"Campaign cell {cell_id} not found."
        )

    if cell.status == "detached":
        return {
            "action": "skipped",
            "reason": "detached",
            "cell_id": cell.id,
        }

    if not cell.meta_adset_id:
        raise RuntimeError(
            f"Cell {cell.id} has no Meta ad-set ID."
        )

    plan = (
        db.query(MetaCampaignPlan)
        .filter(
            MetaCampaignPlan.id
            == cell.meta_campaign_plan_id
        )
        .one()
    )

    if not plan.meta_campaign_record_id:
        raise RuntimeError(
            "Campaign plan has no managed "
            "Meta campaign record."
        )

    campaign = (
        db.query(MetaCampaign)
        .filter(
            MetaCampaign.id
            == plan.meta_campaign_record_id
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

    link = (
        db.query(MetaCampaignPlanAsset)
        .filter(
            MetaCampaignPlanAsset.meta_campaign_plan_id
            == cell.meta_campaign_plan_id,
            MetaCampaignPlanAsset.asset_id
            == cell.asset_id,
        )
        .one_or_none()
    )

    if link is None:
        raise RuntimeError(
            "Campaign cell asset is no longer "
            "selected in the campaign plan."
        )

    if not link.primary_text:
        raise RuntimeError(
            f"Asset {asset.id} has no primary text."
        )

    if not plan.destination_url:
        raise RuntimeError(
            "Campaign plan has no destination URL."
        )

    if not plan.call_to_action:
        raise RuntimeError(
            "Campaign plan has no call to action."
        )

    steps = {
        "video": None,
        "creative": None,
        "ad": None,
    }

    # -----------------------------------------------------
    # Meta video
    # -----------------------------------------------------

    if link.meta_video_id:

        video = get_ad_video(
            link.meta_video_id
        )

        steps["video"] = "reused"

    else:

        link.meta_video_id = (
            upload_asset_video(
                asset
            )
        )

        db.flush()

        video = get_ad_video(
            link.meta_video_id
        )

        steps["video"] = "created"

    # -----------------------------------------------------
    # Meta Ad Creative
    # -----------------------------------------------------

    if link.meta_creative_id:

        creative = get_ad_creative(
            link.meta_creative_id
        )

        steps["creative"] = "reused"

    else:

        thumbnail_url = (
            get_preferred_ad_video_thumbnail(
                link.meta_video_id
            )
        )

        creative_result = (
            create_video_ad_creative(
                name=(
                    "[MMI] "
                    + (
                        asset.file_name
                        or asset.name
                    )
                ),
                page_id=
                    settings.meta_page_id,
                instagram_user_id=
                    settings.meta_instagram_user_id,
                video_id=
                    link.meta_video_id,
                primary_text=
                    link.primary_text,
                call_to_action=
                    plan.call_to_action,
                destination_url=
                    plan.destination_url,
                image_url=
                    thumbnail_url,
            )
        )

        creative_id = (
            creative_result.get(
                "id"
            )
        )

        if not creative_id:
            raise RuntimeError(
                "Meta did not return "
                "an Ad Creative ID."
            )

        creative = get_ad_creative(
            str(creative_id)
        )

        link.meta_creative_id = str(
            creative_id
        )

        db.flush()

        steps["creative"] = "created"

    # -----------------------------------------------------
    # Meta Ad
    # -----------------------------------------------------

    existing_ad = (
        db.query(MetaAd)
        .filter(
            MetaAd.meta_adset_id
            == str(cell.meta_adset_id)
        )
        .one_or_none()
    )

    if existing_ad is not None:

        ad = get_ad(
            existing_ad.meta_ad_id
        )

        # Keep local mapping aligned with Meta.
        existing_ad.status = (
            ad.get("status")
        )

        existing_ad.meta_creative_id = (
            str(
                (
                    ad.get("creative")
                    or {}
                ).get(
                    "id"
                )
                or link.meta_creative_id
            )
        )

        steps["ad"] = "reused"

        meta_ad_id = (
            existing_ad.meta_ad_id
        )

    else:

        ad_name = (
            "[MMI] "
            + (
                asset.file_name
                or asset.name
            )
        )

        result = create_paused_ad(
            adset_id=
                cell.meta_adset_id,
            creative_id=
                link.meta_creative_id,
            name=
                ad_name,
        )

        meta_ad_id = result.get(
            "id"
        )

        if not meta_ad_id:
            raise RuntimeError(
                "Meta did not return "
                "an Ad ID."
            )

        ad = get_ad(
            str(meta_ad_id)
        )

        if ad.get("status") != "PAUSED":
            raise RuntimeError(
                "Safety stop: newly created "
                "Meta Ad is not PAUSED."
            )

        returned_adset_id = (
            (
                ad.get("adset")
                or {}
            ).get("id")
        )

        if str(returned_adset_id) != str(
            cell.meta_adset_id
        ):
            raise RuntimeError(
                "Created Meta Ad is attached "
                "to the wrong ad set."
            )

        returned_creative_id = (
            (
                ad.get("creative")
                or {}
            ).get("id")
        )

        if str(returned_creative_id) != str(
            link.meta_creative_id
        ):
            raise RuntimeError(
                "Created Meta Ad references "
                "the wrong creative."
            )

        local_ad = MetaAd(
            campaign_id=
                campaign.id,
            meta_ad_id=
                str(meta_ad_id),
            meta_adset_id=
                str(cell.meta_adset_id),
            meta_creative_id=
                str(link.meta_creative_id),
            name=
                ad.get("name")
                or ad_name,
            status=
                ad.get("status"),
        )

        db.add(
            local_ad
        )

        db.flush()

        steps["ad"] = "created"

    # -----------------------------------------------------
    # Result
    # -----------------------------------------------------

    created_any = any(
        value == "created"
        for value in steps.values()
    )

    return {
        "action": (
            "created"
            if created_any
            else "reconciled"
        ),
        "cell_id":
            cell.id,
        "asset_id":
            asset.id,
        "asset_name":
            asset.file_name
            or asset.name,
        "meta_adset_id":
            str(cell.meta_adset_id),
        "meta_video_id":
            str(link.meta_video_id),
        "meta_creative_id":
            str(link.meta_creative_id),
        "meta_ad_id":
            str(meta_ad_id),
        "ad_status":
            ad.get("status"),
        "effective_status":
            ad.get("effective_status"),
        "steps":
            steps,
    }


def launch_all_ads_for_plan(
    db,
    campaign_plan_id: int,
) -> dict:
    """
    Build or reconcile all attached campaign cells.

    Each successful cell is committed independently,
    so a later failure cannot roll back earlier mappings.

    New Meta Ads are always created PAUSED.
    Detached cells are skipped.
    """

    cells = (
        db.query(MetaCampaignCell)
        .filter(
            MetaCampaignCell.meta_campaign_plan_id
            == campaign_plan_id
        )
        .order_by(
            MetaCampaignCell.id
        )
        .all()
    )

    cell_ids = [
        cell.id
        for cell in cells
    ]

    results = []

    created = 0
    reconciled = 0
    skipped = 0
    failed = 0

    for cell_id in cell_ids:

        cell = (
            db.query(MetaCampaignCell)
            .filter(
                MetaCampaignCell.id
                == cell_id
            )
            .one()
        )

        if cell.status == "detached":
            results.append(
                {
                    "action": "skipped",
                    "reason": "detached",
                    "cell_id": cell.id,
                }
            )

            skipped += 1
            continue

        try:
            result = launch_or_reconcile_ad(
                db,
                cell.id,
            )

            db.commit()

            results.append(
                result
            )

            action = result.get(
                "action"
            )

            if action == "created":
                created += 1

            elif action == "reconciled":
                reconciled += 1

            elif action == "skipped":
                skipped += 1

            else:
                failed += 1

        except Exception as exc:
            db.rollback()

            results.append(
                {
                    "action": "failed",
                    "cell_id": cell_id,
                    "error": str(exc),
                }
            )

            failed += 1

    return {
        "campaign_plan_id":
            campaign_plan_id,

        "total":
            len(cell_ids),

        "created":
            created,

        "reconciled":
            reconciled,

        "skipped":
            skipped,

        "failed":
            failed,

        "results":
            results,
    }
