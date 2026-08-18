from datetime import date
from urllib.parse import urlencode
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database.database import SessionLocal, get_db
from app.core.config import settings

from app.models.release import Release
from app.models.meta_audience import MetaAudience
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_interest import MetaInterest
from app.models.country_preset import CountryPreset
from app.models.country_preset_country import CountryPresetCountry
from app.models.country import Country
from app.models.meta_campaign_variant import MetaCampaignVariant
from app.models.asset import Asset
from app.models.meta_campaign_plan_asset import MetaCampaignPlanAsset
from app.models.meta_campaign_cell import MetaCampaignCell
from app.models.meta_ad import MetaAd
from app.models.meta_campaign import MetaCampaign
from app.models.meta_ad_metric import MetaAdMetric
from app.schemas.release import ReleaseCreate
from app.services import release_service

from app.services.meta_interest_candidate_service import (
    get_candidate_interests_for_audience,
)

from app.services.futility_backcast_service import (
    build_day2_futility_backcast,
)

from app.services.intelligence_reporting_service import (
    build_intelligence_report,
    build_historical_audience_evidence,
)

from app.services.meta_execution_diff_service import (
    build_execution_diff,
)

from app.services.meta_execution_apply_service import (
    apply_execution_plan,
)


workspace_security = HTTPBasic()


def require_workspace_auth(
    credentials: HTTPBasicCredentials = Depends(
        workspace_security
    ),
):
    username = settings.workspace_username
    password = settings.workspace_password

    if not username or not password:
        raise HTTPException(
            status_code=503,
            detail="Workspace authentication is not configured.",
        )

    username_ok = secrets.compare_digest(
        credentials.username.encode("utf-8"),
        username.encode("utf-8"),
    )
    password_ok = secrets.compare_digest(
        credentials.password.encode("utf-8"),
        password.encode("utf-8"),
    )

    if not (username_ok and password_ok):
        raise HTTPException(
            status_code=401,
            detail="Invalid workspace credentials.",
            headers={
                "WWW-Authenticate": "Basic",
            },
        )


router = APIRouter(
    prefix="/workspace",
    tags=["Workspace"],
    dependencies=[
        Depends(require_workspace_auth),
    ],
)

templates = Jinja2Templates(
    directory="app/templates"
)


APPLE_MUSIC_ID = 14
SPOTIFY_ID = 138

BASE_PLATFORM_IDS = {
    APPLE_MUSIC_ID,
    SPOTIFY_ID,
}


def get_release_or_404(
    release_id: int,
) -> Release:
    db = SessionLocal()

    try:
        release = (
            db.query(Release)
            .filter(
                Release.id == release_id
            )
            .one_or_none()
        )

        if release is None:
            raise HTTPException(
                status_code=404,
                detail="Release not found.",
            )

        db.expunge(release)

        return release

    finally:
        db.close()


@router.get("/releases")
def release_list(
    request: Request,
):
    db = SessionLocal()

    try:
        releases = (
            db.query(Release)
            .order_by(
                Release.release_date.desc()
            )
            .all()
        )

        return templates.TemplateResponse(
            request=request,
            name="workspace/release_list.html",
            context={
                "releases": releases,
            },
        )

    finally:
        db.close()


@router.get("/releases/new")
def new_release_form(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="workspace/release_new.html",
        context={},
    )


@router.post("/releases/new")
async def create_release_from_workspace(
    request: Request,
):
    form = await request.form()

    title = (
        form.get("title", "")
        .strip()
    )

    artist = (
        form.get("artist", "")
        .strip()
    )

    release_date_raw = (
        form.get("release_date", "")
        .strip()
    )

    if not title or not artist or not release_date_raw:
        return templates.TemplateResponse(
            request=request,
            name="workspace/release_new.html",
            context={
                "error":
                    "Title, artist, and release date are required.",

                "title":
                    title,

                "artist":
                    artist,

                "release_date":
                    release_date_raw,
            },
            status_code=400,
        )

    try:
        release_date_value = date.fromisoformat(
            release_date_raw
        )

    except ValueError:
        return templates.TemplateResponse(
            request=request,
            name="workspace/release_new.html",
            context={
                "error":
                    "Release date must be a valid date.",

                "title":
                    title,

                "artist":
                    artist,

                "release_date":
                    release_date_raw,
            },
            status_code=400,
        )

    db = SessionLocal()

    try:
        release = release_service.create_release(
            db,
            ReleaseCreate(
                title=title,
                artist=artist,
                release_date=release_date_value,
            ),
        )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release.id}/release"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.get("/releases/{release_id}")
def release_workspace(
    release_id: int,
):
    return RedirectResponse(
        url=(
            f"/workspace/releases/"
            f"{release_id}/promotion"
        ),
        status_code=302,
    )


