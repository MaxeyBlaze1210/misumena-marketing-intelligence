from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from app.database.database import SessionLocal
from app.models.release import Release
from app.models.meta_audience import MetaAudience
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_audience_interest import MetaAudienceInterest
from app.models.meta_interest import MetaInterest
from app.models.country_preset import CountryPreset
from app.models.country_preset_country import CountryPresetCountry
from app.models.country import Country


router = APIRouter(
    prefix="/workspace",
    tags=["Workspace"],
)

templates = Jinja2Templates(directory="app/templates")

def get_release_or_404(release_id: int) -> Release:
    db = SessionLocal()

    try:
        release = (
            db.query(Release)
            .filter(Release.id == release_id)
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
def release_list(request: Request):
    db = SessionLocal()

    try:
        releases = (
            db.query(Release)
            .order_by(Release.release_date.desc())
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


@router.get("/releases/{release_id}")
def release_workspace(release_id: int):
    return RedirectResponse(
        url=f"/workspace/releases/{release_id}/promotion",
        status_code=302,
    )


@router.get("/releases/{release_id}/promotion")
def release_promotion(
    release_id: int,
    request: Request,
):
    db = SessionLocal()

    try:
        release = get_release_or_404(release_id)

        meta_audiences = (
            db.query(MetaAudience)
            .order_by(MetaAudience.id)
            .all()
        )

        campaign_plan = (
            db.query(MetaCampaignPlan)
            .filter(MetaCampaignPlan.release_id == release_id)
            .one_or_none()
        )

        selected_country_preset = None
        selected_country_count = 0
        selected_countries = []

        if campaign_plan and campaign_plan.country_preset_id:
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
                .order_by(Country.name)
                .all()
            )

        trusted_interests = []

        if campaign_plan is not None:
            trusted_interests = (
                db.query(MetaAudienceInterest)
                .join(
                    MetaInterest,
                    MetaAudienceInterest.meta_interest_id
                    == MetaInterest.id,
                )
                .filter(
                    MetaAudienceInterest.meta_audience_id
                    == campaign_plan.meta_audience_id,
                    MetaAudienceInterest.role == "trusted",
                )
                .order_by(MetaInterest.name)
                .all()
            )

        return templates.TemplateResponse(
            request=request,
            name="workspace/promotion.html",
            context={
                "release": release,
                "active_tab": "promotion",
                "meta_audiences": meta_audiences,
                "campaign_plan": campaign_plan,
                "trusted_interests": trusted_interests,
                "selected_country_preset": selected_country_preset,
                "selected_country_count": selected_country_count,
                "selected_countries": selected_countries,
            },
        )

    finally:
        db.close()

@router.get("/releases/{release_id}/analytics")
def release_analytics(
    release_id: int,
    request: Request,
):
    release = get_release_or_404(release_id)

    return templates.TemplateResponse(
        request=request,
        name="workspace/analytics.html",
        context={
            "release": release,
            "active_tab": "analytics",
        },
    )


@router.get("/releases/{release_id}/intelligence")
def release_intelligence(
    release_id: int,
    request: Request,
):
    release = get_release_or_404(release_id)

    return templates.TemplateResponse(
        request=request,
        name="workspace/intelligence.html",
        context={
            "release": release,
            "active_tab": "intelligence",
        },
    )


@router.get("/releases/{release_id}/release")
def release_information(
    release_id: int,
    request: Request,
):
    release = get_release_or_404(release_id)

    return templates.TemplateResponse(
        request=request,
        name="workspace/release.html",
        context={
            "release": release,
            "active_tab": "release",
        },
    )


@router.get("/releases/{release_id}/assets")
def release_assets(
    release_id: int,
    request: Request,
):
    release = get_release_or_404(release_id)

    return templates.TemplateResponse(
        request=request,
        name="workspace/assets.html",
        context={
            "release": release,
            "active_tab": "assets",
        },
    )   
