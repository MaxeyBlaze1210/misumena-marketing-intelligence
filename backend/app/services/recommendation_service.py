def evaluate_creative(creative):
    recommendations = []

    if creative.results == 0 and creative.spend > 20:
        recommendations.append(
            "Pause this creative."
        )

    if creative.cost_per_result < 0.25:
        recommendations.append(
            "Increase budget."
        )

    return recommendations