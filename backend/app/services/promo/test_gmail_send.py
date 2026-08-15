import sys

from app.database.database import SessionLocal

# Register the full SQLAlchemy model graph before querying.
import app.database.init_db  # noqa: F401

from app.models.release import Release
from app.services.promo.gmail_sender import send_email
from app.services.promo.release_links import get_release_links


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python -m "
            "app.services.promo.test_gmail_send "
            "<recipient_email>"
        )
        raise SystemExit(1)

    to_email = sys.argv[1]

    db = SessionLocal()

    try:
        release = db.get(
            Release,
            1,
        )

        if release is None:
            raise RuntimeError(
                "Release ID 1 not found in MMI."
            )

        links = get_release_links(
            db,
            release,
        )

        html_body = f"""
        <html>
          <body>
            <p>Hello,</p>

            <p>
              we're super happy to share this with you —
              our first collab with Shaamar from Lagos,
              Nigeria. Make sure to check out the video too!
            </p>

            <p>
              <a href="{links['spotify']}">
                Spotify
              </a>
              &nbsp;·&nbsp;

              <a href="{links['apple_music']}">
                Apple Music
              </a>
              &nbsp;·&nbsp;

              <a href="{links['youtube']}">
                YouTube
              </a>
            </p>

            <p>
              <a href="{links['dropbox']}">
                Promo / download
              </a>
            </p>
          </body>
        </html>
        """

        text_body = f"""
Hello,

we're super happy to share this with you — our first
collab with Shaamar from Lagos, Nigeria.

Spotify: {links['spotify']}
Apple Music: {links['apple_music']}
YouTube: {links['youtube']}
Promo / download: {links['dropbox']}
""".strip()

        result = send_email(
            to_email=to_email,
            subject="Promo - Misumena - Ife Tutu (feat. Shaamar)",
            text_body=text_body,
            html_body=html_body,
        )

        print()
        print("Email sent.")
        print("Gmail message ID:", result.get("id"))
        print()

    finally:
        db.close()


if __name__ == "__main__":
    main()
