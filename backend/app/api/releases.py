from sqlalchemy.orm import Session

from fastapi import APIRouter, Depends, HTTPException

from app.database.database import get_db
from app.schemas.release import (
    ReleaseCreate,
    ReleaseUpdate,
    ReleaseResponse,
)
from app.services import release_service

router = APIRouter(
    prefix="/releases",
    tags=["Releases"],
)


@router.get("/", response_model=list[ReleaseResponse])
def get_releases(db: Session = Depends(get_db)):
    return release_service.get_releases(db)


@router.get("/{release_id}", response_model=ReleaseResponse)
def get_release(release_id: int, db: Session = Depends(get_db)):
    release = release_service.get_release(db, release_id)

    if release is None:
        raise HTTPException(status_code=404, detail="Release not found")

    return release


@router.post("/", response_model=ReleaseResponse)
def create_release(
    release: ReleaseCreate,
    db: Session = Depends(get_db),
):
    return release_service.create_release(db, release)


@router.put("/{release_id}", response_model=ReleaseResponse)
def update_release(
    release_id: int,
    release: ReleaseUpdate,
    db: Session = Depends(get_db),
):
    updated = release_service.update_release(db, release_id, release)

    if updated is None:
        raise HTTPException(status_code=404, detail="Release not found")

    return updated


@router.delete("/{release_id}")
def delete_release(
    release_id: int,
    db: Session = Depends(get_db),
):
    deleted = release_service.delete_release(db, release_id)

    if deleted is None:
        raise HTTPException(status_code=404, detail="Release not found")

    return {"message": "Release deleted successfully"}