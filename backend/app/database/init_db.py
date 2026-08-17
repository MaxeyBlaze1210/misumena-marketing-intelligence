from app.database.database import Base, engine

# Core
from app.models.release import Release
from app.models.track import Track
from app.models.artist import Artist
from app.models.release_artist import ReleaseArtist

# YouTube
from app.models.youtube_video import YouTubeVideo
from app.models.youtube_metric import YouTubeMetric
from app.models.youtube_recommendation import YouTubeRecommendation

# Bandcamp
from app.models.bandcamp_sale import BandcampSale
from app.models.youtube_discovery_metric import (
    YouTubeDiscoveryMetric,
)

# Meta
from app.models.meta_interest import MetaInterest
from app.models.meta_campaign import MetaCampaign
from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_creative import MetaCreative
from app.models.meta_audience import MetaAudience
from app.models.meta_audience_interest import MetaAudienceInterest
from app.models.meta_campaign_plan import MetaCampaignPlan
from app.models.meta_campaign_variant import MetaCampaignVariant
from app.models.meta_campaign_cell import MetaCampaignCell
from app.models.meta_campaign_variant_interest import (
    MetaCampaignVariantInterest,
)

# Historical Meta evidence
from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_targeting_item import (
    MetaAdSetTargetingItem,
)
from app.models.meta_adset_metric import MetaAdSetMetric

# Countries
from app.models.country import Country
from app.models.country_preset import CountryPreset
from app.models.country_preset_country import CountryPresetCountry

# Promo / Contacts
from app.models.contact import Contact
from app.models.promo_campaign import PromoCampaign
from app.models.promo_recipient import PromoRecipient
from app.models.promo_click import PromoClick
from app.models.landing_event import LandingEvent

# Assets
from app.models.asset import Asset
from app.models.meta_campaign_plan_asset import (
    MetaCampaignPlanAsset,
)


def init_db():
    Base.metadata.create_all(
        bind=engine
    )


if __name__ == "__main__":
    init_db()
    print("Database initialized.")
