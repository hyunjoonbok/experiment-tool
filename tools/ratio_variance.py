"""
Tool 3: Ratio Metric Variance Decomposition Tool
Delta method variance, bootstrap estimator, and covariance decomposition for CTR-type metrics.
"""

import numpy as np
from scipy import stats


def delta_method_variance(
    mean_num: float,
    var_num: float,
    mean_denom: float,
    var_denom: float,
    cov: float,
    n: int,
) -> dict:
    """
    Delta method variance for ratio Y/X:
    Var(Y/X) ≈ (1/N) * [term1 + term2 - term3]

    Returns breakdown of each term's contribution.
    """
    term1 = var_num / (mean_denom**2)
    term2 = (mean_num**2) * var_denom / (mean_denom**4)
    term3 = 2 * mean_num * cov / (mean_denom**3)
    total = (term1 + term2 - term3) / n
    total = max(total, 1e-12)

    return {
        "total_variance": round(total, 8),
        "std_error": round(np.sqrt(total), 6),
        "term1_numerator_variance": round(term1 / n, 8),
        "term2_denominator_variance": round(term2 / n, 8),
        "term3_covariance_adjustment": round(term3 / n, 8),
        "pct_term1": round(100 * (term1 / n) / total, 1) if total > 0 else 0,
        "pct_term2": round(100 * (term2 / n) / total, 1) if total > 0 else 0,
        "pct_term3": round(100 * (term3 / n) / total, 1) if total > 0 else 0,
    }


def bootstrap_variance(
    mean_num: float,
    var_num: float,
    mean_denom: float,
    var_denom: float,
    cov: float,
    n: int,
    n_boot: int = 5000,
    rng_seed: int = 42,
) -> dict:
    """
    Bootstrap estimate of ratio variance from a bivariate normal.
    Returns variance, 95% CI for the ratio, and comparison to delta method.
    """
    rng = np.random.default_rng(rng_seed)
    # Clamp off-diagonal to keep the matrix strictly positive definite
    max_cov = 0.999 * np.sqrt(var_num * var_denom)
    cov_clamped = float(np.clip(cov, -max_cov, max_cov))
    cov_matrix = np.array([[var_num, cov_clamped], [cov_clamped, var_denom]], dtype=float)
    cov_matrix[0, 0] += 1e-10
    cov_matrix[1, 1] += 1e-10

    # Use explicit Cholesky sampling. Suppress BLAS-level RuntimeWarnings that fire
    # on large arrays regardless of matrix conditioning, then validate the output.
    try:
        L = np.linalg.cholesky(cov_matrix)
        z = rng.standard_normal((n_boot * n, 2))
        with np.errstate(divide="ignore", over="ignore", invalid="ignore"):
            samples_flat = z @ L.T + np.array([mean_num, mean_denom])
        samples = samples_flat.reshape(n_boot, n, 2)
        num_means = samples[:, :, 0].mean(axis=1)
        den_means = samples[:, :, 1].mean(axis=1)
        den_means = np.where(np.abs(den_means) < 1e-12, 1e-12, den_means)
        ratios = num_means / den_means
        # If BLAS produced garbage, fall back to independent sampling
        if not np.all(np.isfinite(ratios)):
            raise np.linalg.LinAlgError("non-finite ratios")
    except (np.linalg.LinAlgError, ValueError):
        samples_num = rng.normal(mean_num, np.sqrt(var_num), (n_boot, n))
        samples_den = rng.normal(mean_denom, np.sqrt(var_denom), (n_boot, n))
        ratios = np.mean(samples_num, axis=1) / np.mean(samples_den, axis=1)

    boot_var = float(np.var(ratios, ddof=1))
    ci_low = float(np.percentile(ratios, 2.5))
    ci_high = float(np.percentile(ratios, 97.5))
    ratio_mean = float(np.mean(ratios))

    delta = delta_method_variance(mean_num, var_num, mean_denom, var_denom, cov, n)

    return {
        "bootstrap_variance": round(boot_var, 8),
        "bootstrap_std_error": round(np.sqrt(boot_var), 6),
        "ratio_mean": round(ratio_mean, 6),
        "ci_95_low": round(ci_low, 6),
        "ci_95_high": round(ci_high, 6),
        "delta_method_variance": delta["total_variance"],
        "delta_vs_bootstrap_ratio": round(delta["total_variance"] / boot_var, 3) if boot_var > 0 else None,
    }


def traffic_shift_impact(
    mean_num: float,
    var_num: float,
    mean_denom: float,
    var_denom: float,
    cov: float,
    n_base: int,
    shift_pcts: list[float],
) -> list[dict]:
    """
    Compute how variance changes as traffic shifts away from baseline.
    shift_pcts: list of percentage changes in n (e.g., [-50, -25, 0, 25, 50]).
    Returns list of {shift_pct, n, variance, std_error}.
    """
    rows = []
    for shift in shift_pcts:
        n_shifted = max(int(n_base * (1 + shift / 100)), 10)
        result = delta_method_variance(mean_num, var_num, mean_denom, var_denom, cov, n_shifted)
        rows.append({
            "traffic_shift_pct": shift,
            "n": n_shifted,
            "variance": result["total_variance"],
            "std_error": result["std_error"],
        })
    return rows


def variance_decomposition_chart_data(
    mean_num: float,
    var_num: float,
    mean_denom: float,
    var_denom: float,
    cov: float,
    n: int,
) -> list[dict]:
    """
    Return data for the variance decomposition bar chart.
    """
    result = delta_method_variance(mean_num, var_num, mean_denom, var_denom, cov, n)
    return [
        {"component": "Numerator Variance", "contribution": result["term1_numerator_variance"], "pct": result["pct_term1"]},
        {"component": "Denominator Variance", "contribution": result["term2_denominator_variance"], "pct": result["pct_term2"]},
        {"component": "Covariance Adjustment", "contribution": -result["term3_covariance_adjustment"], "pct": -result["pct_term3"]},
    ]
