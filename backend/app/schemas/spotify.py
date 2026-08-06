from pydantic import BaseModel


class SpotifyImportRequest(BaseModel):
    album_id: str