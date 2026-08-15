import json
import os
from datetime import datetime, timezone
from decimal import Decimal

import httpx

import app.database.init_db  # noqa: F401

from app.database.database import SessionLocal
from app.models.meta_adset import MetaAdSet
from app.models.meta_adset_metric import MetaAdSetMetric
from app.models.meta_adset_targeting_item import (
    MetaAdSetTargetingItem,
)


GRAPH_API_VERSION = "v25.0"

ACCESS_TOKEN = os.environ.get(
    "META_ACCESS_TOKEN"
)

AD_ACCOUNT_ID = os.environ.get(
    "META_AD_ACCOUNT_ID"
)


RESULT_PRIORITY = [
    "offsite_conversion.fb_pixel_view_content",
    "landing_page_view",
    "link_click",
]


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
) -> dict:
    if params is None:
        params = {}

    safe_params = dict(params)

    params = dict(params)
    params["access_token"] = ACCESS_TOKEN

    url = (
        "https://graph.facebook.com/"
        f"{GRAPH_API_VERSION}/{path}"
    )

    response = httpx.get(
        url,
        params=params,
        timeout=30.0,
    )

    if response.status_code != 200:
        print()
        print(
            f"META API ERROR "
            f"{response.status_code}"
        )

        # Important:
        # never print response.request.url because
        # it contains the access token.

        print(
            response.text
        )

    response.raise_for_status()

    return response.json()


def parse_meta_datetime(
    value: str | None,
):
    if not value:
        return None

    return datetime.strptime(
        value,
        "%Y-%m-%dT%H:%M:%S%z",
    )


def money_value(
    value,
):
    if value in (
        None,
        "",
    ):
        return None

    return Decimal(
        str(value)
    ) / Decimal("100")


def list_all_adsets() -> list[dict]:
    account = AD_ACCOUNT_ID

    if not account.startswith(
        "act_"
    ):
        account = (
            f"act_{account}"
        )

    fields = ",".join(
        [
            "id",
            "name",
            "status",
            "effective_status",
            "campaign_id",
            "created_time",
            "start_time",
            "end_time",
            "daily_budget",
            "lifetime_budget",
            "optimization_goal",
            "billing_event",
            "targeting",
        ]
    )

    all_adsets = []

    after = None

    while True:
        params = {
            "fields": fields,
            "limit": 100,
        }

        if after:
            params["after"] = after

        result = graph_get(
            f"{account}/adsets",
            params,
        )

        all_adsets.extend(
            result.get(
                "data",
                [],
            )
        )

        paging = result.get(
            "paging",
            {},
        )

        cursors = paging.get(
            "cursors",
            {},
        )

        next_after = cursors.get(
            "after"
        )

        if (
            not paging.get("next")
            or not next_after
        ):
            break

        after = next_after

    return all_adsets


def get_adset_insights(
    meta_adset_id: str,
) -> dict | None:
    result = graph_get(
        f"{meta_adset_id}/insights",
        {
            "fields": ",".join(
                [
                    "date_start",
                    "date_stop",
                    "spend",
                    "impressions",
                    "reach",
                    "actions",
                    "cost_per_action_type",
                ]
            ),
            "date_preset": "maximum",
        },
    )

    rows = result.get(
        "data",
        [],
    )

    if not rows:
        return None

    return rows[0]


