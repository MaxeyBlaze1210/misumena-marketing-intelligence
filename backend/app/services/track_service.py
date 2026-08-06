from sqlalchemy.orm import Session

from app.models.track import Track


def get_tracks(db: Session):
    return db.query(Track).all()


def get_track(db: Session, track_id: int):
    return (
        db.query(Track)
        .filter(Track.id == track_id)
        .first()
    )