@router.get(
    "/releases/{release_id}/promotion"
)
def release_promotion(
    release_id: int,
    request: Request,
):
    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        # --------------------------------------------------
        # Meta audiences
        # --------------------------------------------------

        meta_audiences = (
            db.query(MetaAudience)
            .order_by(
                MetaAudience.id
            )
            .all()
        )

        # --------------------------------------------------
        # Campaign plan
        # --------------------------------------------------

        campaign_plan = (
            db.query(MetaCampaignPlan)
            .filter(
                MetaCampaignPlan.release_id
                == release_id
            )
            .one_or_none()
        )

        # --------------------------------------------------
        # Campaign variants
        # --------------------------------------------------

        campaign_variants = []

        if campaign_plan is not None:
            campaign_variants = (
                db.query(MetaCampaignVariant)
                .filter(
                    MetaCampaignVariant.meta_campaign_plan_id
                    == campaign_plan.id
                )
                .order_by(
                    MetaCampaignVariant.id
                )
                .all()
            )

        # --------------------------------------------------
        # Candidate comparator interests
        # --------------------------------------------------

        candidate_interest_options = []

        if (
            campaign_plan is not None
            and campaign_plan.meta_audience is not None
        ):
            candidate_interest_options = (
                get_candidate_interests_for_audience(
                    campaign_plan.meta_audience.name
                )
            )

        # --------------------------------------------------
        # Base platform
        # --------------------------------------------------

        base_platform_options = (
            db.query(MetaInterest)
            .filter(
                MetaInterest.id.in_(
                    BASE_PLATFORM_IDS
                )
            )
            .order_by(
                MetaInterest.name
            )
            .all()
        )

        base_platform_interest = None

        for variant in campaign_variants:
            if variant.role != "control":
                continue

            for link in variant.interests:
                if (
                    link.meta_interest.id
                    in BASE_PLATFORM_IDS
                ):
                    base_platform_interest = (
                        link.meta_interest
                    )
                    break

            if base_platform_interest is not None:
                break

        # --------------------------------------------------
        # Countries
        # --------------------------------------------------

        selected_country_preset = None
        selected_country_count = 0
        selected_countries = []

        if (
            campaign_plan is not None
            and campaign_plan.country_preset_id
        ):
            selected_country_preset = (
                db.query(CountryPreset)
                .filter(
                    CountryPreset.id
                    == campaign_plan.country_preset_id
                )
                .one_or_none()
            )

            selected_country_count = (
                db.query(CountryPresetCountry)
                .filter(
                    CountryPresetCountry.country_preset_id
                    == campaign_plan.country_preset_id
                )
                .count()
            )

            selected_countries = (
                db.query(Country)
                .join(
                    CountryPresetCountry,
                    Country.id
                    == CountryPresetCountry.country_id,
                )
                .filter(
                    CountryPresetCountry.country_preset_id
                    == campaign_plan.country_preset_id
                )
                .order_by(
                    Country.name
                )
                .all()
            )

        # --------------------------------------------------
        # Available creative assets
        # --------------------------------------------------

        short_form_creatives = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id,
                Asset.asset_type == "short_form_video",
            )
            .order_by(
                Asset.name
            )
            .all()
        )

        music_video_asset = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id,
                Asset.asset_type == "music_video",
            )
            .one_or_none()
        )

        # --------------------------------------------------
        # Selected campaign creatives
        # --------------------------------------------------

        selected_creative_ids = set()
        selected_creative_links = {}

        if campaign_plan is not None:

            campaign_asset_links = (
                db.query(MetaCampaignPlanAsset)
                .filter(
                    MetaCampaignPlanAsset.meta_campaign_plan_id
                    == campaign_plan.id
                )
                .all()
            )

            selected_creative_ids = {
                link.asset_id
                for link in campaign_asset_links
            }

            selected_creative_links = {
                link.asset_id: link
                for link in campaign_asset_links
            }

        selected_creative_count = len(
            selected_creative_ids
        )

        campaign_arm_count = len(
            campaign_variants
        )

        total_ad_set_count = (
            campaign_arm_count
            * selected_creative_count
        )

        # --------------------------------------------------
        # Meta build readiness
        # --------------------------------------------------

        meta_build_readiness = None

        if campaign_plan is not None:

            selected_links = list(
                selected_creative_links.values()
            )

            primary_text_ready = sum(
                1
                for link in selected_links
                if link.primary_text
            )

            videos_ready = sum(
                1
                for link in selected_links
                if link.meta_video_id
            )

            creatives_ready = sum(
                1
                for link in selected_links
                if link.meta_creative_id
            )

            missing_copy = [
                link.asset_id
                for link in selected_links
                if not link.primary_text
            ]

            attached_cells = (
                db.query(MetaCampaignCell)
                .filter(
                    MetaCampaignCell.meta_campaign_plan_id
                    == campaign_plan.id,
                    MetaCampaignCell.status
                    != "detached",
                )
                .all()
            )

            ad_sets_ready = sum(
                1
                for cell in attached_cells
                if cell.meta_adset_id
            )

            attached_adset_ids = [
                str(cell.meta_adset_id)
                for cell in attached_cells
                if cell.meta_adset_id
            ]

            ads_ready = 0

            if attached_adset_ids:
                ads_ready = (
                    db.query(MetaAd)
                    .filter(
                        MetaAd.meta_adset_id.in_(
                            attached_adset_ids
                        )
                    )
                    .count()
                )

            meta_build_readiness = {
                "selected":
                    len(selected_links),

                "primary_text_ready":
                    primary_text_ready,

                "videos_ready":
                    videos_ready,

                "creatives_ready":
                    creatives_ready,

                "campaign_cells":
                    len(attached_cells),

                "ad_sets_ready":
                    ad_sets_ready,

                "ads_ready":
                    ads_ready,

                "missing_copy":
                    missing_copy,

                "can_build": (
                    bool(selected_links)
                    and not missing_copy
                    and bool(
                        campaign_plan.destination_url
                    )
                    and bool(
                        campaign_plan.call_to_action
                    )
                    and bool(
                        campaign_plan.meta_campaign_record_id
                    )
                    and bool(attached_cells)
                    and (
                        ad_sets_ready
                        == len(attached_cells)
                    )
                ),
            }

        # --------------------------------------------------
        # Email promotion
        # --------------------------------------------------

        from app.models.contact import Contact
        from app.models.promo_campaign import PromoCampaign
        from app.models.promo_recipient import PromoRecipient
        from app.services.promo.release_links import (
            get_release_links,
        )

        promo_contacts = (
            db.query(Contact)
            .filter(
                Contact.do_not_contact.is_(False)
            )
            .order_by(
                Contact.contact_type.asc(),
                Contact.name.asc(),
                Contact.email.asc(),
            )
            .all()
        )

        promo_campaign = (
            db.query(PromoCampaign)
            .filter(
                PromoCampaign.release_id == release.id
            )
            .order_by(
                PromoCampaign.id.desc()
            )
            .first()
        )

        promo_selected_contact_ids = set()
        promo_selected_types = set()

        if promo_campaign is not None:
            promo_recipient_rows = (
                db.query(PromoRecipient)
                .filter(
                    PromoRecipient.campaign_id
                    == promo_campaign.id
                )
                .all()
            )

            promo_selected_contact_ids = {
                row.contact_id
                for row in promo_recipient_rows
            }

            promo_selected_types = {
                contact.contact_type
                for contact in promo_contacts
                if (
                    contact.id
                    in promo_selected_contact_ids
                    and contact.contact_type
                )
            }

        promo_contact_counts = {}

        for contact in promo_contacts:
            contact_type = (
                contact.contact_type
                or "other"
            )

            promo_contact_counts[contact_type] = (
                promo_contact_counts.get(
                    contact_type,
                    0,
                )
                + 1
            )

        promo_release_links = get_release_links(
            db,
            release,
        )

        # --------------------------------------------------
        # Render
        # --------------------------------------------------

        return templates.TemplateResponse(
            request=request,
            name="workspace/promotion.html",
            context={
                "release": release,
                "active_tab": "promotion",

                "meta_audiences":
                    meta_audiences,

                "campaign_plan":
                    campaign_plan,

                "campaign_variants":
                    campaign_variants,

                "candidate_interest_options":
                    candidate_interest_options,

                "base_platform_options":
                    base_platform_options,

                "base_platform_interest":
                    base_platform_interest,

                "selected_country_preset":
                    selected_country_preset,

                "selected_country_count":
                    selected_country_count,

                "selected_countries":
                    selected_countries,

                "short_form_creatives":
                    short_form_creatives,

                "music_video_asset":
                    music_video_asset,

                "selected_creative_ids":
                    selected_creative_ids,

                "selected_creative_links":
                    selected_creative_links,

                "selected_creative_count":
                    selected_creative_count,

                "campaign_arm_count":
                    campaign_arm_count,

                "total_ad_set_count":
                    total_ad_set_count,

                "meta_build_readiness":
                    meta_build_readiness,

                "meta_build_status":
                    request.query_params.get(
                        "meta_build_status"
                    ),

                "meta_build_message":
                    request.query_params.get(
                        "meta_build_message"
                    ),

                "promo_contacts":
                    promo_contacts,

                "promo_campaign":
                    promo_campaign,

                "promo_selected_contact_ids":
                    promo_selected_contact_ids,

                "promo_selected_types":
                    promo_selected_types,

                "promo_contact_counts":
                    promo_contact_counts,

                "promo_release_links":
                    promo_release_links,

                "promo_email_status":
                    request.query_params.get(
                        "promo_email_status"
                    ),
            },
        )

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/analytics/refresh"
)
def refresh_analytics(
    release_id: int,
):
    from app.services.analytics_refresh_service import (
        refresh_release_analytics,
    )

    try:
        result = refresh_release_analytics(
            release_id
        )

        meta_count = result[
            "meta_campaigns"
        ]

        youtube_count = (
            result.get("youtube") or {}
        ).get("metric_rows", 0)

        message = (
            f"Refreshed {meta_count} Meta "
            f"campaign(s) and {youtube_count} "
            f"YouTube daily metric row(s)."
        )

        params = urlencode(
            {
                "checkpoint": "latest",
                "analytics_status": "success",
                "analytics_message": message,
            }
        )

    except Exception as exc:
        params = urlencode(
            {
                "checkpoint": "latest",
                "analytics_status": "error",
                "analytics_message": str(exc),
            }
        )

    return RedirectResponse(
        url=(
            f"/workspace/releases/{release_id}"
            f"/analytics?{params}"
        ),
        status_code=303,
    )


