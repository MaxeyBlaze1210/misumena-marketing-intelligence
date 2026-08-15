from datetime import datetime, timezone
from uuid import uuid4

from app.models.promo_recipient import PromoRecipient
from app.services.promo.email_renderer import (
    build_promo_email,
)
from app.services.promo.gmail_sender import (
    send_email,
)
from app.services.promo.release_links import (
    get_release_links,
)


def send_promo_campaign(
    *,
    db,
    campaign,
    release,
):
    links = get_release_links(
        db,
        release,
    )

    recipients = (
        db.query(PromoRecipient)
        .filter(
            PromoRecipient.campaign_id
            == campaign.id,
            PromoRecipient.status
            != "sent",
        )
        .all()
    )

    sent = 0
    failed = 0

    for recipient in recipients:
        contact = recipient.contact

        if (
            not contact
            or contact.do_not_contact
            or not contact.email
        ):
            recipient.status = "skipped"
            recipient.error_message = (
                "Contact unavailable or marked do-not-contact."
            )
            continue

        if not recipient.tracking_token:
            recipient.tracking_token = uuid4().hex

        rendered = build_promo_email(
            campaign=campaign,
            contact=contact,
            links=links,
            tracking_token=
                recipient.tracking_token,
        )

        recipient.personalized_subject = (
            rendered["subject"]
        )

        recipient.personalized_body = (
            rendered["text_body"]
        )

        try:
            send_email(
                to_email=contact.email,
                subject=rendered["subject"],
                html_body=rendered["html_body"],
                text_body=rendered["text_body"],
            )

            recipient.status = "sent"
            recipient.sent_at = datetime.now(
                timezone.utc
            )
            recipient.error_message = None
            sent += 1

        except Exception as exc:
            recipient.status = "failed"
            recipient.error_message = str(exc)
            failed += 1

        # Persist each recipient individually so a later
        # failure cannot erase successful sends.
        db.commit()

    campaign.status = (
        "sent"
        if failed == 0
        else "partially_sent"
    )

    db.commit()

    return {
        "sent": sent,
        "failed": failed,
        "total": len(recipients),
    }
