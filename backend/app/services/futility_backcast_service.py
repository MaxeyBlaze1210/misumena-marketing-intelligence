import re
from datetime import timedelta

from app.models.meta_ad import MetaAd
from app.models.meta_ad_metric import MetaAdMetric
from app.models.meta_campaign import MetaCampaign


def _creative_name(ad_name: str) -> str:
    match = re.search(
        r"Creative\s+(\d+)",
        ad_name or "",
        flags=re.IGNORECASE,
    )

    if match:
        return f"Creative {match.group(1)}"

    return ad_name


def _arm_name(campaign_name: str) -> str:
    name = campaign_name or ""

    if "African popular music" in name:
        return "African popular music"

    if "Afrobeat" in name:
        return "Afrobeat"

    if "Broad" in name:
        return "Broad"

    return name


def build_day2_futility_backcast(
    db,
    release_id: int,
):
    """
    Retrospective Day-2 evidence freeze.

    This deliberately does NOT classify cells as futile.
    It reconstructs what was knowable at Day 2 and compares
    that evidence with what happened afterwards.
    """

    rows = (
        db.query(
            MetaCampaign,
            MetaAd,
            MetaAdMetric,
        )
        .join(
            MetaAd,
            MetaAd.campaign_id
            == MetaCampaign.id,
        )
        .join(
            MetaAdMetric,
            MetaAdMetric.ad_id
            == MetaAd.id,
        )
        .filter(
            MetaCampaign.release_id
            == release_id
        )
        .filter(
            MetaCampaign.name.like(
                "%intellijend%"
            )
        )
        .order_by(
            MetaAdMetric.date_start,
            MetaCampaign.id,
            MetaAd.id,
        )
        .all()
    )

    if not rows:
        return None

    dates = sorted(
        {
            metric.date_start
            for _, _, metric in rows
        }
    )

    if len(dates) < 2:
        return None

    day2_date = dates[1]

    cells = {}

    for campaign, ad, metric in rows:

        key = (
            campaign.id,
            ad.id,
        )

        cell = cells.setdefault(
            key,
            {
                "arm":
                    _arm_name(
                        campaign.name
                    ),

                "creative":
                    _creative_name(
                        ad.name
                    ),

                "day2_spend": 0.0,
                "day2_results": 0,
                "day2_impressions": 0,
                "day2_likes": 0,

                "post_spend": 0.0,
                "post_results": 0,
            },
        )

        if metric.date_start <= day2_date:

            cell["day2_spend"] += (
                metric.spend or 0
            )

            cell["day2_results"] += (
                metric.results or 0
            )

            cell["day2_impressions"] += (
                metric.impressions or 0
            )

            cell["day2_likes"] += (
                metric.post_likes or 0
            )

        else:

            cell["post_spend"] += (
                metric.spend or 0
            )

            cell["post_results"] += (
                metric.results or 0
            )

    for cell in cells.values():

        cell["day2_cpr"] = (
            cell["day2_spend"]
            / cell["day2_results"]
            if cell["day2_results"] > 0
            else None
        )

        cell["day2_like_rate"] = (
            (
                cell["day2_likes"]
                / cell["day2_impressions"]
            )
            * 100
            if cell["day2_impressions"] > 0
            else None
        )

        cell["post_cpr"] = (
            cell["post_spend"]
            / cell["post_results"]
            if cell["post_results"] > 0
            else None
        )

    arm_order = {
        "Broad": 0,
        "Afrobeat": 1,
        "African popular music": 2,
    }

    def sort_key(cell):
        match = re.search(
            r"(\d+)",
            cell["creative"],
        )

        number = (
            int(match.group(1))
            if match
            else 999
        )

        return (
            arm_order.get(
                cell["arm"],
                100,
            ),
            number,
        )

    cell_list = sorted(
        cells.values(),
        key=sort_key,
    )

    # Interesting validation case:
    # zero Day-2 results followed by meaningful later
    # conversion. This is exactly the type of false
    # futility signal we want MMI to learn from.
    rescued_cells = [
        cell
        for cell in cell_list
        if (
            cell["day2_results"] == 0
            and cell["post_results"] > 0
        )
    ]

    total_day2_spend = sum(
        cell["day2_spend"]
        for cell in cell_list
    )

    total_day2_results = sum(
        cell["day2_results"]
        for cell in cell_list
    )

    total_post_spend = sum(
        cell["post_spend"]
        for cell in cell_list
    )

    total_post_results = sum(
        cell["post_results"]
        for cell in cell_list
    )

    return {
        "checkpoint_date":
            day2_date,

        "cell_count":
            len(cell_list),

        "cells":
            cell_list,

        "rescued_cells":
            rescued_cells,

        "day2_spend":
            total_day2_spend,

        "day2_results":
            total_day2_results,

        "post_spend":
            total_post_spend,

        "post_results":
            total_post_results,

        "post_cpr":
            (
                total_post_spend
                / total_post_results
                if total_post_results > 0
                else None
            ),
    }
