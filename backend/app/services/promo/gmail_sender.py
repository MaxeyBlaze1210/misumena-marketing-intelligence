import base64
from email.message import EmailMessage

from app.services.promo.gmail_auth import get_gmail_service


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str | None = None,
):
    message = EmailMessage()

    message["From"] = "Misumena Music <misumenamusic@gmail.com>"
    message["To"] = to_email
    message["Subject"] = subject

    if text_body is None:
        text_body = "Please view this message in an HTML-capable email client."

    message.set_content(text_body)
    message.add_alternative(
        html_body,
        subtype="html",
    )

    encoded = base64.urlsafe_b64encode(
        message.as_bytes()
    ).decode()

    service = get_gmail_service()

    result = (
        service.users()
        .messages()
        .send(
            userId="me",
            body={
                "raw": encoded,
            },
        )
        .execute()
    )

    return result
