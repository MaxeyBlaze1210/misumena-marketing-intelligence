from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.services.recommendation_service import recommend_campaign


router = APIRouter(
    prefix="/recommendations",
    tags=["Recommendations"],
)


@router.get("/campaigns/{campaign_id}")
def campaign_recommendations(
    campaign_id: int,
    db: Session = Depends(get_db),
):
    return recommend_campaign(
        db=db,
        campaign_id=campaign_id,
    )