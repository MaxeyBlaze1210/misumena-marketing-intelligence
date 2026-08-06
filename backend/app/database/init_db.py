from app.database.database import Base, engine

# Import every model here
from app.models.meta_interest import MetaInterest
from app.models.release import Release
from app.models.track import Track
from app.models.artist import Artist
from app.models.release_artist import ReleaseArtist
from app.models.youtube_video import YouTubeVideo
from app.models.youtube_metric import YouTubeMetric
from app.models.youtube_recommendation import YouTubeRecommendation
from app.models.meta_campaign import MetaCampaign
from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_audience import MetaAudience
from app.models.meta_audience_interest import MetaAudienceInterest
from app.models.meta_campaign_plan import MetaCampaignPlan

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database initialized.")    