@router.get(
    "/releases/{release_id}/analytics"
)
def release_analytics(
    release_id: int,
    request: Request,
):
    import re

    from app.models.meta_ad_metric import (
        MetaAdMetric,
    )
    from app.models.meta_campaign import (
        MetaCampaign,
    )

    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        # --------------------------------------------------
        # Imported Meta evidence for this release
        #
        # Managed MMI campaigns with no observations are
        # naturally excluded because this query starts from
        # MetaAdMetric.
        # --------------------------------------------------

        rows = (
            db.query(
                MetaCampaign,
                MetaAd,
                MetaAdMetric,
            )
            .join(
                MetaAd,
                MetaAd.campaign_id
                == MetaCampaign.id,
            )
            .join(
                MetaAdMetric,
                MetaAdMetric.ad_id
                == MetaAd.id,
            )
            .filter(
                MetaCampaign.release_id
                == release_id,
            )
            .order_by(
                MetaAdMetric.date_start,
                MetaCampaign.id,
                MetaAd.id,
            )
            .all()
        )

        dates = sorted(
            {
                metric.date_start
                for _, _, metric in rows
            }
        )

        # --------------------------------------------------
        # Checkpoints
        # --------------------------------------------------

        checkpoint_options = []

        if dates:
            candidates = [
                ("1", "Day 1", 1),
                ("2", "Day 2", 2),
                ("3", "Day 3", 3),
                ("7", "Day 7", 7),
                ("14", "Day 14", 14),
                ("21", "Day 21", 21),
                ("28", "Day 28", 28),
            ]

            for value, label, day_number in candidates:
                if len(dates) >= day_number:
                    checkpoint_options.append(
                        {
                            "value": value,
                            "label": label,
                            "date": dates[
                                day_number - 1
                            ],
                        }
                    )

            checkpoint_options.append(
                {
                    "value": "latest",
                    "label": "Latest",
                    "date": dates[-1],
                }
            )

        requested_checkpoint = (
            request.query_params.get(
                "checkpoint",
                "latest",
            )
        )

        selected_option = next(
            (
                item
                for item in checkpoint_options
                if item["value"]
                == requested_checkpoint
            ),
            (
                checkpoint_options[-1]
                if checkpoint_options
                else None
            ),
        )

        selected_date = (
            selected_option["date"]
            if selected_option
            else None
        )

        included_rows = [
            (campaign, ad, metric)
            for campaign, ad, metric in rows
            if (
                selected_date is not None
                and metric.date_start
                <= selected_date
            )
        ]

        # --------------------------------------------------
        # Helpers
        # --------------------------------------------------

        def arm_name(campaign_name):
            name = campaign_name or ""

            if "Interest:" in name:
                return (
                    name.split(
                        "Interest:",
                        1,
                    )[1]
                    .strip()
                )

            if name.endswith(" - Broad"):
                return "Broad"

            if " - Broad - " in name:
                return "Broad"

            # Generic fallback for future imported
            # campaigns.
            return name

        def creative_name(ad_name):
            name = ad_name or ""

            match = re.search(
                r"(?:Ife Tutu )?Creative\s+(\d+)",
                name,
                flags=re.IGNORECASE,
            )

            if match:
                return (
                    f"Creative "
                    f"{int(match.group(1))}"
                )

            return name

        def empty_metrics():
            return {
                "spend": 0.0,
                "results": 0,
                "impressions": 0,
                "clicks": 0,
                "landing_page_views": 0,
                "post_likes": 0,
                "post_saves": 0,
                "post_reactions": 0,
                "video_views": 0,
            }

        def add_metric(target, metric):
            target["spend"] += (
                metric.spend or 0
            )
            target["results"] += (
                metric.results or 0
            )
            target["impressions"] += (
                metric.impressions or 0
            )
            target["clicks"] += (
                metric.clicks or 0
            )
            target[
                "landing_page_views"
            ] += (
                metric.landing_page_views
                or 0
            )
            target["post_likes"] += (
                metric.post_likes or 0
            )
            target["post_saves"] += (
                metric.post_saves or 0
            )
            target["post_reactions"] += (
                metric.post_reactions or 0
            )
            target["video_views"] += (
                metric.video_views or 0
            )

        def finish_metrics(item):
            item["cost_per_result"] = (
                item["spend"]
                / item["results"]
                if item["results"] > 0
                else None
            )

            item["ctr"] = (
                (
                    item["clicks"]
                    / item["impressions"]
                )
                * 100
                if item["impressions"] > 0
                else None
            )

            item["like_rate"] = (
                (
                    item["post_likes"]
                    / item["impressions"]
                )
                * 100
                if item["impressions"] > 0
                else None
            )

            return item

        # --------------------------------------------------
        # Overall campaign summary
        # --------------------------------------------------

        meta_summary = empty_metrics()

        for _, _, metric in included_rows:
            add_metric(
                meta_summary,
                metric,
            )

        finish_metrics(
            meta_summary
        )

        # --------------------------------------------------
        # Arm summaries + creative × arm matrix
        # --------------------------------------------------

        arm_data = {}
        matrix_data = {}
        creative_names = set()

        for campaign, ad, metric in included_rows:

            arm = arm_name(
                campaign.name
            )

            creative = creative_name(
                ad.name
            )

            creative_names.add(
                creative
            )

            arm_metrics = arm_data.setdefault(
                arm,
                empty_metrics(),
            )

            add_metric(
                arm_metrics,
                metric,
            )

            key = (
                creative,
                arm,
            )

            cell = matrix_data.setdefault(
                key,
                empty_metrics(),
            )

            add_metric(
                cell,
                metric,
            )

        for item in arm_data.values():
            finish_metrics(item)

        for item in matrix_data.values():
            finish_metrics(item)

        # Preserve intuitive targeting order where
        # possible, while remaining generic.
        preferred_arm_order = {
            "Broad": 0,
            "Afrobeat": 1,
            "African popular music": 2,
        }

        meta_arms = sorted(
            arm_data.keys(),
            key=lambda name: (
                preferred_arm_order.get(
                    name,
                    100,
                ),
                name.lower(),
            ),
        )

        def creative_sort_key(name):
            match = re.search(
                r"Creative\s+(\d+)",
                name,
                flags=re.IGNORECASE,
            )

            if match:
                return (
                    0,
                    int(match.group(1)),
                )

            return (
                1,
                name.lower(),
            )

        sorted_creatives = sorted(
            creative_names,
            key=creative_sort_key,
        )

        meta_creative_matrix = []

        for creative in sorted_creatives:

            cells = []

            for arm in meta_arms:
                cells.append(
                    matrix_data.get(
                        (
                            creative,
                            arm,
                        )
                    )
                )

            meta_creative_matrix.append(
                {
                    "name": creative,
                    "cells": cells,
                }
            )

        meta_arm_summaries = [
            {
                "name": arm,
                **arm_data[arm],
            }
            for arm in meta_arms
        ]

        # --------------------------------------------------
        # YouTube analytics for this release
        # --------------------------------------------------

        from app.models.youtube_video import YouTubeVideo
        from app.models.youtube_metric import YouTubeMetric
        from app.models.youtube_discovery_metric import (
            YouTubeDiscoveryMetric,
        )
        from app.models.youtube_recommendation import (
            YouTubeRecommendation,
        )

        youtube_video = (
            db.query(YouTubeVideo)
            .filter(
                YouTubeVideo.release_id == release_id
            )
            .order_by(
                YouTubeVideo.published_at.desc()
            )
            .first()
        )

        youtube_analytics = None

        if youtube_video:

            metric_rows = (
                db.query(YouTubeMetric)
                .filter(
                    YouTubeMetric.video_id
                    == youtube_video.id
                )
                .all()
            )

            discovery_rows = (
                db.query(YouTubeDiscoveryMetric)
                .filter(
                    YouTubeDiscoveryMetric.video_id
                    == youtube_video.id
                )
                .all()
            )

            recommendations = (
                db.query(YouTubeRecommendation)
                .filter(
                    YouTubeRecommendation.video_id
                    == youtube_video.id
                )
                .order_by(
                    YouTubeRecommendation.views.desc()
                )
                .limit(10)
                .all()
            )

            total_views = sum(
                row.views or 0
                for row in metric_rows
            )

            watch_hours = sum(
                row.watch_time_hours or 0
                for row in metric_rows
            )

            subscribers = sum(
                row.subscribers_gained or 0
                for row in metric_rows
            )

            watched_seconds = sum(
                (row.views or 0)
                * (row.average_view_duration_seconds or 0)
                for row in metric_rows
            )

            average_duration = (
                round(watched_seconds / total_views)
                if total_views > 0
                else None
            )

            traffic_rows = [
                row
                for row in discovery_rows
                if row.category == "traffic_source"
            ]

            traffic = {}

            for row in traffic_rows:
                traffic[row.key] = (
                    traffic.get(row.key, 0)
                    + (row.views or 0)
                )

            paid_views = traffic.get(
                "ADVERTISING",
                0,
            )

            traffic_total = sum(
                traffic.values()
            )

            organic_views = max(
                traffic_total - paid_views,
                0,
            )

            organic_share = (
                organic_views
                / traffic_total
                * 100
                if traffic_total > 0
                else 0.0
            )

            def top_discovery(category, limit=8):
                return sorted(
                    [
                        row
                        for row in discovery_rows
                        if row.category == category
                    ],
                    key=lambda row: (
                        -(row.views or 0)
                    ),
                )[:limit]

            youtube_analytics = {
                "video":
                    youtube_video,

                "total_views":
                    total_views,

                "watch_hours":
                    watch_hours,

                "average_duration":
                    average_duration,

                "subscribers":
                    subscribers,

                "paid_views":
                    paid_views,

                "organic_views":
                    organic_views,

                "organic_share":
                    organic_share,

                "search_views":
                    traffic.get(
                        "YT_SEARCH",
                        0,
                    ),

                "suggested_views":
                    traffic.get(
                        "RELATED_VIDEO",
                        0,
                    ),

                "playlist_views":
                    traffic.get(
                        "PLAYLIST",
                        0,
                    ),

                "channel_views":
                    traffic.get(
                        "YT_CHANNEL",
                        0,
                    ),

                "external_views":
                    traffic.get(
                        "EXT_URL",
                        0,
                    ),

                "search_terms":
                    top_discovery(
                        "search_term"
                    ),

                "countries":
                    top_discovery(
                        "country"
                    ),

                "recommendations":
                    recommendations,
            }

        return templates.TemplateResponse(
            request=request,
            name="workspace/analytics.html",
            context={
                "release":
                    release,

                "active_tab":
                    "analytics",

                "meta_summary":
                    meta_summary,

                "meta_arms":
                    meta_arms,

                "meta_arm_summaries":
                    meta_arm_summaries,

                "meta_creative_matrix":
                    meta_creative_matrix,

                "youtube_analytics":
                    youtube_analytics,

                "meta_checkpoint_options":
                    checkpoint_options,

                "meta_checkpoint":
                    (
                        selected_option["value"]
                        if selected_option
                        else None
                    ),

                "meta_checkpoint_label":
                    (
                        selected_option["label"]
                        if selected_option
                        else None
                    ),

                "meta_checkpoint_date":
                    selected_date,
            },
        )

    finally:
        db.close()


