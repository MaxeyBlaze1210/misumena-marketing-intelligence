from datetime import date
from pydantic import BaseModel


class ReleaseCreate(BaseModel):
    title: str
    artist: str
    release_date: date


class ReleaseUpdate(BaseModel):
    title: str | None = None
    artist: str | None = None
    release_date: date | None = None


class ReleaseResponse(BaseModel):
    id: int
    title: str
    artist: str
    release_date: date

    model_config = {
        "from_attributes": True
    }