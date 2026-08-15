from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database.init_db import init_db

from app.api.releases import router as releases_router
from app.api.youtube import router as youtube_router
from app.api.tracks import router as tracks_router
from app.api.spotify import router as spotify_router
from app.api.meta import router as meta_router

from app.api import recommendations
from app.api import landing_pages
from app.api import workspace
from app.api import promo_tracking
from app.api import campaign_builder


app = FastAPI(
    title="Misumena Marketing Intelligence",
    version="0.1",
)


app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static",
)


# Create database tables
init_db()


# Register API routes
app.include_router(releases_router)
app.include_router(youtube_router)
app.include_router(tracks_router)
app.include_router(spotify_router)
app.include_router(recommendations.router)
app.include_router(meta_router)
app.include_router(landing_pages.router)

# Workspace page routes
app.include_router(workspace.router)
app.include_router(promo_tracking.router)

# Campaign Builder write actions
app.include_router(campaign_builder.router)


@app.get("/")
def root():
    return {
        "project": "Misumena Marketing Intelligence",
        "version": "0.1",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
    }