@router.get(
    "/releases/{release_id}/intelligence"
)
def release_intelligence(
    release_id: int,
    request: Request,
):
    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        report = build_intelligence_report(
            db,
            release_id,
        )

        futility_backcast = (
            build_day2_futility_backcast(
                db,
                release_id,
            )
        )

        campaign_plan = (
            db.query(MetaCampaignPlan)
            .filter(
                MetaCampaignPlan.release_id
                == release_id
            )
            .one_or_none()
        )

        execution_diff = None
        execution_diff_error = None

        if campaign_plan is not None:

            preview_day = 1

            if campaign_plan.start_date is not None:
                preview_day = max(
                    1,
                    (
                        date.today()
                        - campaign_plan.start_date
                    ).days
                    + 1,
                )

            try:
                execution_diff = (
                    build_execution_diff(
                        db,
                        campaign_plan_id=
                            campaign_plan.id,
                        preview_day=
                            preview_day,
                    )
                )

            except Exception as exc:
                execution_diff_error = str(
                    exc
                )

        return templates.TemplateResponse(
            request=request,
            name="workspace/intelligence.html",
            context={
                "release": release,
                "active_tab": "intelligence",

                "futility_backcast":
                    futility_backcast,

                "historical_evidence":
                    report["historical_evidence"],
                "ife_tutu_experiment":
                    report["ife_tutu_experiment"],

                "execution_plan":
                    report["execution_plan"],

                "execution_diff":
                    execution_diff,

                "execution_diff_error":
                    execution_diff_error,

                "execution_apply_status":
                    request.query_params.get(
                        "execution_status"
                    ),

                "execution_apply_message":
                    request.query_params.get(
                        "execution_message"
                    ),
            },
        )

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/intelligence/apply"
)
def apply_release_execution(
    release_id: int,
):
    db = SessionLocal()

    try:
        campaign_plan = (
            db.query(MetaCampaignPlan)
            .filter(
                MetaCampaignPlan.release_id
                == release_id
            )
            .one_or_none()
        )

        if campaign_plan is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign plan not found.",
            )

        try:
            result = apply_execution_plan(
                db,
                campaign_plan_id=
                    campaign_plan.id,
            )

        except Exception as exc:
            db.rollback()

            params = urlencode(
                {
                    "execution_status":
                        "error",

                    "execution_message":
                        str(exc),
                }
            )

            return RedirectResponse(
                url=(
                    f"/workspace/releases/"
                    f"{release_id}/intelligence?"
                    f"{params}"
                ),
                status_code=303,
            )

        status = result.get(
            "status",
            "unknown",
        )

        if status == "blocked":
            message = result.get(
                "reason",
                "Execution blocked.",
            )

        else:
            message = (
                f"Execution applied. "
                f"{result.get('meta_writes', 0)} "
                f"Meta writes completed."
            )

        params = urlencode(
            {
                "execution_status":
                    status,

                "execution_message":
                    message,
            }
        )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release_id}/intelligence?"
                f"{params}"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.get(
    "/releases/{release_id}/release"
)
def release_information(
    release_id: int,
    request: Request,
):
    release = get_release_or_404(
        release_id
    )

    return templates.TemplateResponse(
        request=request,
        name="workspace/release.html",
        context={
            "release": release,
            "active_tab": "release",
        },
    )


