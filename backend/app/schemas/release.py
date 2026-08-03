from datetime import date

from pydantic import BaseModel, Field


class ReleaseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    artist: str = Field(..., min_length=1, max_length=200)
    release_date: date


class ReleaseCreate(ReleaseBase):
    pass


class ReleaseUpdate(ReleaseBase):
    pass


class ReleaseResponse(ReleaseBase):
    id: int

    class Config:
        from_attributes = True