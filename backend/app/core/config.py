from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # YouTube
    youtube_api_key: str

    # Spotify
    spotify_client_id: str
    spotify_client_secret: str

    # Meta
    meta_access_token: str
    meta_api_version: str = "v26.0"
    meta_ad_account_id: str

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
    )


settings = Settings()