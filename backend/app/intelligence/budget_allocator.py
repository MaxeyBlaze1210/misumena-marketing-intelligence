from dataclasses import dataclass

from app.intelligence.rules import META_RULES


@dataclass
class AudienceCandidate:
    name: str
    current_share: float
    impressions: int
    results: int
    spend: float
    cost_per_result: float | None
    active: bool = True


class BudgetAllocator:

    def propose(
        self,
        audiences: list[AudienceCandidate],
        total_daily_budget: float,
    ) -> dict:

        if total_daily_budget <= 0:
            raise ValueError(
                "Total daily budget must be greater than zero."
            )

        active = [
            audience
            for audience in audiences
            if audience.active
        ]

        if not active:
            return {
                "total_daily_budget": total_daily_budget,
                "allocations": [],
                "message": "No active audiences.",
            }

        minimum_share = META_RULES[
            "min_audience_share"
        ]

        maximum_share_change = META_RULES[
            "max_audience_share_change"
        ]

        # -------------------------------------------------
        # If CPR evidence is incomplete, stay close to equal
        # allocation rather than inventing a winner.
        # -------------------------------------------------

        evidenced = [
            audience
            for audience in active
            if (
                audience.cost_per_result is not None
                and audience.results > 0
            )
        ]

        if len(evidenced) != len(active):
            target_share = (
                1.0 / len(active)
            )

            raw_shares = {
                audience.name: target_share
                for audience in active
            }

            allocation_reason = (
                "Insufficient CPR evidence across all active "
                "audiences; using equal allocation."
            )

        else:
            weights = {
                audience.name:
                    1.0
                    / audience.cost_per_result

                for audience in active
            }

            total_weight = sum(
                weights.values()
            )

            raw_shares = {
                audience.name:
                    weights[audience.name]
                    / total_weight

                for audience in active
            }

            allocation_reason = (
                "Allocated using inverse CPR while preserving "
                "minimum audience share and limiting day-to-day "
                "share changes."
            )

        # -------------------------------------------------
        # Apply minimum share
        # -------------------------------------------------

        adjusted = {
            audience.name:
                max(
                    raw_shares[audience.name],
                    minimum_share,
                )

            for audience in active
        }

        total_adjusted = sum(
            adjusted.values()
        )

        adjusted = {
            name:
                share / total_adjusted

            for name, share
            in adjusted.items()
        }

        # -------------------------------------------------
        # Limit daily movement from current share
        # -------------------------------------------------

        capped = {}

        for audience in active:

            current_share = (
                audience.current_share
                if audience.current_share > 0
                else 1.0 / len(active)
            )

            lower = max(
                0.0,
                current_share
                - maximum_share_change,
            )

            upper = min(
                1.0,
                current_share
                + maximum_share_change,
            )

            capped[audience.name] = min(
                max(
                    adjusted[audience.name],
                    lower,
                ),
                upper,
            )

        total_capped = sum(
            capped.values()
        )

        final_shares = {
            name:
                share / total_capped

            for name, share
            in capped.items()
        }

        allocations = []

        for audience in active:

            share = final_shares[
                audience.name
            ]

            allocations.append(
                {
                    "audience":
                        audience.name,

                    "share":
                        round(
                            share,
                            4,
                        ),

                    "proposed_daily_budget":
                        round(
                            total_daily_budget
                            * share,
                            2,
                        ),

                    "cost_per_result":
                        (
                            round(
                                audience.cost_per_result,
                                4,
                            )
                            if audience.cost_per_result
                            is not None
                            else None
                        ),

                    "results":
                        audience.results,

                    "impressions":
                        audience.impressions,

                    "reason":
                        allocation_reason,
                }
            )

        return {
            "total_daily_budget":
                round(
                    total_daily_budget,
                    2,
                ),

            "allocations":
                allocations,

            "advisory_only":
                not META_RULES[
                    "allow_live_meta_changes"
                ],
        }
