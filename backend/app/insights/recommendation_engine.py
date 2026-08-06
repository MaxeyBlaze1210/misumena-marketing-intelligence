class RecommendationEngine:
    MIN_IMPRESSIONS = 2000
    WEAK_MULTIPLIER = 1.5

    def evaluate_creatives(self, creatives):
        if not creatives:
            return {
                "best_creative": None,
                "recommendations": [],
            }

        eligible = [
            creative
            for creative in creatives
            if creative.impressions is not None
            and creative.impressions >= self.MIN_IMPRESSIONS
            and creative.cost_per_result is not None
        ]

        if not eligible:
            return {
                "best_creative": None,
                "recommendations": [
                    {
                        "action": "wait",
                        "reason": (
                            "No creative has reached "
                            f"{self.MIN_IMPRESSIONS} impressions yet."
                        ),
                    }
                ],
            }

        best = min(
            eligible,
            key=lambda creative: creative.cost_per_result,
        )

        weak_threshold = (
            best.cost_per_result * self.WEAK_MULTIPLIER
        )

        recommendations = []

        for creative in creatives:
            if (
                creative.impressions is None
                or creative.impressions < self.MIN_IMPRESSIONS
            ):
                recommendations.append(
                    {
                        "creative": creative.creative_name,
                        "action": "wait",
                        "reason": (
                            f"Only {creative.impressions or 0} impressions. "
                            "Not enough evidence yet."
                        ),
                    }
                )
                continue

            if creative.results == 0:
                recommendations.append(
                    {
                        "creative": creative.creative_name,
                        "action": "pause_candidate",
                        "reason": (
                            "The creative has reached the minimum "
                            "impression threshold but has no results."
                        ),
                    }
                )
                continue

            if (
                creative.cost_per_result is not None
                and creative.cost_per_result >= weak_threshold
            ):
                recommendations.append(
                    {
                        "creative": creative.creative_name,
                        "action": "pause_candidate",
                        "reason": (
                            f"Cost per result is "
                            f"{creative.cost_per_result:.2f}, "
                            f"at least 50% above the best creative "
                            f"at {best.cost_per_result:.2f}."
                        ),
                    }
                )
                continue

            if creative.id == best.id:
                recommendations.append(
                    {
                        "creative": creative.creative_name,
                        "action": "scale_candidate",
                        "reason": (
                            "Lowest cost per result among creatives "
                            "with sufficient impressions."
                        ),
                    }
                )
                continue

            recommendations.append(
                {
                    "creative": creative.creative_name,
                    "action": "keep",
                    "reason": (
                        "Performance is within 50% of the best creative."
                    ),
                }
            )

        return {
            "best_creative": best.creative_name,
            "best_cost_per_result": best.cost_per_result,
            "recommendations": recommendations,
        }