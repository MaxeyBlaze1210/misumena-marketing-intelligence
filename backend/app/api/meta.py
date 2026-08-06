from fastapi import APIRouter

from app.database.database import SessionLocal

from app.models.meta_interest import MetaInterest

router = APIRouter(
    prefix="/meta",
    tags=["Meta"],
)

from app.services.meta_service import (
    get_ad_insights,
    get_ads,
    get_campaign_insights,
    get_campaigns,
    search_interests,
)


from app.services.meta_interest_service import (
    save_meta_interests,
)

@router.get("/campaigns")
def campaigns():
    return get_campaigns()


@router.get("/campaigns/{campaign_id}/insights")
def campaign_insights(campaign_id: str):
    return get_campaign_insights(campaign_id)


@router.get("/campaigns/{campaign_id}/ads")
def campaign_ads(campaign_id: str):
    return get_ads(campaign_id)  

@router.get("/campaigns/{campaign_id}/ad-insights")
def campaign_ad_insights(campaign_id: str):
    return get_ad_insights(campaign_id)  

@router.get("/interests/search")
def interest_search(q: str):

    results = search_interests(q)

    db = SessionLocal()

    try:

        save_meta_interests(
            db=db,
            search_query=q,
            interests=results["data"],
        )

    finally:
        db.close()

    return results 

@router.get("/interests")
def list_interests():

    db = SessionLocal()

    try:

        interests = (
            db.query(MetaInterest)
            .order_by(
                MetaInterest.name
            )
            .all()
        )

        return interests

    finally:
        db.close()    


