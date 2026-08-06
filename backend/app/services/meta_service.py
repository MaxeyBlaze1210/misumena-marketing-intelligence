import requests

from app.core.config import settings


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