from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import (
    HTMLResponse,
    RedirectResponse,
    Response,
)
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.database.database import SessionLocal
from app.models.landing_event import LandingEvent
from app.models.release import Release


router = APIRouter(
    prefix="/r",
    tags=["Landing Pages"],
)

templates = Jinja2Templates(
    directory="app/templates"
)


def get_release_by_slug(
    db,
    slug: str,
) -> Release:
    release = (
        db.query(Release)
        .filter(
            Release.landing_slug == slug
        )
        .one_or_none()
    )

    if release is None:
        raise HTTPException(
            status_code=404,
            detail="Release not found.",
        )

    return release


@router.get(
    "/{slug}",
    response_class=HTMLResponse,
)
def landing_page(
    request: Request,
    slug: str,
):
    db = SessionLocal()

    try:
        release = get_release_by_slug(
            db,
            slug,
        )

        return templates.TemplateResponse(
            request=request,
            name="landing_page.html",
            context={
                "release": release,
                "meta_pixel_id":
                    settings.meta_pixel_id,
            },
        )

    finally:
        db.close()


@router.post(
    "/{slug}/event/pageview",
    status_code=204,
)
def track_landing_pageview(
    slug: str,
):
    db = SessionLocal()

    try:
        release = get_release_by_slug(
            db,
            slug,
        )

        db.add(
            LandingEvent(
                release_id=release.id,
                event_type="pageview",
            )
        )

        db.commit()

        return Response(
            status_code=204
        )

    finally:
        db.close()


@router.get(
    "/{slug}/go/{platform}",
)
def landing_platform_click(
    slug: str,
    platform: str,
):
    allowed = {
        "spotify",
        "apple_music",
        "youtube",
        "bandcamp",
    }

    if platform not in allowed:
        raise HTTPException(
            status_code=404,
            detail="Unknown landing-page platform.",
        )

    db = SessionLocal()

    try:
        release = get_release_by_slug(
            db,
            slug,
        )

        destinations = {
            "spotify":
                release.spotify_url,
            "apple_music":
                release.apple_music_url,
            "youtube":
                release.youtube_url,
            "bandcamp":
                release.bandcamp_url,
        }

        destination = destinations.get(
            platform
        )

        if not destination:
            raise HTTPException(
                status_code=404,
                detail="Release link unavailable.",
            )

        db.add(
            LandingEvent(
                release_id=release.id,
                event_type="platform_click",
                platform=platform,
            )
        )

        db.commit()

        return RedirectResponse(
            url=destination,
            status_code=302,
        )

    finally:
        db.close()