@router.get(
    "/releases/{release_id}/assets"
)
def release_assets(
    release_id: int,
    request: Request,
):
    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        assets = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id
            )
            .order_by(
                Asset.asset_type,
                Asset.name,
            )
            .all()
        )

        short_form_creatives = [
            asset
            for asset in assets
            if asset.asset_type == "short_form_video"
        ]

        promo_audio = next(
            (
                asset
                for asset in assets
                if asset.asset_type == "promo_audio"
            ),
            None,
        )

        music_video = next(
            (
                asset
                for asset in assets
                if asset.asset_type == "music_video"
            ),
            None,
        )

        return templates.TemplateResponse(
            request=request,
            name="workspace/assets.html",
            context={
                "release": release,
                "active_tab": "assets",
                "assets": assets,
                "short_form_creatives": short_form_creatives,
                "promo_audio": promo_audio,
                "music_video": music_video,
            },
        )

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Research workspace
# ---------------------------------------------------------------------------

@router.get("/research")
def research_workspace(
    request: Request,
):
    db = SessionLocal()

    try:
        historical_evidence = (
            build_historical_audience_evidence(
                db
            )
        )

        # --------------------------------------------------
        # Historical YouTube organic-discovery evidence
        # --------------------------------------------------

        from app.models.youtube_video import (
            YouTubeVideo,
        )
        from app.models.youtube_metric import (
            YouTubeMetric,
        )
        from app.models.youtube_recommendation import (
            YouTubeRecommendation,
        )
        from app.models.youtube_discovery_metric import (
            YouTubeDiscoveryMetric,
        )

        videos = (
            db.query(YouTubeVideo)
            .order_by(
                YouTubeVideo.published_at.desc()
            )
            .all()
        )

        youtube_rows = []

        total_views_all = 0
        total_organic_all = 0
        total_traffic_all = 0

        for video in videos:

            metrics = (
                db.query(YouTubeMetric)
                .filter(
                    YouTubeMetric.video_id
                    == video.id
                )
                .all()
            )

            total_views = sum(
                row.views or 0
                for row in metrics
            )

            traffic = (
                db.query(
                    YouTubeDiscoveryMetric
                )
                .filter(
                    YouTubeDiscoveryMetric.video_id
                    == video.id,
                    YouTubeDiscoveryMetric.category
                    == "traffic_source",
                )
                .all()
            )

            traffic_map = {
                row.key: (
                    row.views or 0
                )
                for row in traffic
            }

            traffic_total = sum(
                traffic_map.values()
            )

            paid_views = (
                traffic_map.get(
                    "ADVERTISING",
                    0,
                )
            )

            organic_views = max(
                0,
                traffic_total
                - paid_views,
            )

            organic_share = (
                organic_views
                / traffic_total
                * 100
                if traffic_total > 0
                else 0.0
            )

            def discovery_rows(
                category,
                limit=8,
            ):
                return (
                    db.query(
                        YouTubeDiscoveryMetric
                    )
                    .filter(
                        YouTubeDiscoveryMetric.video_id
                        == video.id,
                        YouTubeDiscoveryMetric.category
                        == category,
                    )
                    .order_by(
                        YouTubeDiscoveryMetric.views.desc()
                    )
                    .limit(limit)
                    .all()
                )

            recommendations = (
                db.query(
                    YouTubeRecommendation
                )
                .filter(
                    YouTubeRecommendation.video_id
                    == video.id
                )
                .order_by(
                    YouTubeRecommendation.views.desc()
                )
                .limit(10)
                .all()
            )

            youtube_rows.append(
                {
                    "id":
                        video.id,

                    "title":
                        video.title,

                    "published_at":
                        video.published_at,

                    "total_views":
                        total_views,

                    "paid_views":
                        paid_views,

                    "organic_views":
                        organic_views,

                    "organic_share":
                        organic_share,

                    "search_views":
                        traffic_map.get(
                            "YT_SEARCH",
                            0,
                        ),

                    "suggested_views":
                        traffic_map.get(
                            "RELATED_VIDEO",
                            0,
                        ),

                    "playlist_views":
                        traffic_map.get(
                            "PLAYLIST",
                            0,
                        ),

                    "channel_views":
                        traffic_map.get(
                            "YT_CHANNEL",
                            0,
                        ),

                    "subscriber_views":
                        traffic_map.get(
                            "SUBSCRIBER",
                            0,
                        ),

                    "external_views":
                        traffic_map.get(
                            "EXT_URL",
                            0,
                        ),

                    "recommendations":
                        recommendations,

                    "search_terms":
                        discovery_rows(
                            "search_term",
                            8,
                        ),

                    "countries":
                        discovery_rows(
                            "country",
                            8,
                        ),

                    "external_sources":
                        discovery_rows(
                            "external_source",
                            8,
                        ),
                }
            )

            total_views_all += (
                total_views
            )

            total_organic_all += (
                organic_views
            )

            total_traffic_all += (
                traffic_total
            )

        youtube_rows.sort(
            key=lambda item: (
                -item["organic_views"],
                -item["total_views"],
                item["title"] or "",
            )
        )

        youtube_research = {
            "summary": {
                "video_count":
                    len(youtube_rows),

                "total_views":
                    total_views_all,

                "organic_views":
                    total_organic_all,

                "organic_share":
                    (
                        total_organic_all
                        / total_traffic_all
                        * 100
                        if total_traffic_all > 0
                        else 0.0
                    ),
            },

            "videos":
                youtube_rows,
        }

        # --------------------------------------------------
        # Historical Bandcamp sales evidence
        # --------------------------------------------------

        from sqlalchemy import func

        from app.models.bandcamp_sale import (
            BandcampSale,
        )

        bandcamp_purchases = (
            db.query(BandcampSale)
            .count()
        )

        bandcamp_unique_buyers = (
            db.query(
                func.count(
                    func.distinct(
                        BandcampSale.buyer_id
                    )
                )
            )
            .filter(
                BandcampSale.buyer_id.isnot(None)
            )
            .scalar()
            or 0
        )

        repeat_buyer_rows = (
            db.query(
                BandcampSale.buyer_id
            )
            .filter(
                BandcampSale.buyer_id.isnot(None)
            )
            .group_by(
                BandcampSale.buyer_id
            )
            .having(
                func.count(BandcampSale.id) > 1
            )
            .all()
        )

        bandcamp_repeat_buyers = len(
            repeat_buyer_rows
        )

        bandcamp_net_revenue = (
            db.query(
                func.sum(
                    BandcampSale.net_amount
                )
            )
            .scalar()
            or 0.0
        )

        bandcamp_countries = (
            db.query(
                BandcampSale.buyer_country_name,
                func.count(
                    BandcampSale.id
                ).label("purchases"),
                func.count(
                    func.distinct(
                        BandcampSale.buyer_id
                    )
                ).label("buyers"),
            )
            .filter(
                BandcampSale.buyer_country_name
                .isnot(None)
            )
            .group_by(
                BandcampSale.buyer_country_name
            )
            .order_by(
                func.count(
                    BandcampSale.id
                ).desc()
            )
            .limit(10)
            .all()
        )

        bandcamp_items = (
            db.query(
                BandcampSale.item_name,
                func.count(
                    BandcampSale.id
                ).label("purchases"),
                func.count(
                    func.distinct(
                        BandcampSale.buyer_id
                    )
                ).label("buyers"),
                func.sum(
                    BandcampSale.net_amount
                ).label("net_revenue"),
            )
            .filter(
                BandcampSale.item_name
                .isnot(None)
            )
            .group_by(
                BandcampSale.item_name
            )
            .order_by(
                func.count(
                    BandcampSale.id
                ).desc()
            )
            .limit(15)
            .all()
        )

        bandcamp_research = {
            "summary": {
                "purchases":
                    bandcamp_purchases,

                "unique_buyers":
                    bandcamp_unique_buyers,

                "repeat_buyers":
                    bandcamp_repeat_buyers,

                "net_revenue":
                    bandcamp_net_revenue,
            },

            "countries":
                bandcamp_countries,

            "items":
                bandcamp_items,
        }

        return templates.TemplateResponse(
            request=request,
            name="workspace/research.html",
            context={
                "historical_evidence":
                    historical_evidence,

                "youtube_research":
                    youtube_research,

                "bandcamp_research":
                    bandcamp_research,
            },
        )

    finally:
        db.close()


