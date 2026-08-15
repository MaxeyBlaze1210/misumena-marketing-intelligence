from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse, Response

from app.database.database import SessionLocal
from app.models.promo_campaign import PromoCampaign
from app.models.promo_click import PromoClick
from app.models.promo_recipient import PromoRecipient
from app.models.release import Release
from app.services.promo.release_links import get_release_links


router = APIRouter(
    prefix="/t",
    tags=["Promo Tracking"],
)


# 1x1 transparent GIF
TRANSPARENT_GIF = bytes.fromhex(
    "47494638396101000100800000"
    "000000ffffff21f90401000000"
    "002c0000000001000100000202"
    "4401003b"
)


@router.get("/open/{token}.gif")
def track_open(token: str):
    db = SessionLocal()

    try:
        recipient = (
            db.query(PromoRecipient)
            .filter(
                PromoRecipient.tracking_token == token
            )
            .one_or_none()
        )

        if recipient is not None:
            now = datetime.now(timezone.utc)

            if recipient.first_opened_at is None:
                recipient.first_opened_at = now

            recipient.last_opened_at = now
            recipient.open_count = (
                recipient.open_count or 0
            ) + 1

            db.commit()

        # Always return an image.
        # Do not reveal whether the token exists.
        return Response(
            content=TRANSPARENT_GIF,
            media_type="image/gif",
            headers={
                "Cache-Control":
                    "no-store, no-cache, must-revalidate, max-age=0",
            },
        )

    finally:
        db.close()


@router.get("/click/{token}/{link_type}")
def track_click(
    token: str,
    link_type: str,
):
    allowed = {
        "spotify",
        "apple_music",
        "youtube",
        "dropbox",
    }

    if link_type not in allowed:
        raise HTTPException(
            status_code=404,
            detail="Unknown promo link.",
        )

    db = SessionLocal()

    try:
        recipient = (
            db.query(PromoRecipient)
            .filter(
                PromoRecipient.tracking_token == token
            )
            .one_or_none()
        )

        if recipient is None:
            raise HTTPException(
                status_code=404,
                detail="Unknown tracking token.",
            )

        campaign = db.get(
            PromoCampaign,
            recipient.campaign_id,
        )

        if campaign is None:
            raise HTTPException(
                status_code=404,
                detail="Campaign not found.",
            )

        release = db.get(
            Release,
            campaign.release_id,
        )

        if release is None:
            raise HTTPException(
                status_code=404,
                detail="Release not found.",
            )

        links = get_release_links(
            db,
            release,
        )

        destination = links.get(
            link_type
        )

        if not destination:
            raise HTTPException(
                status_code=404,
                detail="Release link unavailable.",
            )

        db.add(
            PromoClick(
                recipient_id=recipient.id,
                link_type=link_type,
            )
        )

        db.commit()

        return RedirectResponse(
            url=destination,
            status_code=302,
        )

    finally:
        db.close()
