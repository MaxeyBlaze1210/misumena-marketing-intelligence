import requests

from app.core.config import settings


def meta_post(
    path: str,
    data: dict,
) -> dict:
    """
    Authenticated Meta Graph API POST helper.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{path.lstrip('/')}"
    )

    headers = {
        "Authorization":
            f"Bearer {settings.meta_access_token}",
    }

    response = requests.post(
        url,
        data=data,
        headers=headers,
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def create_paused_campaign(
    name: str,
    objective: str,
) -> dict:
    """
    Create a Meta campaign in PAUSED state.

    This function cannot start spend because the
    campaign is created paused.
    """

    if not name.strip():
        raise ValueError(
            "Campaign name is required."
        )

    return meta_post(
        (
            f"{settings.meta_ad_account_id}"
            "/campaigns"
        ),
        {
            "name": name,
            "objective": objective,
            "status": "PAUSED",
            "special_ad_categories": "[]",
            "is_adset_budget_sharing_enabled": "false",
        },
    )



def handle_meta_response(response: requests.Response) -> dict:
    if not response.ok:
        try:
            error_details = response.json()
        except ValueError:
            error_details = response.text

        raise RuntimeError(
            f"Meta API error {response.status_code}: {error_details}"
        )

    return response.json()


def get_campaigns():
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{settings.meta_ad_account_id}/campaigns"
    )

    params = {
        "fields": (
            "id,name,status,objective,"
            "daily_budget,lifetime_budget,"
            "start_time,stop_time"
        ),
        "limit": 100,
    }
    
    headers = {
    "Authorization": f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
    )

    return handle_meta_response(response)


def get_campaign_insights(campaign_id: str):
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{campaign_id}/insights"
    )

    params = {
        "fields": (
            "campaign_id,"
            "campaign_name,"
            "spend,"
            "impressions,"
            "reach,"
            "clicks,"
            "ctr,"
            "cpc,"
            "actions,"
            "cost_per_action_type"
        ),
        "date_preset": "maximum",
        "level": "campaign",
    }

    headers = {
    "Authorization": f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
    )

    return handle_meta_response(response)

def get_ads(campaign_id: str):
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{campaign_id}/ads"
    )

    params = {
        "fields": (
            "id,"
            "name,"
            "status,"
            "creative,"
            "adset{id,name}"
        ),
        "limit": 100,
    }

    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
    )

    return handle_meta_response(response)   

def get_ad_insights(campaign_id: str):
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{campaign_id}/insights"
    )

    params = {
        "fields": (
            "ad_id,"
            "ad_name,"
            "adset_id,"
            "adset_name,"
            "campaign_id,"
            "campaign_name,"
            "spend,"
            "impressions,"
            "reach,"
            "clicks,"
            "ctr,"
            "cpc,"
            "actions,"
            "cost_per_action_type"
        ),
        "date_preset": "maximum",
        "time_increment": 1,
        "level": "ad",
        "limit": 100,
    }

    headers = {
    "Authorization": f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
    url,
    params=params,
    headers=headers,
    timeout=30,
    )

    return handle_meta_response(response)


def search_interests(query: str) -> dict:
    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/search"
    )

    params = {
        "type": "adinterest",
        "q": query,
        "limit": 50,
    }

    headers = {
        "Authorization": f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30,
    )

    return handle_meta_response(response)

def get_ad_account_pixels() -> dict:
    """
    Read pixels associated with the configured Meta ad account.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{settings.meta_ad_account_id}/adspixels"
    )

    params = {
        "fields": "id,name,last_fired_time",
        "limit": 100,
    }

    headers = {
        "Authorization":
            f"Bearer {settings.meta_access_token}",
    }

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def create_paused_adset(
    *,
    campaign_id: str,
    name: str,
    daily_budget: float,
    optimization_goal: str,
    pixel_id: str,
    custom_event_type: str,
    targeting: dict,
    start_time: str | None = None,
    end_time: str | None = None,
) -> dict:
    """
    Create one Meta ad set in PAUSED state.

    Budget is supplied in major currency units and converted
    to Meta's minor-unit representation.
    """

    import json

    if daily_budget <= 0:
        raise ValueError(
            "Daily budget must be greater than zero."
        )

    data = {
        "name":
            name,

        "campaign_id":
            campaign_id,

        "daily_budget":
            str(
                int(
                    round(
                        daily_budget * 100
                    )
                )
            ),

        "billing_event":
            "IMPRESSIONS",

        "optimization_goal":
            optimization_goal,

        "bid_strategy":
            "LOWEST_COST_WITHOUT_CAP",

        "promoted_object":
            json.dumps(
                {
                    "pixel_id":
                        pixel_id,

                    "custom_event_type":
                        custom_event_type,

                    "smart_pse_enabled":
                        False,
                }
            ),

        "targeting":
            json.dumps(
                targeting
            ),

        "status":
            "PAUSED",
    }

    if start_time is not None:
        data["start_time"] = start_time

    if end_time is not None:
        data["end_time"] = end_time

    return meta_post(
        (
            f"{settings.meta_ad_account_id}"
            "/adsets"
        ),
        data,
    )


