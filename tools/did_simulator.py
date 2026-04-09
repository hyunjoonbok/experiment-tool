"""
Tool 7: DiD & Synthetic Control Simulator
Simulates bias, power, and CI coverage under varying parallel trend violations,
noise levels, pre-period lengths, and treatment intensities.
"""

import numpy as np
from scipy import stats
from dataclasses import dataclass


@dataclass
class DiDResult:
    true_effect: float
    estimated_effect: float
    bias: float
    bias_pct: float
    se: float
    ci_low: float
    ci_high: float
    ci_coverage: float   # empirical 95% CI coverage rate across simulations
    power: float


def generate_panel(
    n_units: int,
    n_pre: int,
    n_post: int,
    true_effect: float,
    noise: float,
    trend_violation: float,
    treatment_share: float = 0.5,
    rng: np.random.Generator = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Generate a balanced panel dataset for DiD simulation.

    Returns: (Y, treated, time) arrays, each shape (n_units * (n_pre + n_post),)
    trend_violation: additional trend in treated group pre-treatment (0 = perfect parallel trends)
    """
    if rng is None:
        rng = np.random.default_rng(42)

    n_periods = n_pre + n_post
    n_treated = int(n_units * treatment_share)

    unit_fe = rng.normal(0, 1, n_units)
    time_fe = np.linspace(-1, 1, n_periods)

    Y_list, treated_list, time_list = [], [], []

    for i in range(n_units):
        is_treated = int(i < n_treated)
        for t in range(n_periods):
            is_post = int(t >= n_pre)
            # Pre-trend violation: treated group drifts differently in pre-period
            pre_drift = trend_violation * (t / max(n_pre - 1, 1)) * is_treated * (1 - is_post)
            y = (unit_fe[i]
                 + time_fe[t]
                 + true_effect * is_treated * is_post
                 + pre_drift
                 + rng.normal(0, noise))
            Y_list.append(y)
            treated_list.append(is_treated)
            time_list.append(t)

    return np.array(Y_list), np.array(treated_list), np.array(time_list)


def estimate_did(
    Y: np.ndarray,
    treated: np.ndarray,
    time: np.ndarray,
    n_pre: int,
) -> tuple[float, float]:
    """
    Estimate DiD using the within estimator (unit FE absorbed by demeaning).
    Regresses unit-demeaned Y on unit-demeaned (treat×post) and (post) to control
    for unit fixed effects and the common time trend respectively.
    Returns (estimate, se).
    """
    n_obs = len(Y)
    n_periods = int(time.max()) + 1
    n_units = n_obs // n_periods
    unit_ids = np.arange(n_obs) // n_periods

    post = (time >= n_pre).astype(float)
    interact = treated * post

    # Within-unit demeaning: removes unit fixed effects from all variables
    Y_dm = Y.astype(float).copy()
    interact_dm = interact.astype(float).copy()
    post_dm = post.astype(float).copy()
    for u in range(n_units):
        mask = unit_ids == u
        Y_dm[mask] -= Y_dm[mask].mean()
        interact_dm[mask] -= interact_dm[mask].mean()
        post_dm[mask] -= post_dm[mask].mean()

    X = np.column_stack([interact_dm, post_dm])
    XtX = X.T @ X
    XtY = X.T @ Y_dm
    try:
        beta = np.linalg.solve(XtX, XtY)
    except np.linalg.LinAlgError:
        return 0.0, 1.0

    if not np.all(np.isfinite(beta)):
        return 0.0, 1.0

    resid = Y_dm - X @ beta
    # DOF: subtract absorbed unit FE and explicit regressors
    dof = max(n_obs - n_units - X.shape[1], 1)
    rtr = resid @ resid
    if not np.isfinite(rtr):
        return 0.0, 1.0

    sigma2 = rtr / dof
    try:
        cov_mat = sigma2 * np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        return float(beta[0]), 1.0

    se_val = cov_mat[0, 0]
    se = float(np.sqrt(se_val)) if np.isfinite(se_val) and se_val > 0 else 1.0
    est = float(beta[0]) if np.isfinite(beta[0]) else 0.0
    return est, se


def simulate_did(
    n_units: int,
    n_pre: int,
    n_post: int,
    true_effect: float,
    noise: float,
    trend_violation: float,
    n_sim: int = 2000,
    alpha: float = 0.05,
) -> DiDResult:
    """
    Vectorized DiD simulation over n_sim replications.
    Returns aggregate bias, power, and CI coverage.
    """
    rng = np.random.default_rng(42)
    z_crit = stats.norm.ppf(1 - alpha / 2)

    estimates = []
    ses = []

    for _ in range(n_sim):
        Y, treated, time = generate_panel(n_units, n_pre, n_post, true_effect, noise, trend_violation, rng=rng)
        est, se = estimate_did(Y, treated, time, n_pre)
        estimates.append(est)
        ses.append(se)

    estimates = np.array(estimates)
    ses = np.array(ses)

    mean_est = float(estimates.mean())
    mean_se = float(ses.mean())
    bias = mean_est - true_effect
    bias_pct = (bias / true_effect * 100) if true_effect != 0 else 0.0
    ci_low = mean_est - z_crit * mean_se
    ci_high = mean_est + z_crit * mean_se
    covers = float(np.mean((estimates - z_crit * ses <= true_effect) & (true_effect <= estimates + z_crit * ses)))
    t_stats = estimates / np.where(ses < 1e-10, 1e-10, ses)
    power = float(np.mean(np.abs(t_stats) > z_crit))

    return DiDResult(
        true_effect=true_effect,
        estimated_effect=round(mean_est, 4),
        bias=round(bias, 4),
        bias_pct=round(bias_pct, 2),
        se=round(mean_se, 4),
        ci_low=round(ci_low, 4),
        ci_high=round(ci_high, 4),
        ci_coverage=round(float(covers), 4),  # empirical coverage across all simulations
        power=round(power, 4),
    )


def pre_trend_data(
    n_units: int,
    n_pre: int,
    true_effect: float,
    noise: float,
    trend_violations: list[float],
    n_post: int = 4,
) -> list[dict]:
    """
    For each trend violation level, compute average treated/control trajectories.
    Returns list of {period, treated_mean, control_mean, violation} rows.
    """
    rng = np.random.default_rng(0)
    rows = []
    for tv in trend_violations:
        Y, treated, time = generate_panel(n_units, n_pre, n_post, true_effect, noise, tv, rng=rng)
        for t in range(n_pre + n_post):
            mask = time == t
            rows.append({
                "period": t - n_pre,  # 0 = treatment start
                "treated_mean": float(Y[mask & (treated == 1)].mean()),
                "control_mean": float(Y[mask & (treated == 0)].mean()),
                "violation": f"Δ={tv:.1f}",
            })
    return rows


def bias_vs_violation(
    n_units: int,
    n_pre: int,
    n_post: int,
    true_effect: float,
    noise: float,
    violations: list[float],
    n_sim: int = 1000,
) -> list[dict]:
    """
    Compute DiD bias as a function of trend violation magnitude.
    """
    rows = []
    for tv in violations:
        result = simulate_did(n_units, n_pre, n_post, true_effect, noise, tv, n_sim=n_sim)
        rows.append({
            "trend_violation": tv,
            "bias": result.bias,
            "bias_pct": result.bias_pct,
            "power": result.power,
            "ci_coverage": result.ci_coverage,
        })
    return rows


def power_vs_n(
    n_units_list: list[int],
    n_pre: int,
    n_post: int,
    true_effect: float,
    noise: float,
    trend_violation: float = 0.0,
    n_sim: int = 1000,
    alpha: float = 0.05,
) -> list[dict]:
    """Power curve as a function of number of units."""
    rows = []
    for n in n_units_list:
        result = simulate_did(n, n_pre, n_post, true_effect, noise, trend_violation, n_sim=n_sim, alpha=alpha)
        rows.append({"n_units": n, "power": result.power, "bias": result.bias})
    return rows
