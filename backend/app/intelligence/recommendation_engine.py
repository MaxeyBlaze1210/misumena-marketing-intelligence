from dataclasses import dataclass

from app.intelligence.confidence import confidence_from_metrics
from app.intelligence.rules import META_RULES

@dataclass
class CreativePerformance:
    name: str
    impressions: int
    spend: float
    results: int
    cost_per_result: float | None


class RecommendationEngine:
    MIN_IMPRESSIONS = META_RULES["min_impressions"]
    WEAK_MULTIPLIER = META_RULES["weak_multiplier"]

    def evaluate(
        self,
        creatives: list[CreativePerformance],
    ) -> dict:
        if not creatives:
            return {
                "winner": None,
                "winner_cost_per_result": None,
                "recommendations": [],
            }

        winner = self._find_winner(creatives)

        if winner is None:
            return {
                "winner": None,
                "winner_cost_per_result": None,
                "recommendations": [
                    self._build_no_data_recommendation(creatives)
                ],
            }

        recommendations = [
            self._evaluate_creative(
                creative=creative,
                winner=winner,
            )
            for creative in creatives
        ]

        return {
            "winner": winner.name,
            "winner_cost_per_result": winner.cost_per_result,
            "recommendations": recommendations,
        }

    def _find_winner(
        self,
        creatives: list[CreativePerformance],
    ) -> CreativePerformance | None:
        eligible = [
            creative
            for creative in creatives
            if self._is_eligible(creative)
        ]

        if not eligible:
            return None

        return min(
            eligible,
            key=lambda creative: creative.cost_per_result,
        )

    def _is_eligible(
        self,
        creative: CreativePerformance,
    ) -> bool:
        return (
            creative.impressions >= self.MIN_IMPRESSIONS
            and creative.results > 0
            and creative.cost_per_result is not None
        )

    def _evaluate_creative(
        self,
        creative: CreativePerformance,
        winner: CreativePerformance,
    ) -> dict:
        confidence_score, confidence = confidence_from_metrics(
            impressions=creative.impressions,
            results=creative.results,
        )

        base = {
            "creative": creative.name,
            "confidence": confidence,
            "confidence_score": confidence_score,
        }

        if creative.impressions < self.MIN_IMPRESSIONS:
            return {
                **base,
                "action": "observe",
                "reason": (
                    f"Only {creative.impressions} impressions. "
                    "Insufficient evidence."
                ),
            }

        if creative.results == 0:
            return {
                **base,
                "action": "pause_candidate",
                "reason": (
                    "Sufficient impressions but no results."
                ),
            }

        if creative.cost_per_result is None:
            return {
                **base,
                "action": "review",
                "reason": "Cost per result is unavailable.",
            }

        if creative.name == winner.name:
            return {
                **base,
                "action": "scale_candidate",
                "reason": (
                    "Lowest cost per result among "
                    "sufficiently tested creatives."
                ),
            }

        weak_threshold = (
            winner.cost_per_result * self.WEAK_MULTIPLIER
        )

        if creative.cost_per_result >= weak_threshold:
            return {
                **base,
                "action": "pause_candidate",
                "reason": (
                    "Cost per result is at least 50% above "
                    f"the winner at €{winner.cost_per_result:.2f}."
                ),
            }

        return {
            **base,
            "action": "keep",
            "reason": (
                "Performance is within 50% of the winner."
            ),
        }

    def _build_no_data_recommendation(
        self,
        creatives: list[CreativePerformance],
    ) -> dict:
        highest_impressions = max(
            creative.impressions
            for creative in creatives
        )

        return {
            "action": "observe",
            "confidence": "low",
            "confidence_score": 0.2,
            "reason": (
                "No creative has enough data yet. "
                f"The highest impression count is "
                f"{highest_impressions}."
            ),
        }