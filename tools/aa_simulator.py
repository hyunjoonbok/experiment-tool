"""
Tool: A/A Test Simulator
Vectorized simulation of A/A experiments (no true effect) to estimate empirical
false positive rate and validate randomization quality via SRM detection.
"""

import numpy as np
from scipy import stats


# ── Core A/A simulation ────────────────────────────────────────────────────────

def simulate_aa(
    metric_type: str,
    n_per_arm: int,
    baseline_mean: float,
    baseline_std: float = 1.0,
    alpha: float = 0.05,
    n_sim: int = 1000,
    seed: int = 42,
) -> dict:
    """
    Run n_sim A/A experiments. Both arms drawn from identical distributions.

    Memory strategy:
    - Binary: binomial counts are O(n_sim) regardless of n_per_arm.
    - Continuous: simulate CLT summary statistics directly — O(n_sim) memory.
      Exact for normal data: diff of means ~ N(0, 2σ²/n);
      pooled variance ~ σ² · χ²(2(n−1)) / (2(n−1)) → t-statistic is exact.

    Returns:
        p_values, z_stats, false_positive_rate, confidence interval, running FPR,
        KS uniformity test result, z-stat calibration metrics.
    """
    rng = np.random.default_rng(seed)
    n_per_arm = max(n_per_arm, 5)

    if metric_type == "binary":
        p = float(np.clip(baseline_mean, 0.001, 0.999))
        ctrl = rng.binomial(n_per_arm, p, n_sim).astype(float)
        treat = rng.binomial(n_per_arm, p, n_sim).astype(float)
        p_ctrl = ctrl / n_per_arm
        p_treat = treat / n_per_arm
        p_pool = (ctrl + treat) / (2 * n_per_arm)
        se = np.sqrt(p_pool * (1 - p_pool) * 2 / n_per_arm)
        se = np.where(se < 1e-10, 1e-10, se)
        z_stats = (p_treat - p_ctrl) / se

    else:  # continuous
        sigma = max(float(baseline_std), 1e-8)
        dof = 2 * (n_per_arm - 1)
        # Difference of sample means ~ N(0, 2σ²/n) under null
        diff = rng.normal(0.0, sigma * np.sqrt(2.0 / n_per_arm), n_sim)
        # Pooled sample variance via chi-square (exact for normal populations)
        chi2_samp = rng.chisquare(max(dof, 1), n_sim)
        pooled_var = sigma ** 2 * chi2_samp / max(dof, 1)
        pooled_se = np.sqrt(pooled_var * 2.0 / n_per_arm)
        pooled_se = np.where(pooled_se < 1e-10, 1e-10, pooled_se)
        z_stats = diff / pooled_se

    p_values = 2.0 * stats.norm.sf(np.abs(z_stats))

    # ── Empirical FPR + Wilson CI ─────────────────────────────────────────
    n_fp = int(np.sum(p_values < alpha))
    fpr = n_fp / n_sim
    z95 = 1.96
    denom = 1 + z95 ** 2 / n_sim
    centre = (fpr + z95 ** 2 / (2 * n_sim)) / denom
    margin = z95 * np.sqrt(fpr * (1 - fpr) / n_sim + z95 ** 2 / (4 * n_sim ** 2)) / denom
    fpr_ci = (round(float(max(0.0, centre - margin)), 4),
              round(float(min(1.0, centre + margin)), 4))

    # ── Running FPR (subsampled to ≤200 points) ──────────────────────────
    cum_fp = np.cumsum(p_values < alpha)
    run_fpr_full = cum_fp / np.arange(1, n_sim + 1)
    idx = np.linspace(0, n_sim - 1, min(200, n_sim)).astype(int)
    running_fpr = [{"sim": int(i + 1), "fpr": round(float(run_fpr_full[i]), 4)} for i in idx]

    # ── KS test: p-values vs Uniform[0,1] ────────────────────────────────
    ks_stat, ks_p = stats.kstest(p_values, "uniform")

    # ── Z-stat calibration ────────────────────────────────────────────────
    z_mean = float(np.mean(z_stats))
    z_std = float(np.std(z_stats, ddof=1))

    return {
        "p_values": p_values.tolist(),
        "z_stats": z_stats.tolist(),
        "false_positive_rate": round(fpr, 4),
        "n_false_positives": n_fp,
        "fpr_ci": fpr_ci,
        "expected_fpr": alpha,
        "running_fpr": running_fpr,
        "n_sim": n_sim,
        "n_per_arm": n_per_arm,
        "ks_stat": round(float(ks_stat), 4),
        "ks_p_value": round(float(ks_p), 4),
        "z_mean": round(z_mean, 4),
        "z_std": round(z_std, 4),
    }


