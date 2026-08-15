META_RULES = {
    # -----------------------------------------------------
    # Exploration
    # -----------------------------------------------------

    # Every audience × creative combination initially runs.
    "exploration_days": 2,

    # A cell should not be judged before it has had at least
    # some opportunity to deliver.
    "min_cell_impressions": 500,

    # Audience-level decisions require substantially more
    # evidence than creative-level decisions.
    "min_audience_impressions": 2000,

    # -----------------------------------------------------
    # Cell pruning
    # -----------------------------------------------------

    # Zero-result cells become pruning candidates only after
    # meaningful spend and/or impressions.
    "zero_result_min_spend": 3.0,

    # Once there is evidence, cells substantially worse than
    # the median can be paused.
    "weak_cell_multiplier": 1.75,

    # Prefer at least this many results before treating CPR
    # as reasonably informative.
    "min_results_for_cpr_judgement": 10,

    # -----------------------------------------------------
    # Audience pruning
    # -----------------------------------------------------

    # Keep audiences unless they are dramatically worse.
    "weak_audience_multiplier": 1.5,

    # Require the audience to be weak on consecutive checks
    # before proposing a pause.
    "weak_audience_checks_required": 2,

    # -----------------------------------------------------
    # Audience budget allocation
    # -----------------------------------------------------

    "min_audience_share": 0.20,

    # Prevent violent day-to-day redistribution.
    "max_audience_share_change": 0.10,

    # -----------------------------------------------------
    # Daily campaign spend curve
    # -----------------------------------------------------

    # Percentage of total campaign budget targeted by day.
    #
    # Days 1-4 deliberately spend aggressively while the
    # experiment has the largest number of active cells.
    "daily_budget_curve": {
        1: 0.20,
        2: 0.16,
        3: 0.115,
        4: 0.075,
        5: 0.055,
        6: 0.045,
        7: 0.040,
        8: 0.035,
        9: 0.030,
        10: 0.0275,
        11: 0.025,
        12: 0.0225,
        13: 0.020,
        14: 0.0175,
    },

    # After the explicit front-loaded period, distribute the
    # remaining budget smoothly across the remaining days.
    "max_campaign_days": 28,

    # -----------------------------------------------------
    # Safety
    # -----------------------------------------------------

    # Meta/platform minimum used as the underlying floor.
    "min_daily_budget_per_active_cell": 1.0,

    # MMI deliberately plans slightly above the hard minimum
    # so capacity is not calculated exactly on the boundary.
    "cell_budget_headroom_pct": 5.0,

    "allow_pause": True,

    # V1 never resumes automatically.
    "allow_resume": False,

    # V1 is advisory only.
    "allow_live_meta_changes": False,

    # -----------------------------------------------------
    # Legacy compatibility
    # -----------------------------------------------------

    # Older recommendation_engine.py still reads these keys.
    # Keep them temporarily until that service is migrated to
    # the new execution/evidence architecture.
    "min_impressions": 2000,
    "weak_multiplier": 1.5,

}
