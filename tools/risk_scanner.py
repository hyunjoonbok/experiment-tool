"""
Tool 5: Experiment Risk Scanner
Scores SRM, Simpson's paradox, cannibalization, novelty effect,
traffic imbalance, and metric gaming risks.
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Literal


@dataclass
class RiskFlag:
    name: str
    level: Literal["green", "yellow", "red"]
    score: float          # 0–100
    explanation: str
    recommendation: str


def srm_risk(
    n_control: int,
    n_treatment: int,
    expected_allocation: float = 0.5,
) -> RiskFlag:
    """
    Sample Ratio Mismatch: chi-square test on observed vs expected allocation.
    """
    n_total = n_control + n_treatment
    expected_ctrl = n_total * expected_allocation
    expected_treat = n_total * (1 - expected_allocation)

    chi2 = (
        (n_control - expected_ctrl) ** 2 / expected_ctrl
        + (n_treatment - expected_treat) ** 2 / expected_treat
    )
    p_val = 1 - stats.chi2.cdf(chi2, df=1)
    observed_ratio = n_control / n_total if n_total > 0 else expected_allocation
    deviation_pct = abs(observed_ratio - expected_allocation) / expected_allocation * 100

    if p_val < 0.001 or deviation_pct > 5:
        level = "red"
        score = 90
    elif p_val < 0.05 or deviation_pct > 2:
        level = "yellow"
        score = 55
    else:
        level = "green"
        score = 10

    return RiskFlag(
        name="Sample Ratio Mismatch (SRM)",
        level=level,
        score=score,
        explanation=f"Observed allocation: {observed_ratio:.1%} vs expected {expected_allocation:.1%} "
                    f"(deviation: {deviation_pct:.1f}%, p={p_val:.4f})",
        recommendation="Audit randomization pipeline. Check for logging bugs, bot traffic, or targeting filters." if level != "green" else "Allocation looks balanced.",
    )


def simpsons_paradox_risk(
    n_segments: int,
    segment_size_imbalance: float,  # 0 = perfectly balanced, 1 = maximally imbalanced
    metric_correlation: float,      # correlation between segment membership and outcome
) -> RiskFlag:
    """
    Estimate Simpson's paradox risk based on segment count and correlation structure.
    """
    base_score = n_segments * 8 + segment_size_imbalance * 30 + abs(metric_correlation) * 40
    score = min(base_score, 100)

    if score >= 60:
        level = "red"
    elif score >= 30:
        level = "yellow"
    else:
        level = "green"

    return RiskFlag(
        name="Simpson's Paradox Risk",
        level=level,
        score=round(score, 1),
        explanation=f"{n_segments} segments analyzed, imbalance={segment_size_imbalance:.0%}, "
                    f"metric-segment correlation={metric_correlation:.2f}",
        recommendation="Pre-register segment analysis. Use stratified randomization. Report overall metric as primary." if level != "green" else "Segment structure appears balanced.",
    )


def traffic_imbalance_risk(
    n_control: int,
    n_treatment: int,
    expected_allocation: float = 0.5,
) -> RiskFlag:
    """
    Power loss due to unequal allocation.
    """
    n_total = n_control + n_treatment
    actual_alloc = n_control / n_total if n_total > 0 else 0.5
    # Relative power loss = 4 * p * (1-p) vs optimal 50/50
    power_factor = 4 * actual_alloc * (1 - actual_alloc)
    power_loss_pct = (1 - power_factor) * 100

    if power_loss_pct > 20:
        level = "red"
        score = 80
    elif power_loss_pct > 5:
        level = "yellow"
        score = 45
    else:
        level = "green"
        score = 10

    return RiskFlag(
        name="Traffic Imbalance",
        level=level,
        score=score,
        explanation=f"Actual allocation: {actual_alloc:.1%} / {1-actual_alloc:.1%}. "
                    f"Estimated power loss: {power_loss_pct:.1f}%",
        recommendation="Rebalance traffic to 50/50 or use unequal allocation power formulas." if level != "green" else "Allocation is efficient.",
    )


def cannibalization_risk(
    randomization_unit: Literal["user", "session", "geo", "device"],
    feature_type: str,
) -> RiskFlag:
    """
    Estimate interference / cannibalization risk based on randomization unit and feature type.
    """
    unit_scores = {"session": 70, "device": 50, "user": 20, "geo": 10}
    market_penalty = 30 if feature_type in ("marketplace", "social", "referral") else 0
    score = min(unit_scores.get(randomization_unit, 30) + market_penalty, 100)

    if score >= 60:
        level = "red"
    elif score >= 30:
        level = "yellow"
    else:
        level = "green"

    explanations = {
        "session": "Session-level randomization allows the same user to be in both arms across sessions.",
        "device": "Device-level randomization risks cross-device contamination for logged-in users.",
        "user": "User-level randomization is generally safe for non-networked features.",
        "geo": "Geo randomization minimizes interference for network-effect features.",
    }

    return RiskFlag(
        name="Cannibalization / Interference",
        level=level,
        score=score,
        explanation=explanations.get(randomization_unit, "") + (
            " Marketplace/social features risk network-level spillover." if market_penalty else ""
        ),
        recommendation="Switch to user or geo-level randomization. Use SUTVA tests." if level != "green" else "Randomization unit is appropriate.",
    )


def novelty_effect_risk(
    experiment_duration_days: int,
    feature_type: str,
    is_new_feature: bool = True,
) -> RiskFlag:
    """
    Flag novelty effect based on duration and feature type.
    """
    high_novelty_types = {"ai_usage", "engagement", "marketplace"}
    novelty_prone = feature_type.lower() in high_novelty_types and is_new_feature

    if experiment_duration_days < 7:
        score = 85 if novelty_prone else 60
    elif experiment_duration_days < 14:
        score = 60 if novelty_prone else 35
    elif experiment_duration_days < 21:
        score = 40 if novelty_prone else 20
    else:
        score = 15

    if score >= 60:
        level = "red"
    elif score >= 30:
        level = "yellow"
    else:
        level = "green"

    return RiskFlag(
        name="Novelty Effect",
        level=level,
        score=score,
        explanation=f"Duration: {experiment_duration_days} days, feature type: {feature_type}. "
                    f"{'High novelty risk category.' if novelty_prone else 'Lower novelty risk category.'}",
        recommendation="Run for at least 2–4 weeks. Analyze day-over-day trend of the metric." if level != "green" else "Duration is sufficient to mitigate novelty effect.",
    )


def metric_gaming_risk(
    metric_type: str,
    has_pre_experiment_data: bool,
) -> RiskFlag:
    """
    Assess vulnerability to metric gaming based on metric type.
    """
    gameable_metrics = {"click", "ctr", "impression", "open_rate", "view", "click_rate"}
    is_gameable = any(m in metric_type.lower() for m in gameable_metrics)
    score = 65 if is_gameable else 20
    if not has_pre_experiment_data:
        score += 20
    score = min(score, 100)

    if score >= 60:
        level = "red"
    elif score >= 35:
        level = "yellow"
    else:
        level = "green"

    return RiskFlag(
        name="Metric Gaming Vulnerability",
        level=level,
        score=score,
        explanation=f"Metric '{metric_type}' {'is susceptible to artificial inflation' if is_gameable else 'is relatively hard to game'}. "
                    f"{'No pre-experiment data increases risk.' if not has_pre_experiment_data else ''}",
        recommendation="Add downstream quality guardrails (e.g., downstream conversion). Use pre-experiment data for CUPED." if level != "green" else "Metric appears robust to gaming.",
    )


def run_risk_scan(
    n_control: int,
    n_treatment: int,
    expected_allocation: float,
    n_segments: int,
    segment_size_imbalance: float,
    metric_correlation: float,
    randomization_unit: str,
    feature_type: str,
    experiment_duration_days: int,
    is_new_feature: bool,
    metric_type: str,
    has_pre_experiment_data: bool,
) -> list[RiskFlag]:
    """Run all risk checks and return list of RiskFlags."""
    return [
        srm_risk(n_control, n_treatment, expected_allocation),
        simpsons_paradox_risk(n_segments, segment_size_imbalance, metric_correlation),
        traffic_imbalance_risk(n_control, n_treatment, expected_allocation),
        cannibalization_risk(randomization_unit, feature_type),
        novelty_effect_risk(experiment_duration_days, feature_type, is_new_feature),
        metric_gaming_risk(metric_type, has_pre_experiment_data),
    ]
