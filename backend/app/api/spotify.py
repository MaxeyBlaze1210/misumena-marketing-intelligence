from fastapi import APIRouter

from app.schemas.spotify import SpotifyImportRequest
from app.services.spotify_service import (
    search_track,
    get_album,
    get_album_tracks,
    get_track,
)

from app.database.database import SessionLocal
from app.models.release import Release
from app.models.track import Track
from datetime import date

router = APIRouter(
    prefix="/spotify",
    tags=["Spotify"],
)


@router.get("/search")
def spotify_search(query: str):
    return search_track(query)


@router.post("/import")
def spotify_import(request: SpotifyImportRequest):
    db = SessionLocal()

    try:
        album = get_album(request.album_id)
        tracks = get_album_tracks(request.album_id)

        existing_release = (
            db.query(Release)
            .filter(Release.spotify_album_id == album["id"])
            .first()
        )

        if existing_release:
            return {
                "message": "Release already imported",
                "release_id": existing_release.id,
            }

        release = Release(
            title=album["name"],
            artist=album["artists"][0]["name"],
            release_date=date.fromisoformat(album["release_date"]),
            spotify_album_id=album["id"],
            artwork_url=album["images"][0]["url"] if album["images"] else None,
        )

        db.add(release)
        db.commit()
        db.refresh(release)

        for spotify_track in tracks:
            full_track = get_track(spotify_track["id"])

            track = Track(
                title=full_track["name"],
                isrc=full_track["external_ids"].get("isrc"),
                spotify_track_id=full_track["id"],
                duration_ms=full_track["duration_ms"],
                track_number=full_track["track_number"],
                release_id=release.id,
            )

            db.add(track)

        db.commit()

        return {
            "release_id": release.id,
            "title": release.title,
            "tracks_imported": len(tracks),
        }

    finally:
        db.close()