def update_adset_status(
    adset_id: str,
    status: str,
) -> dict:
    """
    Update a Meta ad set's configured status.

    Allowed values are deliberately restricted
    for MMI execution safety.
    """

    status = status.upper()

    if status not in {
        "ACTIVE",
        "PAUSED",
    }:
        raise ValueError(
            "Ad-set status must be ACTIVE or PAUSED."
        )

    return meta_post(
        str(adset_id),
        {
            "status": status,
        },
    )


def update_adset_daily_budget(
    adset_id: str,
    daily_budget_eur: float,
) -> dict:
    """
    Update an ad set's daily budget.

    Meta expects the value in cents.
    """

    if daily_budget_eur <= 0:
        raise ValueError(
            "Daily budget must be greater than zero."
        )

    daily_budget_cents = round(
        daily_budget_eur * 100
    )

    return meta_post(
        str(adset_id),
        {
            "daily_budget":
                str(daily_budget_cents),
        },
    )


def upload_ad_video(
    *,
    file_path: str,
    title: str,
) -> dict:
    """
    Upload one local video file to the configured Meta
    ad account's video library.

    This creates a video asset only.
    It does not create an Ad Creative or Ad.
    """

    if not title.strip():
        raise ValueError(
            "Video title is required."
        )

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{settings.meta_ad_account_id}/advideos"
    )

    headers = {
        "Authorization":
            f"Bearer {settings.meta_access_token}",
    }

    with open(file_path, "rb") as handle:
        response = requests.post(
            url,
            data={
                "title": title,
            },
            files={
                "source": handle,
            },
            headers=headers,
            timeout=120,
        )

    return handle_meta_response(
        response
    )


