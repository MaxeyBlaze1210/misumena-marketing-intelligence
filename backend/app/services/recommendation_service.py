from sqlalchemy.orm import Session

from app.intelligence.recommendation_engine import (
    CreativePerformance,
    RecommendationEngine,
)
from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_campaign import MetaCampaign


def recommend_campaign(
    db: Session,
    campaign_id: int,
) -> dict:
    campaign = (
        db.query(MetaCampaign)
        .filter(MetaCampaign.id == campaign_id)
        .one_or_none()
    )

    if campaign is None:
        return {
            "campaign_id": campaign_id,
            "winner": None,
            "recommendations": [],
            "message": "Campaign not found.",
        }

    rows = (
        db.query(MetaAd, MetaAdMetric)
        .join(
            MetaAdMetric,
            MetaAdMetric.ad_id == MetaAd.id,
        )
        .filter(MetaAd.campaign_id == campaign.id)
        .all()
    )

    creatives = []

    for ad, metric in rows:
        cost_per_result = metric.cost_per_result

        if (
            cost_per_result is None
            and metric.results
            and metric.results > 0
        ):
            cost_per_result = metric.spend / metric.results

        creatives.append(
            CreativePerformance(
                name=clean_creative_name(ad.name),
                impressions=metric.impressions or 0,
                spend=metric.spend or 0,
                results=metric.results or 0,
                cost_per_result=cost_per_result,
            )
        )

    engine = RecommendationEngine()
    result = engine.evaluate(creatives)

    return {
        "campaign_id": campaign.id,
        "meta_campaign_id": campaign.meta_campaign_id,
        "campaign_name": campaign.name,
        **result,
    }

def clean_creative_name(name: str) -> str:
    marker = "Ife Tutu Creative "
    if marker in name:
        return f"Creative {name.split(marker, 1)[1]}"

    return name