# ---------------------------------------------------------------------------
# Playlist workspace
# ---------------------------------------------------------------------------

PLAYLIST_MIRROR_CONFIG = [
    {
        "name": "Light up your day",
        "spotify_id": "4ZF5vXUdRU4Ocev5sfzkQp",
        "apple_id": "335284DC4891CF25",
    },
    {
        "name": "Dance Groove Repeat",
        "spotify_id": "046qaNH5CuEcNeI7w5JLqY",
        "apple_id": "DC01151C2BC071B6",
    },
    {
        "name": "Roots & Chill",
        "spotify_id": "6yppNnxoQW5rYnU7igzL09",
        "apple_id": "5E459C828A15B962",
    },
]


@router.get("/playlists")
def playlist_workspace(
    request: Request,
):
    from app.services.playlist_mirror.spotify_reader import (
        get_playlist_items,
    )
    from app.services.playlist_mirror.compare_spotify_apple import (
        get_apple_tracks,
        score_match,
    )

    results = []

    for config in PLAYLIST_MIRROR_CONFIG:
        result = {
            **config,
            "error": None,
        }

        try:
            spotify = get_playlist_items(
                config["spotify_id"]
            )
            apple = get_apple_tracks(
                config["name"]
            )

            unused_apple = set(range(len(apple)))
            matches = []
            missing = []

            for s_pos, s_track in enumerate(spotify):
                best_pos = None
                best_score = 0.0

                for a_pos in unused_apple:
                    score = score_match(
                        s_track,
                        apple[a_pos],
                    )

                    if score > best_score:
                        best_score = score
                        best_pos = a_pos

                if (
                    best_pos is not None
                    and best_score >= 0.50
                ):
                    unused_apple.remove(best_pos)

                    matches.append(
                        (
                            s_pos,
                            best_pos,
                            best_score,
                        )
                    )
                else:
                    missing.append(
                        {
                            "position": s_pos,
                            "artist": ", ".join(
                                s_track["artists"]
                            ),
                            "title": s_track["title"],
                            "isrc": s_track.get("isrc"),
                        }
                    )

            extras = [
                {
                    "position": pos,
                    "artist": apple[pos]["artist"],
                    "title": apple[pos]["title"],
                }
                for pos in sorted(unused_apple)
            ]

            apple_positions = [
                a_pos
                for _, a_pos, _ in matches
            ]

            ordered = (
                apple_positions
                == sorted(apple_positions)
            )

            result.update(
                {
                    "spotify_count": len(spotify),
                    "apple_count": len(apple),
                    "matched_count": len(matches),
                    "missing": missing,
                    "extras": extras,
                    "ordered": ordered,
                }
            )

        except Exception as exc:
            result["error"] = str(exc)

        results.append(result)

    return templates.TemplateResponse(
        request=request,
        name="workspace/playlists.html",
        context={
            "playlists": results,
        },
    )


@router.post("/playlists/sync")
def sync_playlists():
    from app.services.playlist_mirror.sync_all import (
        sync_all_playlists,
    )

    try:
        results = sync_all_playlists()

        changed = sum(
            1
            for result in results
            if result["changed"]
        )

        return RedirectResponse(
            url=(
                "/workspace/playlists"
                f"?sync=success&changed={changed}"
            ),
            status_code=303,
        )

    except Exception as exc:
        params = urlencode(
            {
                "sync": "error",
                "message": str(exc),
            }
        )

        return RedirectResponse(
            url=f"/workspace/playlists?{params}",
            status_code=303,
        )


@router.get("/contacts")
def contacts_workspace(
    request: Request,
    db: Session = Depends(get_db),
):
    from app.models.contact import Contact

    contacts = (
        db.query(Contact)
        .order_by(
            Contact.organization.asc(),
            Contact.name.asc(),
            Contact.email.asc(),
        )
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="workspace/contacts.html",
        context={
            "contacts": contacts,
        },
    )


@router.get("/contacts/new")
def new_contact_workspace(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="workspace/contact_form.html",
        context={
            "contact": None,
            "error": None,
        },
    )


@router.post("/contacts/new")
async def create_contact_workspace(
    request: Request,
    db: Session = Depends(get_db),
):
    from app.models.contact import Contact

    form = await request.form()

    name = (form.get("name") or "").strip()
    greeting_name = (form.get("greeting_name") or "").strip()
    email = (form.get("email") or "").strip().lower()
    organization = (form.get("organization") or "").strip()
    contact_type = (form.get("contact_type") or "").strip()
    country = (form.get("country") or "").strip()
    notes = (form.get("notes") or "").strip()

    if not email:
        return templates.TemplateResponse(
            request=request,
            name="workspace/contact_form.html",
            context={
                "contact": {
                    "name": name,
                    "greeting_name": greeting_name,
                    "email": email,
                    "organization": organization,
                    "contact_type": contact_type,
                    "country": country,
                    "notes": notes,
                },
                "error": "Email address is required.",
            },
            status_code=400,
        )

    existing = (
        db.query(Contact)
        .filter(Contact.email == email)
        .first()
    )

    if existing:
        return templates.TemplateResponse(
            request=request,
            name="workspace/contact_form.html",
            context={
                "contact": {
                    "name": name,
                    "greeting_name": greeting_name,
                    "email": email,
                    "organization": organization,
                    "contact_type": contact_type,
                    "country": country,
                    "notes": notes,
                },
                "error": "A contact with this email address already exists.",
            },
            status_code=400,
        )

    contact = Contact(
        name=name or None,
        greeting_name=greeting_name or None,
        email=email,
        organization=organization or None,
        contact_type=contact_type or None,
        country=country or None,
        notes=notes or None,
        source="manual",
        do_not_contact=False,
    )

    db.add(contact)
    db.commit()

    return RedirectResponse(
        url="/workspace/contacts",
        status_code=303,
    )


@router.get("/contacts/{contact_id}/edit")
def edit_contact_workspace(
    contact_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.models.contact import Contact

    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=404,
            detail="Contact not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="workspace/contact_form.html",
        context={
            "contact": contact,
            "error": None,
            "edit_mode": True,
        },
    )


