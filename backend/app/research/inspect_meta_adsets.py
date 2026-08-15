import json
import os
import sys

import httpx


GRAPH_API_VERSION = "v25.0"

ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
AD_ACCOUNT_ID = os.environ.get("META_AD_ACCOUNT_ID")


def require_config():
    if not ACCESS_TOKEN:
        raise RuntimeError(
            "META_ACCESS_TOKEN is not configured."
        )

    if not AD_ACCOUNT_ID:
        raise RuntimeError(
            "META_AD_ACCOUNT_ID is not configured."
        )


def graph_get(
    path: str,
    params: dict | None = None,
):
    if params is None:
        params = {}

    params = dict(params)
    params["access_token"] = ACCESS_TOKEN

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/{path}"
    )

    response = httpx.get(
        url,
        params=params,
        timeout=30.0,
    )

    if response.status_code != 200:
        print()
        print("META API ERROR")
        print("=" * 72)
        print("Status:", response.status_code)
        print(response.text)
        print()

    response.raise_for_status()

    return response.json()


def list_adsets():
    account = AD_ACCOUNT_ID

    if not account.startswith("act_"):
        account = f"act_{account}"

    result = graph_get(
        f"{account}/adsets",
        {
            "fields": ",".join(
                [
                    "id",
                    "name",
                    "status",
                    "effective_status",
                    "campaign_id",
                    "created_time",
                    "start_time",
                    "end_time",
                ]
            ),
            "limit": 100,
        },
    )

    adsets = result.get(
        "data",
        [],
    )

    print()
    print("=" * 100)
    print("META AD SETS")
    print("=" * 100)
    print()

    for adset in adsets:
        print(
            adset.get("id"),
            "|",
            adset.get("effective_status"),
            "|",
            adset.get("name"),
        )

    print()
    print(
        f"{len(adsets)} ad sets returned."
    )
    print()

    return adsets


def inspect_adset(
    adset_id: str,
):
    result = graph_get(
        adset_id,
        {
            "fields": ",".join(
                [
                    "id",
                    "name",
                    "campaign_id",
                    "status",
                    "effective_status",
                    "created_time",
                    "start_time",
                    "end_time",
                    "daily_budget",
                    "lifetime_budget",
                    "optimization_goal",
                    "billing_event",
                    "targeting",
                ]
            ),
        },
    )

    print()
    print("=" * 100)
    print("AD SET DETAIL")
    print("=" * 100)
    print()

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


def main():
    require_config()

    if len(sys.argv) == 1:
        list_adsets()
        return

    if len(sys.argv) == 2:
        inspect_adset(
            sys.argv[1]
        )
        return

    print(
        "Usage:\n"
        "\n"
        "List ad sets:\n"
        "  python -m app.research.inspect_meta_adsets\n"
        "\n"
        "Inspect one ad set:\n"
        "  python -m app.research.inspect_meta_adsets <ADSET_ID>"
    )

    raise SystemExit(1)


if __name__ == "__main__":
    main()
