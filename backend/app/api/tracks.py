from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app.database.database import get_db
from app.schemas.track import TrackCreate, TrackResponse
from app.services import track_service

router = APIRouter(
    prefix="/tracks",
    tags=["Tracks"],
)


@router.get("/", response_model=list[TrackResponse])
def get_tracks(db: Session = Depends(get_db)):
    return track_service.get_tracks(db)


@router.get("/{track_id}", response_model=TrackResponse)
def get_track(track_id: int, db: Session = Depends(get_db)):
    track = track_service.get_track(db, track_id)

    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return track


@router.post("/", response_model=TrackResponse)
def create_track(
    track: TrackCreate,
    db: Session = Depends(get_db),
):
    return track_service.create_track(db, track)


@router.put("/{track_id}", response_model=TrackResponse)
def update_track(
    track_id: int,
    track: TrackCreate,
    db: Session = Depends(get_db),
):
    updated = track_service.update_track(db, track_id, track)

    if updated is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return updated


@router.delete("/{track_id}")
def delete_track(
    track_id: int,
    db: Session = Depends(get_db),
):
    deleted = track_service.delete_track(db, track_id)

    if deleted is None:
        raise HTTPException(status_code=404, detail="Track not found")

    return {"message": "Track deleted successfully"}