@router.post("/contacts/{contact_id}/edit")
async def update_contact_workspace(
    contact_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    from app.models.contact import Contact

    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=404,
            detail="Contact not found",
        )

    form = await request.form()

    name = (form.get("name") or "").strip()
    greeting_name = (form.get("greeting_name") or "").strip()
    email = (form.get("email") or "").strip().lower()
    organization = (form.get("organization") or "").strip()
    contact_type = (form.get("contact_type") or "").strip()
    country = (form.get("country") or "").strip()
    notes = (form.get("notes") or "").strip()

    if not email:
        error = "Email address is required."
    else:
        duplicate = (
            db.query(Contact)
            .filter(
                Contact.email == email,
                Contact.id != contact_id,
            )
            .first()
        )

        error = (
            "A contact with this email address already exists."
            if duplicate
            else None
        )

    if error:
        values = {
            "id": contact_id,
            "name": name,
            "email": email,
            "organization": organization,
            "contact_type": contact_type,
            "country": country,
            "notes": notes,
        }

        return templates.TemplateResponse(
            request=request,
            name="workspace/contact_form.html",
            context={
                "contact": values,
                "error": error,
                "edit_mode": True,
            },
            status_code=400,
        )

    contact.name = name or None
    contact.greeting_name = greeting_name or None
    contact.email = email
    contact.organization = organization or None
    contact.contact_type = contact_type or None
    contact.country = country or None
    contact.notes = notes or None

    db.commit()

    return RedirectResponse(
        url="/workspace/contacts",
        status_code=303,
    )


@router.post("/contacts/{contact_id}/delete")
def delete_contact_workspace(
    contact_id: int,
    db: Session = Depends(get_db),
):
    from app.models.contact import Contact

    contact = db.get(Contact, contact_id)

    if contact is None:
        raise HTTPException(
            status_code=404,
            detail="Contact not found",
        )

    db.delete(contact)
    db.commit()

    return RedirectResponse(
        url="/workspace/contacts",
        status_code=303,
    )


@router.post(
    "/releases/{release_id}/promotion/email"
)
async def save_promo_email(
    release_id: int,
    request: Request,
):
    from app.models.contact import Contact
    from app.models.promo_campaign import PromoCampaign
    from app.models.promo_recipient import PromoRecipient

    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        form = await request.form()

        action = (
            form.get("action")
            or "save"
        ).strip()

        subject = (
            form.get("subject")
            or ""
        ).strip()

        body = (
            form.get("body")
            or ""
        ).strip()

        selected_types = set(
            form.getlist(
                "recipient_types"
            )
        )

        campaign = (
            db.query(PromoCampaign)
            .filter(
                PromoCampaign.release_id
                == release.id
            )
            .order_by(
                PromoCampaign.id.desc()
            )
            .first()
        )

        if campaign is None:
            campaign = PromoCampaign(
                release_id=release.id,
                name=f"{release.title} promo",
                status="draft",
            )

            db.add(campaign)
            db.flush()

        campaign.subject = subject
        campaign.body = body
        campaign.status = "draft"

        # Replace draft recipient selection.
        (
            db.query(PromoRecipient)
            .filter(
                PromoRecipient.campaign_id
                == campaign.id
            )
            .delete(
                synchronize_session=False
            )
        )

        if selected_types:
            contacts = (
                db.query(Contact)
                .filter(
                    Contact.do_not_contact
                    .is_(False),
                    Contact.contact_type
                    .in_(selected_types),
                )
                .all()
            )

            for contact in contacts:
                db.add(
                    PromoRecipient(
                        campaign_id=
                            campaign.id,
                        contact_id=
                            contact.id,
                        status="draft",
                    )
                )

        db.commit()

        if action == "review":
            destination = (
                f"/workspace/releases/"
                f"{release.id}/promotion/email/review"
            )
        else:
            destination = (
                f"/workspace/releases/"
                f"{release.id}/promotion"
                "?promo_email_status=saved"
            )

        return RedirectResponse(
            url=destination,
            status_code=303,
        )

    finally:
        db.close()


@router.get(
    "/releases/{release_id}/promotion/email/review"
)
def review_promo_email(
    release_id: int,
    request: Request,
):
    from app.models.promo_campaign import (
        PromoCampaign,
    )
    from app.models.promo_recipient import (
        PromoRecipient,
    )
    from app.services.promo.release_links import (
        get_release_links,
    )

    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        campaign = (
            db.query(PromoCampaign)
            .filter(
                PromoCampaign.release_id
                == release.id
            )
            .order_by(
                PromoCampaign.id.desc()
            )
            .first()
        )

        if campaign is None:
            return RedirectResponse(
                url=(
                    f"/workspace/releases/"
                    f"{release.id}/promotion"
                    "?promo_email_status=no_draft"
                ),
                status_code=303,
            )

        recipients = (
            db.query(PromoRecipient)
            .filter(
                PromoRecipient.campaign_id
                == campaign.id
            )
            .all()
        )

        type_counts = {}

        for recipient in recipients:
            contact_type = (
                recipient.contact.contact_type
                if recipient.contact
                else None
            ) or "other"

            type_counts[contact_type] = (
                type_counts.get(
                    contact_type,
                    0,
                )
                + 1
            )

        links = get_release_links(
            db,
            release,
        )

        return templates.TemplateResponse(
            request=request,
            name="workspace/promo_email_review.html",
            context={
                "release": release,
                "active_tab": "promotion",
                "campaign": campaign,
                "recipients": recipients,
                "type_counts": type_counts,
                "links": links,
            },
        )

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/promotion/email/send"
)
def send_release_promo_email(
    release_id: int,
):
    from app.models.promo_campaign import (
        PromoCampaign,
    )
    from app.services.promo.campaign_sender import (
        send_promo_campaign,
    )

    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        campaign = (
            db.query(PromoCampaign)
            .filter(
                PromoCampaign.release_id
                == release.id
            )
            .order_by(
                PromoCampaign.id.desc()
            )
            .first()
        )

        if campaign is None:
            return RedirectResponse(
                url=(
                    f"/workspace/releases/"
                    f"{release.id}/promotion"
                    "?promo_email_status=no_draft"
                ),
                status_code=303,
            )

        result = send_promo_campaign(
            db=db,
            campaign=campaign,
            release=release,
        )

        params = urlencode(
            {
                "promo_email_status": "sent",
                "sent": result["sent"],
                "failed": result["failed"],
            }
        )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release.id}/promotion?"
                f"{params}"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/assets/sync-promo"
)
def sync_release_promo_assets_workspace(
    release_id: int,
):
    from app.services.promo.promo_asset_sync import (
        sync_release_promo_assets,
    )

    db = SessionLocal()

    try:
        release = get_release_or_404(
            release_id
        )

        if not release.promo_folder_url:
            params = urlencode(
                {
                    "promo_asset_status": "error",
                    "promo_asset_message":
                        "No Dropbox promo folder configured.",
                }
            )

            return RedirectResponse(
                url=(
                    f"/workspace/releases/"
                    f"{release.id}/assets?{params}"
                ),
                status_code=303,
            )

        result = sync_release_promo_assets(
            db,
            release,
        )

        if result["errors"]:
            params = urlencode(
                {
                    "promo_asset_status": "warning",
                    "promo_asset_message":
                        " | ".join(result["errors"]),
                }
            )
        else:
            params = urlencode(
                {
                    "promo_asset_status": "success",
                    "promo_asset_message":
                        "Promo assets synced.",
                }
            )

        return RedirectResponse(
            url=(
                f"/workspace/releases/"
                f"{release.id}/assets?{params}"
            ),
            status_code=303,
        )

    finally:
        db.close()