def get_action_value(
    actions: list[dict] | None,
    action_type: str,
):
    for action in (
        actions or []
    ):
        if (
            action.get(
                "action_type"
            )
            == action_type
        ):
            try:
                return float(
                    action.get(
                        "value",
                        0,
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

    return None


def choose_result(
    insight: dict,
) -> tuple[
    str | None,
    float | None,
    float | None,
]:
    actions = insight.get(
        "actions",
        [],
    )

    costs = insight.get(
        "cost_per_action_type",
        [],
    )

    for result_type in RESULT_PRIORITY:
        results = get_action_value(
            actions,
            result_type,
        )

        if results is None:
            continue

        cpr = get_action_value(
            costs,
            result_type,
        )

        return (
            result_type,
            results,
            cpr,
        )

    return (
        None,
        None,
        None,
    )


def sync_targeting_items(
    db,
    adset: MetaAdSet,
    targeting: dict,
):
    for item in list(
        adset.targeting_items
    ):
        db.delete(item)

    db.flush()

    flexible_specs = targeting.get(
        "flexible_spec",
        [],
    )

    for spec in flexible_specs:

        mappings = {
            "interests":
                "interest",

            "work_employers":
                "work_employer",

            "work_positions":
                "work_position",
        }

        for source_key, item_type in (
            mappings.items()
        ):
            for item in spec.get(
                source_key,
                [],
            ):
                db.add(
                    MetaAdSetTargetingItem(
                        meta_adset_id=adset.id,
                        item_type=item_type,
                        meta_item_id=str(
                            item.get("id")
                        )
                        if item.get("id")
                        else None,
                        name=item.get(
                            "name",
                            "",
                        ),
                    )
                )


def sync_metric(
    db,
    adset: MetaAdSet,
    insight: dict | None,
):
    if insight is None:
        return

    date_start = datetime.strptime(
        insight["date_start"],
        "%Y-%m-%d",
    ).date()

    date_stop = datetime.strptime(
        insight["date_stop"],
        "%Y-%m-%d",
    ).date()

    metric = (
        db.query(
            MetaAdSetMetric
        )
        .filter(
            MetaAdSetMetric.adset_id
            == adset.id,

            MetaAdSetMetric.date_start
            == date_start,

            MetaAdSetMetric.date_stop
            == date_stop,
        )
        .one_or_none()
    )

    if metric is None:
        metric = MetaAdSetMetric(
            adset_id=adset.id,
            date_start=date_start,
            date_stop=date_stop,
        )

        db.add(metric)

    (
        result_type,
        results,
        cost_per_result,
    ) = choose_result(
        insight
    )

    metric.spend = float(
        insight.get(
            "spend",
            0,
        )
    )

    metric.impressions = int(
        insight.get(
            "impressions",
            0,
        )
    )

    metric.reach = int(
        insight.get(
            "reach",
            0,
        )
    )

    metric.result_type = (
        result_type
    )

    metric.results = results

    if cost_per_result is not None:
        metric.cost_per_result = cost_per_result
    elif (
        results is not None
        and results > 0
    ):
        metric.cost_per_result = (
            metric.spend / results
        )
    else:
        metric.cost_per_result = None

    metric.raw_insights_json = (
        json.dumps(
            insight,
            ensure_ascii=False,
        )
    )


def sync_adset(
    db,
    source: dict,
):
    meta_adset_id = str(
        source["id"]
    )

    adset = (
        db.query(MetaAdSet)
        .filter(
            MetaAdSet.meta_adset_id
            == meta_adset_id
        )
        .one_or_none()
    )

    if adset is None:
        adset = MetaAdSet(
            meta_adset_id=(
                meta_adset_id
            ),
            name=source.get(
                "name",
                "",
            ),
        )

        db.add(adset)

        db.flush()

    targeting = source.get(
        "targeting",
        {},
    )

    geo_locations = targeting.get(
        "geo_locations",
        {},
    )

    countries = geo_locations.get(
        "countries",
        [],
    )

    targeting_automation = (
        targeting.get(
            "targeting_automation",
            {},
        )
    )

    advantage_value = (
        targeting_automation.get(
            "advantage_audience"
        )
    )

    adset.meta_campaign_id = (
        str(
            source.get(
                "campaign_id"
            )
        )
        if source.get(
            "campaign_id"
        )
        else None
    )

    adset.name = source.get(
        "name",
        "",
    )

    adset.status = source.get(
        "status"
    )

    adset.effective_status = (
        source.get(
            "effective_status"
        )
    )

    adset.created_time = (
        parse_meta_datetime(
            source.get(
                "created_time"
            )
        )
    )

    adset.start_time = (
        parse_meta_datetime(
            source.get(
                "start_time"
            )
        )
    )

    adset.end_time = (
        parse_meta_datetime(
            source.get(
                "end_time"
            )
        )
    )

    adset.daily_budget = (
        money_value(
            source.get(
                "daily_budget"
            )
        )
    )

    adset.lifetime_budget = (
        money_value(
            source.get(
                "lifetime_budget"
            )
        )
    )

    adset.optimization_goal = (
        source.get(
            "optimization_goal"
        )
    )

    adset.billing_event = (
        source.get(
            "billing_event"
        )
    )

    adset.age_min = targeting.get(
        "age_min"
    )

    adset.age_max = targeting.get(
        "age_max"
    )

    if advantage_value is None:
        adset.advantage_audience = (
            None
        )
    else:
        adset.advantage_audience = (
            bool(
                int(
                    advantage_value
                )
            )
        )

    adset.countries_json = (
        json.dumps(
            countries,
            ensure_ascii=False,
        )
    )

    adset.targeting_json = (
        json.dumps(
            targeting,
            ensure_ascii=False,
        )
    )

    adset.last_imported_at = (
        datetime.now(
            timezone.utc
        )
    )

    sync_targeting_items(
        db,
        adset,
        targeting,
    )

    insight = get_adset_insights(
        meta_adset_id
    )

    sync_metric(
        db,
        adset,
        insight,
    )

    return (
        adset,
        insight,
    )


def main():
    require_config()

    db = SessionLocal()

    try:
        adsets = list_all_adsets()

        print()
        print("=" * 90)
        print(
            "META HISTORICAL IMPORT"
        )
        print("=" * 90)
        print()

        print(
            f"{len(adsets)} ad sets found."
        )
        print()

        for index, source in enumerate(
            adsets,
            start=1,
        ):
            print(
                f"[{index}/{len(adsets)}] "
                f"{source.get('name')}"
            )

            adset, insight = (
                sync_adset(
                    db,
                    source,
                )
            )

            db.commit()

            interest_count = sum(
                1
                for item
                in adset.targeting_items
                if item.item_type
                == "interest"
            )

            metric = (
                adset.metrics[0]
                if adset.metrics
                else None
            )

            if metric:
                print(
                    "      "
                    f"€{metric.spend:.2f} "
                    f"| results "
                    f"{metric.results} "
                    f"| CPR "
                    f"{metric.cost_per_result}"
                    f" | interests "
                    f"{interest_count}"
                )
            else:
                print(
                    "      "
                    "No historical insights "
                    f"| interests "
                    f"{interest_count}"
                )

        print()
        print("=" * 90)
        print("IMPORT COMPLETE")
        print("=" * 90)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
