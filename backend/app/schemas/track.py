from pydantic import BaseModel


class TrackCreate(BaseModel):
    title: str
    isrc: str | None = None
    spotify_id: str | None = None
    duration_ms: int | None = None
    release_id: int


class TrackResponse(TrackCreate):
    id: int

    model_config = {
        "from_attributes": True
    }