@router.post(
    "/releases/{release_id}/promotion/youtube/short"
)
async def upload_release_youtube_short(
    release_id: int,
    request: Request,
):
    from pathlib import Path
    import tempfile

    from app.services.dropbox_service import (
        download_shared_folder_asset,
    )
    from app.services.youtube_upload_service import (
        upload_video,
    )

    form = await request.form()

    try:
        asset_id = int(form.get("asset_id", ""))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="A valid asset is required.",
        )

    title = (form.get("title") or "").strip()
    description = (
        form.get("description") or ""
    ).strip()

    privacy_status = (
        form.get("privacy_status") or "private"
    ).strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="YouTube title is required.",
        )

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube visibility.",
        )

    db = SessionLocal()
    temp_path = None

    try:
        asset = (
            db.query(Asset)
            .filter(
                Asset.id == asset_id,
                Asset.release_id == release_id,
                Asset.asset_type
                == "short_form_video",
            )
            .one_or_none()
        )

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Short-form video asset "
                    "not found."
                ),
            )

        if asset.youtube_video_id:
            raise RuntimeError(
                "This creative has already been "
                "uploaded to YouTube."
            )

        if not asset.source_url:
            raise RuntimeError(
                "Asset has no Dropbox source URL."
            )

        suffix = (
            Path(
                asset.file_name
                or asset.name
            ).suffix
            or ".mp4"
        )

        handle = tempfile.NamedTemporaryFile(
            prefix=(
                f"mmi_youtube_short_"
                f"{release_id}_"
            ),
            suffix=suffix,
            delete=False,
        )

        temp_path = handle.name
        handle.close()

        download_shared_folder_asset(
            shared_folder_url=
                asset.source_url,
            dropbox_file_id=
                asset.source_id,
            destination_path=
                temp_path,
        )

        result = upload_video(
            file_path=temp_path,
            title=title,
            description=description,
            privacy_status=privacy_status,
        )

        from datetime import datetime, timezone

        asset.youtube_video_id = (
            result["video_id"]
        )
        asset.youtube_url = (
            result["youtube_url"]
        )
        asset.youtube_privacy_status = (
            result["privacy_status"]
        )
        asset.youtube_uploaded_at = (
            datetime.now(timezone.utc)
        )

        db.commit()

        params = urlencode(
            {
                "youtube_status": "success",
                "youtube_message": (
                    "YouTube Short uploaded "
                    "successfully."
                ),
                "youtube_video_id":
                    result["video_id"],
                "youtube_url":
                    result["youtube_url"],
            }
        )

    except HTTPException:
        raise

    except Exception as exc:
        params = urlencode(
            {
                "youtube_status": "error",
                "youtube_message": str(exc),
            }
        )

    finally:
        if temp_path:
            Path(temp_path).unlink(
                missing_ok=True
            )

        db.close()

    return RedirectResponse(
        url=(
            f"/workspace/releases/"
            f"{release_id}/promotion?"
            f"{params}"
        ),
        status_code=303,
    )


@router.post(
    "/releases/{release_id}/promotion/youtube/full"
)
async def upload_release_youtube_full_video(
    release_id: int,
    request: Request,
):
    from pathlib import Path
    from datetime import datetime, timezone

    from app.services.youtube_release_upload_service import (
        download_release_music_video,
    )
    from app.services.youtube_upload_service import (
        upload_video,
    )

    form = await request.form()

    title = (
        form.get("title")
        or ""
    ).strip()

    description = (
        form.get("description")
        or ""
    ).strip()

    privacy_status = (
        form.get("privacy_status")
        or "private"
    ).strip()

    if not title:
        raise HTTPException(
            status_code=400,
            detail="YouTube title is required.",
        )

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube visibility.",
        )

    db = SessionLocal()
    temp_path = None

    try:
        release = (
            db.query(Release)
            .filter(
                Release.id == release_id
            )
            .one_or_none()
        )

        if release is None:
            raise HTTPException(
                status_code=404,
                detail="Release not found.",
            )

        asset = (
            db.query(Asset)
            .filter(
                Asset.release_id == release_id,
                Asset.asset_type == "music_video",
            )
            .one_or_none()
        )

        if asset is None:
            raise RuntimeError(
                "No music video asset is configured."
            )

        if asset.youtube_video_id:
            raise RuntimeError(
                "This music video has already been "
                "uploaded to YouTube."
            )

        temp_path, asset = (
            download_release_music_video(
                db,
                release,
            )
        )

        result = upload_video(
            file_path=temp_path,
            title=title,
            description=description,
            privacy_status=privacy_status,
        )

        asset.youtube_video_id = (
            result["video_id"]
        )

        asset.youtube_url = (
            result["youtube_url"]
        )

        asset.youtube_privacy_status = (
            result["privacy_status"]
        )

        asset.youtube_uploaded_at = (
            datetime.now(timezone.utc)
        )

        release.youtube_url = (
            result["youtube_url"]
        )

        db.commit()

        params = urlencode(
            {
                "youtube_status": "success",
                "youtube_message": (
                    "Full music video uploaded "
                    "successfully."
                ),
                "youtube_video_id":
                    result["video_id"],
                "youtube_url":
                    result["youtube_url"],
            }
        )

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()

        params = urlencode(
            {
                "youtube_status": "error",
                "youtube_message": str(exc),
            }
        )

    finally:
        if temp_path:
            Path(temp_path).unlink(
                missing_ok=True
            )

        db.close()

    return RedirectResponse(
        url=(
            f"/workspace/releases/"
            f"{release_id}/promotion?"
            f"{params}"
        ),
        status_code=303,
    )


@router.post(
    "/releases/{release_id}/promotion/youtube/visibility"
)
async def update_release_youtube_visibility(
    release_id: int,
    request: Request,
):
    from app.services.youtube_upload_service import (
        update_video_privacy,
    )

    form = await request.form()

    try:
        asset_id = int(
            form.get("asset_id", "")
        )
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=400,
            detail="A valid asset is required.",
        )

    privacy_status = (
        form.get("privacy_status")
        or ""
    ).strip()

    if privacy_status not in {
        "private",
        "unlisted",
        "public",
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid YouTube visibility.",
        )

    db = SessionLocal()

    try:
        asset = (
            db.query(Asset)
            .filter(
                Asset.id == asset_id,
                Asset.release_id == release_id,
            )
            .one_or_none()
        )

        if asset is None:
            raise HTTPException(
                status_code=404,
                detail="Asset not found.",
            )

        if not asset.youtube_video_id:
            raise RuntimeError(
                "This asset has not been uploaded "
                "to YouTube yet."
            )

        result = update_video_privacy(
            video_id=asset.youtube_video_id,
            privacy_status=privacy_status,
        )

        asset.youtube_privacy_status = (
            result["privacy_status"]
        )

        db.commit()

        params = urlencode(
            {
                "youtube_status": "success",
                "youtube_message": (
                    "YouTube visibility updated "
                    f"to {result['privacy_status']}."
                ),
                "youtube_url":
                    result["youtube_url"],
            }
        )

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()

        params = urlencode(
            {
                "youtube_status": "error",
                "youtube_message": str(exc),
            }
        )

    finally:
        db.close()

    return RedirectResponse(
        url=(
            f"/workspace/releases/"
            f"{release_id}/promotion?"
            f"{params}"
        ),
        status_code=303,
    )
