from sqlalchemy.orm import Session

from app.models.release import Release
from app.schemas.release import ReleaseCreate


def get_releases(db: Session):
    return db.query(Release).all()


def get_release(db: Session, release_id: int):
    return db.query(Release).filter(Release.id == release_id).first()


def create_release(db: Session, release: ReleaseCreate):
    db_release = Release(
        title=release.title,
        artist=release.artist,
        release_date=release.release_date,
    )

    db.add(db_release)
    db.commit()
    db.refresh(db_release)

    return db_release