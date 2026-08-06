from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.database.database import SessionLocal
from app.models.release import Release
from fastapi.staticfiles import StaticFiles

router = APIRouter(
    prefix="/r",
    tags=["Landing Pages"],
)

templates = Jinja2Templates(directory="app/templates")


@router.get("/{slug}", response_class=HTMLResponse)
def landing_page(
    request: Request,
    slug: str,
):
    db = SessionLocal()

    release = (
        db.query(Release)
        .filter(Release.landing_slug == slug)
        .first()
    )

    db.close()

    if release is None:
        raise HTTPException(
            status_code=404,
            detail="Release not found.",
        )

    return templates.TemplateResponse(
        request=request,
        name="landing_page.html",
        context={
            "release": release,
        },
    )