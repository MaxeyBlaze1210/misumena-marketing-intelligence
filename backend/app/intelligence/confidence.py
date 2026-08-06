def confidence_from_metrics(
    impressions: int,
    results: int,
) -> tuple[float, str]:
    # Impression score
    if impressions < 500:
        impression_score = 0.2
    elif impressions < 2000:
        impression_score = 0.5
    elif impressions < 10000:
        impression_score = 0.8
    else:
        impression_score = 1.0

    # Result score
    if results <= 5:
        result_score = 0.2
    elif results <= 20:
        result_score = 0.5
    elif results <= 100:
        result_score = 0.8
    else:
        result_score = 1.0

    score = round(
        (impression_score + result_score) / 2,
        2,
    )

    if score < 0.4:
        label = "low"
    elif score < 0.7:
        label = "medium"
    else:
        label = "high"

    return score, label