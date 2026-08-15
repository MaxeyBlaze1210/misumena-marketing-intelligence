from app.core.config import settings
from dropbox import DropboxOAuth2FlowNoRedirect


SCOPES = [
    "files.content.read",
    "files.content.write",
    "sharing.read",
    "sharing.write",
]


def main():
    if not settings.dropbox_app_key:
        raise RuntimeError("DROPBOX_APP_KEY is missing.")

    if not settings.dropbox_app_secret:
        raise RuntimeError("DROPBOX_APP_SECRET is missing.")

    flow = DropboxOAuth2FlowNoRedirect(
        consumer_key=settings.dropbox_app_key,
        consumer_secret=settings.dropbox_app_secret,
        token_access_type="offline",
        scope=SCOPES,
    )

    authorize_url = flow.start()

    print()
    print("1. Open this URL in your browser:")
    print()
    print(authorize_url)
    print()
    print("2. Approve MMI's Dropbox access.")
    print("3. Dropbox will give you an authorization code.")
    print()

    code = input("Paste authorization code here: ").strip()

    result = flow.finish(code)

    print()
    print("Dropbox authorization successful.")
    print()
    print("NEW REFRESH TOKEN:")
    print(result.refresh_token)
    print()
    print(
        "Replace DROPBOX_REFRESH_TOKEN in .env "
        "with this value."
    )
    print()


if __name__ == "__main__":
    main()