# ── Multi-metric false positive projection ────────────────────────────────────

def multi_metric_fp_table(alpha: float, n_sim: int, max_metrics: int = 10) -> list:
    """
    For k = 1..max_metrics simultaneous metrics, compute:
      - FWER without correction
      - Expected # of false positive experiments (out of n_sim)
      - Expected # of false positive metrics per experiment
      - Bonferroni per-test alpha
    """
    rows = []
    for k in range(1, max_metrics + 1):
        fwer = 1 - (1 - alpha) ** k
        rows.append({
            "# Metrics": k,
            "FWER (no correction)": round(fwer, 4),
            "Expected false positive runs": round(fwer * n_sim, 1),
            "Avg false positive metrics / experiment": round(k * alpha, 2),
            "Bonferroni threshold per metric": round(alpha / k, 5),
        })
    return rows


# ── SRM check ─────────────────────────────────────────────────────────────────

def srm_check(
    observed_counts: list,
    expected_fractions: list,
    variant_names: list = None,
) -> dict:
    """
    Chi-square goodness-of-fit test for Sample Ratio Mismatch.

    Args:
        observed_counts: user counts per variant
        expected_fractions: expected traffic fractions (must sum ≈ 1)
        variant_names: display labels for each variant

    Returns dict with chi2, p_value, per-variant breakdown, and SRM verdict.
    Note: SRM threshold is 0.01 (stricter than the standard 0.05) following
    the industry convention from Kohavi et al. (2020) §21.
    """
    k = len(observed_counts)
    if variant_names is None:
        variant_names = ["Control"] + [f"Treatment {i}" for i in range(1, k)]

    total = sum(observed_counts)
    if total == 0:
        return {"error": "Total observed count is 0."}

    expected_counts = [f * total for f in expected_fractions]
    chi2, p_val = stats.chisquare(observed_counts, f_exp=expected_counts)

    variants = []
    for i in range(k):
        obs = observed_counts[i]
        exp = expected_counts[i]
        diff = obs - exp
        pct_diff = diff / exp * 100 if exp > 0 else 0.0
        variants.append({
            "Variant": variant_names[i],
            "Observed": obs,
            "Expected": round(exp),
            "Difference": round(diff),
            "% Difference": round(pct_diff, 2),
        })

    p_val_f = float(p_val)
    return {
        "chi2": round(float(chi2), 4),
        "p_value": round(p_val_f, 4),
        "total_users": total,
        "variants": variants,
        "srm_detected": p_val_f < 0.01,
        "warning_zone": 0.01 <= p_val_f < 0.05,
    }


# ── Randomization stability over time (sequential SRM) ────────────────────────

def sequential_srm(
    daily_control: list,
    daily_treatment: list,
    expected_split: float = 0.5,
) -> list:
    """
    Run SRM check on cumulative traffic day by day.
    Returns list of {day, cumulative_control, cumulative_treatment, p_value, srm_flag}.
    Useful for detecting randomization drift mid-experiment.
    """
    rows = []
    cum_ctrl = 0
    cum_treat = 0
    expected_frac = [expected_split, 1 - expected_split]

    for day, (c, t) in enumerate(zip(daily_control, daily_treatment), start=1):
        cum_ctrl += c
        cum_treat += t
        total = cum_ctrl + cum_treat
        if total < 10:
            rows.append({
                "day": day,
                "cumulative_control": cum_ctrl,
                "cumulative_treatment": cum_treat,
                "p_value": None,
                "srm_flag": False,
            })
            continue
        result = srm_check([cum_ctrl, cum_treat], expected_frac)
        rows.append({
            "day": day,
            "cumulative_control": cum_ctrl,
            "cumulative_treatment": cum_treat,
            "p_value": result["p_value"],
            "srm_flag": result["srm_detected"],
        })
    return rows
