from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.config import settings
from app.database.database import SessionLocal
from app.models.playlist import Playlist
from app.models.playlist_landing_event import PlaylistLandingEvent


router = APIRouter(
    prefix="/p",
    tags=["Playlist Landing Pages"],
)

templates = Jinja2Templates(
    directory="app/templates",
)


def get_playlist(db, playlist_id: int) -> Playlist:
    playlist = db.get(Playlist, playlist_id)

    if playlist is None:
        raise HTTPException(
            status_code=404,
            detail="Playlist not found.",
        )

    return playlist


def get_spotify_destination(playlist: Playlist) -> str:
    destination = playlist.spotify_url

    if not destination:
        raise HTTPException(
            status_code=404,
            detail="Spotify destination unavailable.",
        )

    parsed = urlsplit(destination)

    if (
        parsed.scheme != "https"
        or parsed.netloc != "open.spotify.com"
        or not parsed.path.startswith("/playlist/")
    ):
        raise HTTPException(
            status_code=500,
            detail="Invalid Spotify playlist destination.",
        )

    return destination


def record_event(
    db,
    playlist_id: int,
    event_type: str,
    platform: str | None = None,
) -> None:
    db.add(
        PlaylistLandingEvent(
            playlist_id=playlist_id,
            event_type=event_type,
            platform=platform,
        )
    )
    db.commit()


@router.get(
    "/{playlist_id}",
    response_class=HTMLResponse,
)
def playlist_landing_page(
    request: Request,
    playlist_id: int,
):
    db = SessionLocal()

    try:
        playlist = get_playlist(db, playlist_id)
        get_spotify_destination(playlist)

        record_event(
            db,
            playlist.id,
            "pageview",
        )

        return templates.TemplateResponse(
            request=request,
            name="playlist_landing_page.html",
            context={
                "playlist": playlist,
                "meta_pixel_id": settings.meta_pixel_id,
            },
        )

    finally:
        db.close()


@router.get("/{playlist_id}/go/spotify")
def playlist_spotify_click(playlist_id: int):
    db = SessionLocal()

    try:
        playlist = get_playlist(db, playlist_id)

        destination = get_spotify_destination(
            playlist
        )

        record_event(
            db,
            playlist.id,
            "platform_click",
            "spotify",
        )

        return RedirectResponse(
            url=destination,
            status_code=302,
        )

    finally:
        db.close()
