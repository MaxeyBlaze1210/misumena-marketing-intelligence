from fastapi import APIRouter

from app.services.youtube_service import search_videos

router = APIRouter(
    prefix="/youtube",
    tags=["YouTube"],
)


@router.get("/search")
def search(query: str):
    return search_videos(query)