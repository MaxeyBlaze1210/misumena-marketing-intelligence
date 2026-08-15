from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    # YouTube
    youtube_api_key: str

    # Spotify
    spotify_client_id: str
    spotify_client_secret: str

    # Spotify playlist mirror
    spotify_playlist_client_id: str | None = None
    spotify_playlist_client_secret: str | None = None

    # Meta
    meta_access_token: str
    meta_api_version: str = "v26.0"
    meta_ad_account_id: str
    meta_page_id: str
    meta_instagram_user_id: str

    # Promo email
    promo_public_base_url: str | None = None

    # OpenAI
    openai_api_key: str

    # Dropbox
    dropbox_access_token: str | None = None
    dropbox_refresh_token: str | None = None
    dropbox_app_key: str | None = None
    dropbox_app_secret: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()