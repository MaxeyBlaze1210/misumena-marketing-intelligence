from datetime import date

from pydantic import BaseModel


class ReleaseBase(BaseModel):
    title: str
    artist: str
    release_date: date


class ReleaseCreate(ReleaseBase):
    pass


class ReleaseUpdate(ReleaseBase):
    pass


class ReleaseResponse(ReleaseBase):
    id: int

    model_config = {
        "from_attributes": True
    }