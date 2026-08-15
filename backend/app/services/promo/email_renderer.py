from html import escape

from app.core.config import settings


def greeting_for(contact) -> str:
    if contact.greeting_name:
        return contact.greeting_name.strip()

    if contact.name:
        return contact.name.strip().split()[0]

    return ""


def build_promo_email(
    *,
    campaign,
    contact,
    links,
    tracking_token: str,
):
    greeting_name = greeting_for(contact)

    greeting_text = (
        f"Hello {greeting_name},"
        if greeting_name
        else "Hello,"
    )

    subject = (
        campaign.subject
        or campaign.name
        or "New music from Misumena"
    )

    body = campaign.body or ""

    public_base = (
        settings.promo_public_base_url
        or ""
    ).rstrip("/")

    tracking_enabled = bool(public_base)

    def destination(link_type):
        direct = links.get(link_type)

        if not direct:
            return None

        if tracking_enabled:
            return (
                f"{public_base}/t/click/"
                f"{tracking_token}/{link_type}"
            )

        return direct

    spotify = destination("spotify")
    apple = destination("apple_music")
    youtube = destination("youtube")
    dropbox = destination("dropbox")

    link_rows = []

    for label, url in [
        ("Spotify", spotify),
        ("Apple Music", apple),
        ("YouTube", youtube),
        ("Promo / download", dropbox),
    ]:
        if not url:
            continue

        link_rows.append(
            f'''
            <a
                href="{escape(url, quote=True)}"
                style="
                    display:inline-block;
                    margin:0 14px 8px 0;
                    color:#111111;
                    font-weight:600;
                "
            >{escape(label)}</a>
            '''
        )

    tracking_pixel = ""

    if tracking_enabled:
        tracking_pixel = (
            f'<img src="{public_base}/t/open/'
            f'{tracking_token}.gif" '
            f'width="1" height="1" alt="" '
            f'style="display:block;width:1px;height:1px;">'
        )

    html_body = f"""
    <html>
      <body
        style="
            font-family:Arial,Helvetica,sans-serif;
            color:#171717;
            line-height:1.55;
            font-size:15px;
        "
      >
        <p>{escape(greeting_text)}</p>

        <div style="white-space:pre-wrap;">
            {escape(body)}
        </div>

        <p style="margin-top:24px;">
            {''.join(link_rows)}
        </p>

        {tracking_pixel}
      </body>
    </html>
    """

    text_links = []

    for label, direct_url in [
        ("Spotify", links.get("spotify")),
        ("Apple Music", links.get("apple_music")),
        ("YouTube", links.get("youtube")),
        ("Promo / download", links.get("dropbox")),
    ]:
        if direct_url:
            text_links.append(
                f"{label}: {direct_url}"
            )

    text_body = "\n\n".join(
        [
            greeting_text,
            body,
            "\n".join(text_links),
        ]
    ).strip()

    return {
        "subject": subject,
        "html_body": html_body,
        "text_body": text_body,
        "tracking_enabled": tracking_enabled,
    }
