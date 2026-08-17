from app.core.config import settings


def build_release_landing_url(
    release,
) -> str | None:
    if not release.landing_slug:
        return None

    public_base = (
        settings.promo_public_base_url
        or ""
    ).rstrip("/")

    if not public_base:
        return None

    return (
        f"{public_base}/r/"
        f"{release.landing_slug}"
    )
