from fastapi import FastAPI

from app.database.init_db import init_db
from app.api.releases import router as releases_router
from app.api.youtube import router as youtube_router
from app.api.tracks import router as tracks_router

app = FastAPI(
    title="Misumena Marketing Intelligence",
    version="0.1",
)

# Create database tables
init_db()

# Register API routes
app.include_router(releases_router)
app.include_router(youtube_router)
app.include_router(tracks_router)


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
        "status": "ok"
    }