def get_preferred_ad_video_thumbnail(
    video_id: str,
) -> str:
    """
    Return the preferred Meta-generated thumbnail URL
    for an uploaded ad video.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{video_id}"
    )

    response = requests.get(
        url,
        params={
            "fields": "thumbnails",
        },
        headers={
            "Authorization":
                f"Bearer {settings.meta_access_token}",
        },
        timeout=30,
    )

    data = handle_meta_response(
        response
    )

    thumbnails = (
        data.get("thumbnails", {})
        .get("data", [])
    )

    if not thumbnails:
        raise RuntimeError(
            "Meta video has no thumbnails."
        )

    preferred = next(
        (
            item
            for item in thumbnails
            if item.get("is_preferred")
        ),
        None,
    )

    chosen = (
        preferred
        or thumbnails[0]
    )

    thumbnail_url = chosen.get(
        "uri"
    )

    if not thumbnail_url:
        raise RuntimeError(
            "Meta thumbnail has no URL."
        )

    return thumbnail_url


def get_ad_video(
    video_id: str,
) -> dict:
    """
    Read back one Meta ad video.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{video_id}"
    )

    response = requests.get(
        url,
        params={
            "fields": (
                "id,"
                "title,"
                "created_time,"
                "status"
            ),
        },
        headers={
            "Authorization":
                f"Bearer {settings.meta_access_token}",
        },
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def create_video_ad_creative(
    *,
    name: str,
    page_id: str,
    instagram_user_id: str,
    video_id: str,
    primary_text: str,
    call_to_action: str,
    destination_url: str,
    image_url: str,
) -> dict:
    """
    Create one Meta video Ad Creative.

    This creates a creative object only.
    It does not create or activate an Ad.
    """

    import json

    if not name.strip():
        raise ValueError(
            "Creative name is required."
        )

    if not video_id:
        raise ValueError(
            "Meta video ID is required."
        )

    if not primary_text.strip():
        raise ValueError(
            "Primary text is required."
        )

    object_story_spec = {
        "page_id":
            page_id,

        "instagram_user_id":
            instagram_user_id,

        "video_data": {
            "video_id":
                video_id,

            "message":
                primary_text,

            "image_url":
                image_url,

            "call_to_action": {
                "type":
                    call_to_action,

                "value": {
                    "link":
                        destination_url,
                },
            },
        },
    }

    return meta_post(
        (
            f"{settings.meta_ad_account_id}"
            "/adcreatives"
        ),
        {
            "name":
                name,

            "object_story_spec":
                json.dumps(
                    object_story_spec
                ),
        },
    )


def get_ad_creative(
    creative_id: str,
) -> dict:
    """
    Read one Meta Ad Creative back from Graph API.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{creative_id}"
    )

    response = requests.get(
        url,
        params={
            "fields": (
                "id,"
                "name,"
                "body,"
                "object_story_spec,"
                "call_to_action_type,"
                "video_id"
            ),
        },
        headers={
            "Authorization":
                f"Bearer {settings.meta_access_token}",
        },
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def create_paused_ad(
    *,
    adset_id: str,
    creative_id: str,
    name: str,
) -> dict:
    """
    Create one Meta Ad in PAUSED state.

    The referenced Ad Creative must already exist.
    """

    import json

    if not adset_id:
        raise ValueError(
            "Meta ad-set ID is required."
        )

    if not creative_id:
        raise ValueError(
            "Meta creative ID is required."
        )

    if not name.strip():
        raise ValueError(
            "Ad name is required."
        )

    return meta_post(
        (
            f"{settings.meta_ad_account_id}"
            "/ads"
        ),
        {
            "name":
                name,

            "adset_id":
                str(adset_id),

            "creative":
                json.dumps(
                    {
                        "creative_id":
                            str(creative_id),
                    }
                ),

            "status":
                "PAUSED",
        },
    )


def get_ad(
    ad_id: str,
) -> dict:
    """
    Read back one Meta Ad.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{ad_id}"
    )

    response = requests.get(
        url,
        params={
            "fields": (
                "id,"
                "name,"
                "status,"
                "effective_status,"
                "adset{id,name},"
                "creative{id,name}"
            ),
        },
        headers={
            "Authorization":
                f"Bearer {settings.meta_access_token}",
        },
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def get_campaign(
    campaign_id: str,
) -> dict:
    """
    Read back one Meta campaign.
    """

    url = (
        f"https://graph.facebook.com/"
        f"{settings.meta_api_version}/"
        f"{campaign_id}"
    )

    response = requests.get(
        url,
        params={
            "fields": (
                "id,"
                "name,"
                "status,"
                "effective_status,"
                "objective"
            ),
        },
        headers={
            "Authorization":
                f"Bearer {settings.meta_access_token}",
        },
        timeout=30,
    )

    return handle_meta_response(
        response
    )


def update_campaign_status(
    campaign_id: str,
    status: str,
) -> dict:
    """
    Update a Meta campaign's configured status.

    Deliberately restricted to ACTIVE/PAUSED.
    """

    status = status.upper()

    if status not in {
        "ACTIVE",
        "PAUSED",
    }:
        raise ValueError(
            "Campaign status must be ACTIVE or PAUSED."
        )

    return meta_post(
        str(campaign_id),
        {
            "status": status,
        },
    )


def update_ad_status(
    ad_id: str,
    status: str,
) -> dict:
    """
    Update a Meta Ad's configured status.

    Deliberately restricted to ACTIVE/PAUSED.
    """

    status = status.upper()

    if status not in {
        "ACTIVE",
        "PAUSED",
    }:
        raise ValueError(
            "Ad status must be ACTIVE or PAUSED."
        )

    return meta_post(
        str(ad_id),
        {
            "status": status,
        },
    )
