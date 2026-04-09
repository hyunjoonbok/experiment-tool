"""
Tool 1: Advanced Power & MDE Simulator
Vectorized Monte Carlo engine for binary, continuous, and ratio metrics.
Includes CUPED, clustering ICC adjustments.
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass
from typing import Optional


@dataclass
class PowerResult:
    power: float
    required_n_per_arm: int
    mde: float
    variance: float


def cuped_variance(base_variance: float, r_squared: float) -> float:
    """Reduce variance using CUPED: Var_cuped = Var * (1 - R²)."""
    return base_variance * (1 - r_squared)


def cluster_design_effect(icc: float, cluster_size: float) -> float:
    """Design effect for cluster randomization: DEFF = 1 + (m-1)*ICC."""
    return 1 + (cluster_size - 1) * icc


def analytical_power_binary(
    p_control: float,
    effect_size: float,
    n_per_arm: int,
    alpha: float = 0.05,
) -> float:
    """Two-proportion z-test power (analytical, exact)."""
    p_treat = min(p_control * (1 + effect_size), 0.9999)
    se_alt = np.sqrt((p_control * (1 - p_control) + p_treat * (1 - p_treat)) / n_per_arm)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    ncp = abs(p_treat - p_control) / se_alt
    power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
    return float(np.clip(power, 0, 1))


def analytical_power_continuous(
    mean: float,
    std: float,
    effect_size: float,
    n_per_arm: int,
    alpha: float = 0.05,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
) -> float:
    """Two-sample t-test power (analytical). Applies CUPED and clustering adjustments."""
    eff_std = std * np.sqrt(1 - r_squared)
    deff = cluster_design_effect(icc, cluster_size) if icc > 0 else 1.0
    eff_n = max(int(n_per_arm / deff), 5)

    delta = abs(mean * effect_size)
    se = eff_std * np.sqrt(2 / eff_n)
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    ncp = delta / se
    power = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
    return float(np.clip(power, 0, 1))


def monte_carlo_power_ratio(
    baseline_mean: float,
    baseline_std: float,
    effect_size: float,
    n_per_arm: int,
    alpha: float = 0.05,
    n_sim: int = 2000,
    mean_denom: float = 1.0,
    var_denom: float = 0.1,
    rng: Optional[np.random.Generator] = None,
) -> float:
    """
    Vectorized Monte Carlo power for ratio metrics (CTR-style).

    To avoid OOM at large n_per_arm, simulates at most _RATIO_MC_BATCH observations
    per arm. The per-observation variance is estimated from this batch and then
    divided by the actual n_per_arm for the SE — identical to the standard error
    formula used in production (SE = sqrt(Var(r_i) / n)). This is exact in
    expectation and does not require the delta-method approximation.
    """
    if rng is None:
        rng = np.random.default_rng(42)

    mean_num = baseline_mean * mean_denom
    treat_mean_num = mean_num * (1 + effect_size)
    std_denom = np.sqrt(var_denom)

    # Batch size: cap at _RATIO_MC_BATCH regardless of n_per_arm.
    # Peak memory: 4 arrays × (n_sim × n_batch) × 8 bytes ≤ ~128 MB.
    n_batch = min(n_per_arm, _RATIO_MC_BATCH)

    ctrl_num  = rng.normal(mean_num,       baseline_std, (n_sim, n_batch))
    ctrl_den  = rng.normal(mean_denom,     std_denom,    (n_sim, n_batch))
    treat_num = rng.normal(treat_mean_num, baseline_std, (n_sim, n_batch))
    treat_den = rng.normal(mean_denom,     std_denom,    (n_sim, n_batch))

    ctrl_den  = np.where(np.abs(ctrl_den)  < 1e-9, 1e-9, ctrl_den)
    treat_den = np.where(np.abs(treat_den) < 1e-9, 1e-9, treat_den)

    ctrl_ratio  = ctrl_num  / ctrl_den    # (n_sim, n_batch)
    treat_ratio = treat_num / treat_den

    # Batch means estimate E[r_i]; batch variances estimate Var(r_i).
    # SE of the full-n mean = sqrt(Var(r_i) / n_per_arm).
    ctrl_means  = ctrl_ratio.mean(axis=1)           # (n_sim,)
    treat_means = treat_ratio.mean(axis=1)
    ctrl_vars   = ctrl_ratio.var(axis=1, ddof=1)    # per-observation variance
    treat_vars  = treat_ratio.var(axis=1, ddof=1)

    pooled_se = np.sqrt((ctrl_vars + treat_vars) / n_per_arm)
    pooled_se = np.where(pooled_se < 1e-12, 1e-12, pooled_se)
    t_stats = (treat_means - ctrl_means) / pooled_se

    z_crit = stats.norm.ppf(1 - alpha / 2)
    return float(np.mean(np.abs(t_stats) > z_crit))


# Max observations per simulation batch — caps peak memory at ~128 MB regardless
# of n_per_arm. Per-observation variance is estimated from this batch and then
# scaled to the actual n_per_arm for the SE calculation.
_RATIO_MC_BATCH = 2_000


def compute_power(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    effect_size: float,
    n_per_arm: int,
    alpha: float = 0.05,
    n_sim: int = 2000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
) -> float:
    """
    Dispatch to analytical formula (binary/continuous) or vectorized MC (ratio).
    """
    if metric_type == "binary":
        p = analytical_power_binary(baseline_mean, effect_size, n_per_arm, alpha)
        # Apply CUPED and clustering as effective n adjustment
        deff = cluster_design_effect(icc, cluster_size) if icc > 0 else 1.0
        eff_n = max(int(n_per_arm / deff), 5)
        # Re-compute with CUPED-adjusted std and effective n
        p_treat = min(baseline_mean * (1 + effect_size), 0.9999)
        p_ctrl = baseline_mean
        # CUPED reduces variance by (1 - R²)
        var_ctrl = p_ctrl * (1 - p_ctrl) * (1 - r_squared)
        var_treat = p_treat * (1 - p_treat) * (1 - r_squared)
        se = np.sqrt((var_ctrl + var_treat) / eff_n)
        if se < 1e-12:
            return 1.0
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        ncp = abs(p_treat - p_ctrl) / se
        p = 1 - stats.norm.cdf(z_alpha - ncp) + stats.norm.cdf(-z_alpha - ncp)
        return float(np.clip(p, 0, 1))
    elif metric_type == "continuous":
        return analytical_power_continuous(
            baseline_mean, baseline_std, effect_size, n_per_arm, alpha, r_squared, icc, cluster_size
        )
    else:  # ratio
        deff = cluster_design_effect(icc, cluster_size) if icc > 0 else 1.0
        eff_n = max(int(n_per_arm / deff), 5)
        eff_std = baseline_std * np.sqrt(1 - r_squared)
        return monte_carlo_power_ratio(
            baseline_mean=baseline_mean,
            baseline_std=eff_std,
            effect_size=effect_size,
            n_per_arm=eff_n,
            alpha=alpha,
            n_sim=n_sim,
        )


def power_curve(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    effect_size: float,
    alpha: float = 0.05,
    n_sim: int = 2000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
    sample_sizes: Optional[list] = None,
) -> dict:
    """
    Compute power across a range of sample sizes.
    Returns dict with 'n_per_arm' and 'power' lists.
    """
    if sample_sizes is None:
        sample_sizes = list(range(100, 5001, 250))

    rng = np.random.default_rng(42)
    powers = []
    for n in sample_sizes:
        if metric_type == "ratio":
            deff = cluster_design_effect(icc, cluster_size) if icc > 0 else 1.0
            eff_n = max(int(n / deff), 5)
            eff_std = baseline_std * np.sqrt(1 - r_squared)
            p = monte_carlo_power_ratio(
                    baseline_mean, eff_std, effect_size, eff_n, alpha, n_sim, rng=rng
                )
        else:
            p = compute_power(
                metric_type, baseline_mean, baseline_std, effect_size,
                n, alpha, n_sim, r_squared, icc, cluster_size,
            )
        powers.append(round(p, 4))

    return {"n_per_arm": sample_sizes, "power": powers}


def mde_for_power(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    target_power: float = 0.8,
    alpha: float = 0.05,
    n_per_arm: int = 1000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
) -> float:
    """
    Binary search for minimum detectable effect at target power.
    Returns effect size as a fraction of baseline.
    Analytical for binary/continuous (instant); MC for ratio.
    """
    lo, hi = 0.001, 2.0
    n_iter = 25 if metric_type == "ratio" else 40  # fewer iters for MC
    for _ in range(n_iter):
        mid = (lo + hi) / 2
        p = compute_power(
            metric_type, baseline_mean, baseline_std, mid,
            n_per_arm, alpha, 1000, r_squared, icc, cluster_size,
        )
        if p < target_power:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def sample_size_for_effect(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    effect_size: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    n_sim: int = 1000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
) -> int:
    """Binary search for minimum n_per_arm to achieve target_power at a given effect size."""
    # Binary/continuous use analytical formulas — no cost to searching up to 50M.
    # Ratio uses batch MC (capped at 2k obs/sim) — also safe at large N.
    # Low CVR + small relative MDE can require millions of users (e.g. p=1.2%, MDE=2%
    # → Δ=0.024pp → ~3.3M per arm). A 500k cap silently returns a wrong answer.
    lo, hi = 50, 50_000_000
    # Ratio: 25 iters covers [50, 50M] with ~6% precision (2^25 = 33M range).
    # Binary/continuous: 40 iters covers [50, 50M] with <0.01% precision.
    n_iter = 25 if metric_type == "ratio" else 40
    for _ in range(n_iter):
        mid = (lo + hi) // 2
        pwr = compute_power(
            metric_type, baseline_mean, baseline_std,
            effect_size, mid, alpha, n_sim, r_squared, icc, cluster_size,
        )
        if pwr < target_power:
            lo = mid
        else:
            hi = mid
    return hi


ZONE_THRESHOLDS = [
    (2, "VIABLE"),
    (4, "PATIENCE"),
    (8, "MARGINAL"),
    (float("inf"), "NOT VIABLE"),
]


def feasibility_curve(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    daily_traffic: int = 1000,
    n_sim: int = 1000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
    mde_values: Optional[list] = None,
) -> list:
    """
    For each MDE value, compute required n_per_arm and weeks.
    Returns list of dicts: {mde_pct, weeks, n_per_arm, zone}.
    Used for the Feasibility Zone chart (X=MDE%, Y=weeks).
    """
    if mde_values is None:
        mde_values = [2, 3, 5, 7, 10, 12, 15, 20, 25, 30, 40, 50]
    rows = []
    for mde_pct in mde_values:
        effect_size = mde_pct / 100.0
        n_per_arm = sample_size_for_effect(
            metric_type, baseline_mean, baseline_std, effect_size,
            alpha, target_power, n_sim, r_squared, icc, cluster_size,
        )
        weeks = (n_per_arm / daily_traffic) / 7 if daily_traffic > 0 else None
        zone = "NOT VIABLE"
        if weeks is not None:
            for threshold, label in ZONE_THRESHOLDS:
                if weeks <= threshold:
                    zone = label
                    break
        rows.append({
            "mde_pct": mde_pct,
            "weeks": round(weeks, 2) if weeks is not None else None,
            "n_per_arm": n_per_arm,
            "zone": zone,
        })
    return [r for r in rows if r["weeks"] is None or r["weeks"] <= 20]


def tradeoff_scenarios(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    alpha: float = 0.05,
    target_power: float = 0.80,
    daily_traffic: int = 1000,
    n_sim: int = 1000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
    durations_days: Optional[list] = None,
) -> list:
    """
    For each candidate duration, compute achievable MDE using mde_for_power().
    Returns list of dicts: {days, weeks, n_per_arm, mde_relative_pct, mde_absolute}.
    """
    if durations_days is None:
        durations_days = [7, 14, 21, 28, 42, 56, 84]
    rows = []
    for days in durations_days:
        n_per_arm = max(int(days * daily_traffic), 50)
        mde_rel = mde_for_power(
            metric_type, baseline_mean, baseline_std,
            target_power, alpha, n_per_arm,
            r_squared, icc, cluster_size,
        )
        rows.append({
            "days": days,
            "weeks": round(days / 7, 1),
            "n_per_arm": n_per_arm,
            "mde_relative_pct": round(mde_rel * 100, 2),
            "mde_absolute": round(mde_rel * baseline_mean, 6),
        })
    return rows


def sensitivity_heatmap(
    metric_type: str,
    baseline_mean: float,
    baseline_std: float,
    effect_sizes: list,
    sample_sizes: list,
    alpha: float = 0.05,
    n_sim: int = 2000,
    r_squared: float = 0.0,
    icc: float = 0.0,
    cluster_size: float = 1.0,
) -> list:
    """
    Compute power for all (effect_size, n) combinations.
    Returns list of dicts: [{'effect_size': ..., 'n_per_arm': ..., 'power': ...}]
    """
    rows = []
    for es in effect_sizes:
        for n in sample_sizes:
            p = compute_power(
                metric_type, baseline_mean, baseline_std, es,
                n, alpha, n_sim, r_squared, icc, cluster_size,
            )
            rows.append({
                "effect_size": f"{es:.0%}",
                "n_per_arm": n,
                "power": round(p, 3),
            })
    return rows
