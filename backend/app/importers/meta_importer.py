from datetime import date

from app.database.database import SessionLocal
from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_campaign import MetaCampaign
from app.services.meta_service import (
    get_ad_insights,
    get_ads,
    get_campaigns,
)
from app.database.init_db import init_db

CAMPAIGN_ID = "120248946076850207"
RELEASE_ID = 1

RESULT_ACTION = "offsite_conversion.fb_pixel_view_content"


def find_action_value(items: list[dict], action_type: str) -> float | None:
    for item in items or []:
        if item.get("action_type") == action_type:
            return float(item["value"])

    return None


def import_meta_campaign(
    campaign_id: str,
    release_id: int | None = None,
) -> None:
    init_db()

    db = SessionLocal()

    try:
        campaigns_response = get_campaigns()
        ads_response = get_ads(campaign_id)
        insights_response = get_ad_insights(campaign_id)

        campaign_data = next(
            (
                item
                for item in campaigns_response.get("data", [])
                if item["id"] == campaign_id
            ),
            None,
        )

        if campaign_data is None:
            raise ValueError(
                f"Campaign {campaign_id} was not found."
            )

        campaign = (
            db.query(MetaCampaign)
            .filter(
                MetaCampaign.meta_campaign_id == campaign_id
            )
            .one_or_none()
        )

        if campaign is None:
            campaign = MetaCampaign(
                meta_campaign_id=campaign_id,
            )
            db.add(campaign)

        campaign.release_id = release_id
        campaign.name = campaign_data["name"]
        campaign.status = campaign_data.get("status")
        campaign.objective = campaign_data.get("objective")

        db.flush()

        ads_by_meta_id: dict[str, MetaAd] = {}

        for ad_data in ads_response.get("data", []):
            meta_ad_id = ad_data["id"]

            ad = (
                db.query(MetaAd)
                .filter(MetaAd.meta_ad_id == meta_ad_id)
                .one_or_none()
            )

            if ad is None:
                ad = MetaAd(
                    meta_ad_id=meta_ad_id,
                    campaign_id=campaign.id,
                )
                db.add(ad)

            ad.campaign_id = campaign.id
            ad.name = ad_data["name"]
            ad.status = ad_data.get("status")
            ad.meta_creative_id = (
                ad_data.get("creative", {}).get("id")
            )
            ad.meta_adset_id = (
                ad_data.get("adset", {}).get("id")
            )

            db.flush()
            ads_by_meta_id[meta_ad_id] = ad

        imported_metrics = 0

        for metric_data in insights_response.get("data", []):
            meta_ad_id = metric_data["ad_id"]
            ad = ads_by_meta_id.get(meta_ad_id)

            if ad is None:
                continue

            date_start = date.fromisoformat(
                metric_data["date_start"]
            )
            date_stop = date.fromisoformat(
                metric_data["date_stop"]
            )

            metric = (
                db.query(MetaAdMetric)
                .filter(
                    MetaAdMetric.ad_id == ad.id,
                    MetaAdMetric.date_start == date_start,
                    MetaAdMetric.date_stop == date_stop,
                )
                .one_or_none()
            )

            if metric is None:
                metric = MetaAdMetric(
                    ad_id=ad.id,
                    date_start=date_start,
                    date_stop=date_stop,
                )
                db.add(metric)

            actions = metric_data.get("actions", [])
            costs = metric_data.get(
                "cost_per_action_type",
                [],
            )

            metric.spend = float(
                metric_data.get("spend", 0)
            )
            metric.impressions = int(
                metric_data.get("impressions", 0)
            )
            metric.reach = int(
                metric_data.get("reach", 0)
            )
            metric.clicks = int(
                metric_data.get("clicks", 0)
            )
            metric.ctr = float(
                metric_data.get("ctr", 0)
            )
            metric.cpc = float(
                metric_data.get("cpc", 0)
            )

            metric.landing_page_views = int(
                find_action_value(
                    actions,
                    "landing_page_view",
                )
                or 0
            )
            metric.cost_per_landing_page_view = (
                find_action_value(
                    costs,
                    "landing_page_view",
                )
            )

            metric.results = int(
                find_action_value(
                    actions,
                    RESULT_ACTION,
                )
                or 0
            )
            metric.cost_per_result = (
                find_action_value(
                    costs,
                    RESULT_ACTION,
                )
            )

            metric.video_views = int(
                find_action_value(
                    actions,
                    "video_view",
                )
                or 0
            )

            imported_metrics += 1

        db.commit()

        print(
            "Imported "
            f"1 campaign, "
            f"{len(ads_by_meta_id)} ads, "
            f"{imported_metrics} metric rows."
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    import_meta_campaign(
        campaign_id=CAMPAIGN_ID,
        release_id=RELEASE_ID,
    )

    