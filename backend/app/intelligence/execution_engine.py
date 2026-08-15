from dataclasses import dataclass
from statistics import median

from app.intelligence.budget_allocator import (
    AudienceCandidate,
    BudgetAllocator,
)
from app.intelligence.rules import META_RULES


@dataclass
class CampaignCell:
    audience: str
    creative: str
    impressions: int
    spend: float
    results: int
    cost_per_result: float | None
    active: bool = True
    days_active: int = 0

    # Optional production identity.
    #
    # Research/benchmark cells may leave these unset.
    cell_id: int | None = None
    meta_adset_id: str | None = None


class ExecutionEngine:

    # ---------------------------------------------------------
    # Daily campaign budget
    # ---------------------------------------------------------

    def daily_budget_target(
        self,
        total_budget: float,
        day: int,
        spent_so_far: float = 0.0,
    ) -> float:

        if total_budget <= 0:
            raise ValueError(
                "Total campaign budget must be greater than zero."
            )

        remaining_budget = max(
            0.0,
            total_budget - spent_so_far,
        )

        if remaining_budget <= 0:
            return 0.0

        curve = META_RULES["daily_budget_curve"]

        if day in curve:
            target = total_budget * curve[day]

            return round(
                min(
                    target,
                    remaining_budget,
                ),
                2,
            )

        max_days = META_RULES["max_campaign_days"]

        if day > max_days:
            return 0.0

        explicit_curve_total = sum(
            curve.values()
        )

        remaining_curve_share = max(
            0.0,
            1.0 - explicit_curve_total,
        )

        tail_days = (
            max_days
            - max(curve)
        )

        if tail_days <= 0:
            return round(
                remaining_budget,
                2,
            )

        nominal_tail_target = (
            total_budget
            * remaining_curve_share
            / tail_days
        )

        return round(
            min(
                nominal_tail_target,
                remaining_budget,
            ),
            2,
        )

    # ---------------------------------------------------------
    # Creative-level evidence
    #
    # Same creative pooled across all audiences.
    # ---------------------------------------------------------

    def build_creative_aggregates(
        self,
        cells: list[CampaignCell],
    ) -> dict[str, dict]:

        aggregates = {}

        creative_names = sorted(
            {
                cell.creative
                for cell in cells
            }
        )

        for creative in creative_names:

            creative_cells = [
                cell
                for cell in cells
                if cell.creative == creative
            ]

            spend = sum(
                cell.spend
                for cell in creative_cells
            )

            results = sum(
                cell.results
                for cell in creative_cells
            )

            impressions = sum(
                cell.impressions
                for cell in creative_cells
            )

            if results > 0:
                cpr = spend / results
            else:
                cpr = None

            aggregates[creative] = {
                "creative": creative,
                "spend": spend,
                "results": results,
                "impressions": impressions,
                "cost_per_result": cpr,
                "audience_count": len(
                    {
                        cell.audience
                        for cell in creative_cells
                    }
                ),
            }

        return aggregates

    def get_best_creative(
        self,
        creative_aggregates: dict[str, dict],
    ) -> dict | None:

        minimum_results = META_RULES[
            "min_results_for_cpr_judgement"
        ]

        eligible = [
            aggregate
            for aggregate
            in creative_aggregates.values()
            if (
                aggregate["cost_per_result"]
                is not None
                and aggregate["results"]
                >= minimum_results
            )
        ]

        if not eligible:
            return None

        return min(
            eligible,
            key=lambda aggregate:
                aggregate["cost_per_result"],
        )

    # ---------------------------------------------------------
    # Audience replication
    #
    # Does the same creative lose to the best creative
    # repeatedly across different audiences?
    # ---------------------------------------------------------

    def build_replication_summary(
        self,
        *,
        creative: str,
        best_creative: str | None,
        cells: list[CampaignCell],
    ) -> dict:

        if (
            best_creative is None
            or creative == best_creative
        ):
            return {
                "comparisons": 0,
                "worse_count": 0,
                "worse_fraction": 0.0,
            }

        creative_cells = {
            cell.audience: cell
            for cell in cells
            if cell.creative == creative
        }

        best_cells = {
            cell.audience: cell
            for cell in cells
            if cell.creative == best_creative
        }

        comparisons = 0
        worse_count = 0

        for audience, cell in (
            creative_cells.items()
        ):

            best_cell = best_cells.get(
                audience
            )

            if best_cell is None:
                continue

            if (
                cell.cost_per_result is None
                or best_cell.cost_per_result is None
            ):
                continue

            if (
                cell.results <= 0
                or best_cell.results <= 0
            ):
                continue

            comparisons += 1

            if (
                cell.cost_per_result
                > best_cell.cost_per_result
            ):
                worse_count += 1

        if comparisons > 0:
            worse_fraction = (
                worse_count
                / comparisons
            )
        else:
            worse_fraction = 0.0

        return {
            "comparisons": comparisons,
            "worse_count": worse_count,
            "worse_fraction": worse_fraction,
        }

    # ---------------------------------------------------------
    # Cell-level evidence
    #
    # One audience × one creative.
    # ---------------------------------------------------------

    def build_cell_evidence_profile(
        self,
        *,
        cell: CampaignCell,
        comparable_cprs: list[float],
        creative_aggregate: dict,
        best_creative: dict | None,
        replication: dict,
    ) -> dict:
        """
        Describe the evidence for one audience × creative cell.

        This method does not decide whether the cell should run
        or pause. It only describes the evidence available to
        the execution layer.
        """

        minimum_results = META_RULES[
            "min_results_for_cpr_judgement"
        ]

        minimum_impressions = META_RULES[
            "min_cell_impressions"
        ]

        reference_cpr = (
            median(comparable_cprs)
            if comparable_cprs
            else None
        )

        cell_cpr_ratio = None

        if (
            cell.cost_per_result is not None
            and reference_cpr is not None
            and reference_cpr > 0
        ):
            cell_cpr_ratio = (
                cell.cost_per_result
                / reference_cpr
            )

        if (
            cell.results >= minimum_results
            and cell.cost_per_result is not None
        ):
            cell_evidence = "sufficient"

        elif (
            cell.impressions >= minimum_impressions
            or cell.results > 0
        ):
            cell_evidence = "limited"

        else:
            cell_evidence = "minimal"

        aggregate_cpr = creative_aggregate[
            "cost_per_result"
        ]

        best_cpr = (
            best_creative["cost_per_result"]
            if best_creative is not None
            else None
        )

        creative_cpr_ratio = None

        if (
            aggregate_cpr is not None
            and best_cpr is not None
            and best_cpr > 0
        ):
            creative_cpr_ratio = (
                aggregate_cpr
                / best_cpr
            )

        if (
            creative_aggregate["results"]
            >= minimum_results
            and creative_cpr_ratio is not None
        ):
            creative_evidence = "sufficient"
        else:
            creative_evidence = "limited"

        comparisons = replication[
            "comparisons"
        ]

        worse_fraction = replication[
            "worse_fraction"
        ]

        if comparisons >= 3:
            replication_evidence = "strong"
        elif comparisons >= 2:
            replication_evidence = "moderate"
        elif comparisons == 1:
            replication_evidence = "limited"
        else:
            replication_evidence = "none"

        zero_result_pressure = False

        if cell.results == 0:
            zero_result_pressure = (
                cell.impressions
                >= minimum_impressions
                or cell.spend
                >= META_RULES[
                    "zero_result_min_spend"
                ]
            )

        return {
            "cell": {
                "evidence":
                    cell_evidence,

                "cpr":
                    cell.cost_per_result,

                "reference_cpr":
                    reference_cpr,

                "cpr_ratio":
                    cell_cpr_ratio,

                "results":
                    cell.results,

                "impressions":
                    cell.impressions,

                "spend":
                    cell.spend,

                "zero_result_pressure":
                    zero_result_pressure,
            },

            "creative": {
                "evidence":
                    creative_evidence,

                "cpr":
                    aggregate_cpr,

                "best_cpr":
                    best_cpr,

                "cpr_ratio":
                    creative_cpr_ratio,

                "results":
                    creative_aggregate[
                        "results"
                    ],
            },

            "replication": {
                "evidence":
                    replication_evidence,

                "comparisons":
                    comparisons,

                "worse_count":
                    replication[
                        "worse_count"
                    ],

                "worse_fraction":
                    worse_fraction,
            },
        }


    def calculate_pruning_priority(
        self,
        evidence_profile: dict,
    ) -> dict:
        """
        Produce a continuous evidence-based pruning score.

        Higher score = more expendable.

        This score is advisory only. It does not itself
        pause or keep a cell.
        """

        cell = evidence_profile["cell"]
        creative = evidence_profile["creative"]
        replication = evidence_profile[
            "replication"
        ]

        score = 0.0
        components = {}

        # -------------------------------------------------
        # 1. Cell-level relative CPR
        # Maximum contribution: 35 points.
        #
        # Low-evidence cells are deliberately discounted.
        # -------------------------------------------------

        cell_evidence_weights = {
            "minimal": 0.20,
            "limited": 0.55,
            "sufficient": 1.00,
        }

        cell_ratio = cell["cpr_ratio"]

        cell_component = 0.0

        if (
            cell_ratio is not None
            and cell_ratio > 1.0
        ):
            normalized = min(
                (cell_ratio - 1.0) / 2.0,
                1.0,
            )

            cell_component = (
                35.0
                * normalized
                * cell_evidence_weights.get(
                    cell["evidence"],
                    0.0,
                )
            )

        score += cell_component

        components["cell_performance"] = round(
            cell_component,
            2,
        )

        # -------------------------------------------------
        # 2. Creative-wide relative CPR
        # Maximum contribution: 30 points.
        # -------------------------------------------------

        creative_evidence_weights = {
            "limited": 0.40,
            "sufficient": 1.00,
        }

        creative_ratio = creative[
            "cpr_ratio"
        ]

        creative_component = 0.0

        if (
            creative_ratio is not None
            and creative_ratio > 1.0
        ):
            normalized = min(
                (creative_ratio - 1.0) / 2.0,
                1.0,
            )

            creative_component = (
                30.0
                * normalized
                * creative_evidence_weights.get(
                    creative["evidence"],
                    0.0,
                )
            )

        score += creative_component

        components[
            "creative_performance"
        ] = round(
            creative_component,
            2,
        )

        # -------------------------------------------------
        # 3. Replication across audiences
        # Maximum contribution: 20 points.
        # -------------------------------------------------

        replication_weights = {
            "none": 0.0,
            "limited": 0.40,
            "moderate": 0.75,
            "strong": 1.00,
        }

        replication_component = (
            20.0
            * replication["worse_fraction"]
            * replication_weights.get(
                replication["evidence"],
                0.0,
            )
        )

        score += replication_component

        components["replication"] = round(
            replication_component,
            2,
        )

        # -------------------------------------------------
        # 4. Meaningful delivery with zero results
        # Maximum contribution: 15 points.
        # -------------------------------------------------

        zero_result_component = (
            15.0
            if cell["zero_result_pressure"]
            else 0.0
        )

        score += zero_result_component

        components["zero_results"] = (
            zero_result_component
        )

        score = round(
            min(score, 100.0),
            2,
        )

        if score < 20:
            label = "strong"
        elif score < 40:
            label = "acceptable"
        elif score < 60:
            label = "watch"
        elif score < 80:
            label = "weak"
        else:
            label = "very_weak"

        return {
            "score": score,
            "label": label,
            "components": components,
        }


    def classify_cell(
        self,
        *,
        cell: CampaignCell,
        comparable_cprs: list[float],
        creative_aggregate: dict,
        best_creative: dict | None,
        replication: dict,
    ) -> dict:

        exploration_days = META_RULES[
            "exploration_days"
        ]

        if (
            cell.days_active
            <= exploration_days
        ):
            return {
                "action": "keep",
                "reason": (
                    "Protected exploration period."
                ),
            }

        minimum_impressions = META_RULES[
            "min_cell_impressions"
        ]

        zero_result_min_spend = META_RULES[
            "zero_result_min_spend"
        ]

        # No-result cells can be removed after enough
        # opportunity to deliver.
        if (
            cell.results == 0
            and (
                cell.impressions
                >= minimum_impressions
                or cell.spend
                >= zero_result_min_spend
            )
        ):
            return {
                "action": "pause_candidate",
                "reason": (
                    "No results after meaningful "
                    "exploration spend or delivery."
                ),
            }

        minimum_results = META_RULES[
            "min_results_for_cpr_judgement"
        ]

        weak_multiplier = META_RULES[
            "weak_cell_multiplier"
        ]

        # -------------------------------------------------
        # Signal 1:
        # Is this individual cell clearly weak?
        # -------------------------------------------------

        cell_is_directly_weak = False
        reference_cpr = None

        if (
            cell.results >= minimum_results
            and cell.cost_per_result is not None
            and comparable_cprs
        ):
            reference_cpr = median(
                comparable_cprs
            )

            cell_is_directly_weak = (
                cell.cost_per_result
                >= reference_cpr
                * weak_multiplier
            )

        if cell_is_directly_weak:
            return {
                "action": "pause_candidate",
                "reason": (
                    f"Cell CPR €"
                    f"{cell.cost_per_result:.3f} "
                    f"is at least "
                    f"{weak_multiplier:.2f}× "
                    f"the evidenced cell median "
                    f"€{reference_cpr:.3f}."
                ),
            }

        # -------------------------------------------------
        # Signal 2:
        # Is this creative weak overall?
        # -------------------------------------------------

        aggregate_is_weak = False

        if (
            best_creative is not None
            and creative_aggregate[
                "cost_per_result"
            ] is not None
            and best_creative[
                "cost_per_result"
            ] is not None
            and creative_aggregate[
                "results"
            ] >= minimum_results
            and creative_aggregate[
                "creative"
            ] != best_creative[
                "creative"
            ]
        ):
            aggregate_ratio = (
                creative_aggregate[
                    "cost_per_result"
                ]
                / best_creative[
                    "cost_per_result"
                ]
            )

            aggregate_is_weak = (
                aggregate_ratio
                >= weak_multiplier
            )

        # -------------------------------------------------
        # Signal 3:
        # Is the weakness replicated across audiences?
        # -------------------------------------------------

        replicated_weakness = (
            replication["comparisons"] >= 2
            and replication[
                "worse_fraction"
            ] >= 0.67
        )

        if (
            aggregate_is_weak
            and replicated_weakness
        ):
            return {
                "action": "pause_candidate",
                "reason": (
                    "Weak cell performance is supported "
                    "by cross-audience creative evidence. "
                    f"{creative_aggregate['creative']} "
                    f"has €"
                    f"{creative_aggregate['cost_per_result']:.3f} "
                    "combined CPR versus €"
                    f"{best_creative['cost_per_result']:.3f} "
                    f"for {best_creative['creative']} "
                    "and trails it in "
                    f"{replication['worse_count']}/"
                    f"{replication['comparisons']} "
                    "comparable audiences."
                ),
            }

        # Not enough evidence to judge this cell on CPR.
        if (
            cell.results < minimum_results
            or cell.cost_per_result is None
        ):
            return {
                "action": "keep",
                "reason": (
                    "Cell evidence is limited and "
                    "cross-audience evidence is not "
                    "strong enough to justify pausing."
                ),
            }

        return {
            "action": "keep",
            "reason": (
                "Performance remains within the "
                "acceptable range."
            ),
        }

    def evaluate_cells(
        self,
        cells: list[CampaignCell],
    ) -> list[dict]:

        minimum_results = META_RULES[
            "min_results_for_cpr_judgement"
        ]

        comparable_cprs = [
            cell.cost_per_result
            for cell in cells
            if (
                cell.active
                and cell.cost_per_result
                is not None
                and cell.results
                >= minimum_results
            )
        ]

        creative_aggregates = (
            self.build_creative_aggregates(
                cells
            )
        )

        best_creative = (
            self.get_best_creative(
                creative_aggregates
            )
        )

        decisions = []

        for cell in cells:

            aggregate = (
                creative_aggregates[
                    cell.creative
                ]
            )

            replication = (
                self.build_replication_summary(
                    creative=cell.creative,
                    best_creative=(
                        best_creative[
                            "creative"
                        ]
                        if best_creative
                        else None
                    ),
                    cells=cells,
                )
            )

            if not cell.active:
                decisions.append(
                    {
                        "audience":
                            cell.audience,

                        "creative":
                            cell.creative,

                        "action":
                            "already_paused",

                        "reason":
                            "Cell is already paused.",

                        "impressions":
                            cell.impressions,

                        "spend":
                            round(
                                cell.spend,
                                2,
                            ),

                        "results":
                            cell.results,

                        "cost_per_result":
                            cell.cost_per_result,

                        "creative_aggregate":
                            aggregate,

                        "replication":
                            replication,
                    }
                )

                continue

            evidence_profile = (
                self.build_cell_evidence_profile(
                    cell=cell,
                    comparable_cprs=
                        comparable_cprs,
                    creative_aggregate=
                        aggregate,
                    best_creative=
                        best_creative,
                    replication=
                        replication,
                )
            )

            decision = self.classify_cell(
                cell=cell,
                comparable_cprs=
                    comparable_cprs,
                creative_aggregate=
                    aggregate,
                best_creative=
                    best_creative,
                replication=
                    replication,
            )

            decisions.append(
                {
                    "audience":
                        cell.audience,

                    "creative":
                        cell.creative,

                    "action":
                        decision["action"],

                    "reason":
                        decision["reason"],

                    "impressions":
                        cell.impressions,

                    "spend":
                        round(
                            cell.spend,
                            2,
                        ),

                    "results":
                        cell.results,

                    "cost_per_result":
                        cell.cost_per_result,

                    "creative_aggregate":
                        {
                            "spend":
                                round(
                                    aggregate[
                                        "spend"
                                    ],
                                    2,
                                ),

                            "results":
                                aggregate[
                                    "results"
                                ],

                            "impressions":
                                aggregate[
                                    "impressions"
                                ],

                            "cost_per_result":
                                (
                                    round(
                                        aggregate[
                                            "cost_per_result"
                                        ],
                                        4,
                                    )
                                    if aggregate[
                                        "cost_per_result"
                                    ]
                                    is not None
                                    else None
                                ),
                        },

                    "replication":
                        replication,

                    "evidence_profile":
                        evidence_profile,
                }
            )

        return decisions

    # ---------------------------------------------------------
    # Audience-level evidence
    # ---------------------------------------------------------

    def build_audience_candidates(
        self,
        cells: list[CampaignCell],
        current_shares: dict[str, float],
    ) -> list[AudienceCandidate]:

        audience_names = sorted(
            {
                cell.audience
                for cell in cells
                if cell.active
            }
        )

        candidates = []

        for audience in audience_names:

            audience_cells = [
                cell
                for cell in cells
                if (
                    cell.audience == audience
                    and cell.active
                )
            ]

            impressions = sum(
                cell.impressions
                for cell in audience_cells
            )

            spend = sum(
                cell.spend
                for cell in audience_cells
            )

            results = sum(
                cell.results
                for cell in audience_cells
            )

            if results > 0:
                cpr = spend / results
            else:
                cpr = None

            candidates.append(
                AudienceCandidate(
                    name=audience,
                    current_share=(
                        current_shares.get(
                            audience,
                            0.0,
                        )
                    ),
                    impressions=impressions,
                    results=results,
                    spend=spend,
                    cost_per_result=cpr,
                    active=True,
                )
            )

        return candidates

    # ---------------------------------------------------------
    # Complete daily proposal
    # ---------------------------------------------------------

    def select_cells_for_budget(
        self,
        *,
        cells: list[CampaignCell],
        cell_decisions: list[dict],
        audience_allocations: list[dict],
    ) -> dict:
        """
        Convert evidence rankings into executable RUN / PAUSE
        decisions under today's audience-level budget.

        Higher pruning score = more expendable.

        Existing paused cells are never automatically resumed.
        """

        minimum_budget = META_RULES[
            "min_daily_budget_per_active_cell"
        ]

        headroom_pct = META_RULES.get(
            "cell_budget_headroom_pct",
            0.0,
        )

        effective_minimum_budget = (
            minimum_budget
            * (
                1.0
                + headroom_pct / 100.0
            )
        )

        decision_by_cell = {
            (
                item["audience"],
                item["creative"],
            ): item
            for item in cell_decisions
        }

        allocation_by_audience = {
            item["audience"]:
                item["proposed_daily_budget"]
            for item in audience_allocations
        }

        execution = []

        active_before = sum(
            1
            for cell in cells
            if cell.active
        )

        audience_names = sorted(
            {
                cell.audience
                for cell in cells
            }
        )

        for audience in audience_names:

            audience_cells = [
                cell
                for cell in cells
                if (
                    cell.audience == audience
                    and cell.active
                )
            ]

            # Preserve already-paused cells.
            for cell in cells:
                if (
                    cell.audience == audience
                    and not cell.active
                ):
                    execution.append(
                        {
                            "cell_id":
                                cell.cell_id,

                            "meta_adset_id":
                                cell.meta_adset_id,

                            "audience":
                                cell.audience,

                            "creative":
                                cell.creative,

                            "execution_action":
                                "remain_paused",

                            "pruning_priority":
                                None,

                            "evidence_label":
                                None,

                            "reason":
                                (
                                    "Cell is already paused "
                                    "and automatic resume is disabled."
                                ),
                        }
                    )

            if not audience_cells:
                continue

            audience_budget = (
                allocation_by_audience.get(
                    audience,
                    0.0,
                )
            )

            if effective_minimum_budget <= 0:
                capacity = len(
                    audience_cells
                )
            else:
                capacity = int(
                    audience_budget
                    // effective_minimum_budget
                )

            capacity = min(
                capacity,
                len(audience_cells),
            )

            ranked = []

            for cell in audience_cells:

                key = (
                    cell.audience,
                    cell.creative,
                )

                decision = (
                    decision_by_cell.get(
                        key
                    )
                )

                if (
                    decision is None
                    or "evidence_profile"
                    not in decision
                ):
                    raise RuntimeError(
                        "Missing evidence profile for "
                        f"{cell.audience} × {cell.creative}."
                    )

                pruning = (
                    self.calculate_pruning_priority(
                        decision[
                            "evidence_profile"
                        ]
                    )
                )

                ranked.append(
                    {
                        "cell":
                            cell,

                        "score":
                            pruning[
                                "score"
                            ],

                        "label":
                            pruning[
                                "label"
                            ],

                        "components":
                            pruning[
                                "components"
                            ],
                    }
                )

            # Lowest pruning score = strongest retention case.
            ranked.sort(
                key=lambda item: (
                    item["score"],
                    (
                        item["cell"].
                        cost_per_result
                        if item["cell"].
                        cost_per_result
                        is not None
                        else float("inf")
                    ),
                )
            )

            keep_keys = {
                (
                    item["cell"].audience,
                    item["cell"].creative,
                )
                for item in ranked[
                    :capacity
                ]
            }

            for rank_position, item in enumerate(
                ranked,
                start=1,
            ):
                cell = item[
                    "cell"
                ]

                key = (
                    cell.audience,
                    cell.creative,
                )

                if key in keep_keys:
                    execution_action = "run"

                    reason = (
                        "Retained within today's "
                        "audience budget based on "
                        "evidence ranking."
                    )

                else:
                    execution_action = (
                        "pause_budget_pressure"
                    )

                    reason = (
                        "Paused because today's "
                        "audience budget can support "
                        f"{capacity} active cells at "
                        f"the €{effective_minimum_budget:.2f}/day "
                        "effective planning floor "
                        f"(€{minimum_budget:.2f} minimum + "
                        f"{headroom_pct:.1f}% headroom), "
                        "and this cell ranked "
                        "below the retention cutoff."
                    )

                execution.append(
                    {
                        "cell_id":
                            cell.cell_id,

                        "meta_adset_id":
                            cell.meta_adset_id,

                        "audience":
                            cell.audience,

                        "creative":
                            cell.creative,

                        "execution_action":
                            execution_action,

                        "pruning_priority":
                            item["score"],

                        "evidence_label":
                            item["label"],

                        "rank_within_audience":
                            rank_position,

                        "audience_capacity":
                            capacity,

                        "audience_daily_budget":
                            round(
                                audience_budget,
                                2,
                            ),

                        "score_components":
                            item[
                                "components"
                            ],

                        "reason":
                            reason,
                    }
                )

        active_after = sum(
            1
            for item in execution
            if item[
                "execution_action"
            ] == "run"
        )

        paused_for_budget = sum(
            1
            for item in execution
            if item[
                "execution_action"
            ] == "pause_budget_pressure"
        )

        return {
            "active_before":
                active_before,

            "active_after":
                active_after,

            "paused_for_budget":
                paused_for_budget,

            "execution":
                execution,
        }


    def propose_day(
        self,
        *,
        total_budget: float,
        day: int,
        spent_so_far: float,
        cells: list[CampaignCell],
        current_audience_shares: dict[str, float],
    ) -> dict:

        daily_target = (
            self.daily_budget_target(
                total_budget=total_budget,
                day=day,
                spent_so_far=spent_so_far,
            )
        )

        if daily_target <= 0:
            return {
                "day": day,
                "mode": "stopped",
                "daily_target": 0.0,
                "cell_decisions": [],
                "audience_allocations": [],
                "message": (
                    "Campaign budget or duration "
                    "limit reached."
                ),
            }

        if (
            day
            <= META_RULES[
                "exploration_days"
            ]
        ):
            mode = "exploration"
        else:
            mode = "optimization"

        cell_decisions = (
            self.evaluate_cells(
                cells
            )
        )

        audience_candidates = (
            self.build_audience_candidates(
                cells,
                current_audience_shares,
            )
        )

        allocator = BudgetAllocator()

        audience_plan = allocator.propose(
            audience_candidates,
            daily_target,
        )

        budget_execution = (
            self.select_cells_for_budget(
                cells=cells,
                cell_decisions=
                    cell_decisions,
                audience_allocations=
                    audience_plan[
                        "allocations"
                    ],
            )
        )

        active_cell_count = (
            budget_execution[
                "active_after"
            ]
        )

        minimum_required = (
            active_cell_count
            * META_RULES[
                "min_daily_budget_per_active_cell"
            ]
        )

        warnings = []

        if (
            minimum_required
            > daily_target
        ):
            warnings.append(
                (
                    "Today's target budget is below "
                    "the minimum required to keep "
                    "every active cell funded at €"
                    f"{META_RULES['min_daily_budget_per_active_cell']:.2f}"
                    "/day."
                )
            )

        return {
            "day":
                day,

            "mode":
                mode,

            "daily_target":
                daily_target,

            "spent_so_far":
                round(
                    spent_so_far,
                    2,
                ),

            "remaining_budget":
                round(
                    max(
                        0.0,
                        total_budget
                        - spent_so_far,
                    ),
                    2,
                ),

            "active_cells":
                active_cell_count,

            "minimum_required_daily_budget":
                round(
                    minimum_required,
                    2,
                ),

            "cell_decisions":
                cell_decisions,

            "execution_plan":
                budget_execution,

            "audience_allocations":
                audience_plan[
                    "allocations"
                ],

            "warnings":
                warnings,

            "advisory_only":
                True,
        }
