from dataclasses import dataclass

from app.intelligence.rules import META_RULES


@dataclass
class BudgetCandidate:
    name: str
    current_daily_budget: float
    impressions: int
    results: int
    cost_per_result: float | None
    action: str


class BudgetAllocator:
    def propose(
        self,
        candidates: list[BudgetCandidate],
        total_daily_budget: float,
    ) -> dict:
        if total_daily_budget <= 0:
            raise ValueError("Total daily budget must be greater than zero.")

        active = [
            candidate
            for candidate in candidates
            if candidate.action != "pause_candidate"
            and candidate.cost_per_result is not None
            and candidate.results > 0
        ]

        if not active:
            return {
                "total_daily_budget": total_daily_budget,
                "allocations": [],
                "message": "No eligible creatives for budget allocation.",
            }

        minimum_budget = META_RULES["min_daily_budget_per_adset"]
        maximum_increase_pct = META_RULES[
            "max_daily_budget_increase_pct"
        ]

        required_minimum = minimum_budget * len(active)

        if required_minimum > total_daily_budget:
            return {
                "total_daily_budget": total_daily_budget,
                "allocations": [],
                "message": (
                    "The total daily budget is too low to keep all "
                    "eligible creatives active at the minimum budget."
                ),
            }

        performance_pool = total_daily_budget - required_minimum

        weights = {
            candidate.name: 1 / candidate.cost_per_result
            for candidate in active
        }

        total_weight = sum(weights.values())

        allocations = []

        for candidate in active:
            weighted_share = (
                weights[candidate.name] / total_weight
            )

            proposed_budget = (
                minimum_budget
                + performance_pool * weighted_share
            )

            maximum_allowed = (
                candidate.current_daily_budget
                * (1 + maximum_increase_pct / 100)
            )

            proposed_budget = min(
                proposed_budget,
                maximum_allowed,
            )

            allocations.append(
                {
                    "creative": candidate.name,
                    "current_daily_budget": round(
                        candidate.current_daily_budget,
                        2,
                    ),
                    "proposed_daily_budget": round(
                        proposed_budget,
                        2,
                    ),
                    "cost_per_result": round(
                        candidate.cost_per_result,
                        4,
                    ),
                    "reason": (
                        "Allocated according to inverse cost per result, "
                        "subject to minimum-budget and maximum-increase rules."
                    ),
                }
            )

        allocated_total = sum(
            item["proposed_daily_budget"]
            for item in allocations
        )

        return {
            "total_daily_budget": total_daily_budget,
            "proposed_total": round(allocated_total, 2),
            "unallocated_budget": round(
                total_daily_budget - allocated_total,
                2,
            ),
            "allocations": allocations,
            "advisory_only": not META_RULES["allow_budget_changes"],
        }