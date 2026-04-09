"""
Tool 2: Sequential Testing Simulator
Vectorized simulation of alpha spending, type I error, and power under repeated peeking.
"""

import numpy as np
from scipy import stats
from functools import lru_cache


def obrien_fleming_boundary(k: int, K: int, alpha: float = 0.05) -> float:
    """O'Brien-Fleming cumulative alpha at look k of K."""
    t_k = k / K
    z_alpha = stats.norm.ppf(1 - alpha / 2)
    return float(2 * (1 - stats.norm.cdf(z_alpha / np.sqrt(t_k))))


def pocock_z_boundary(K: int, alpha: float = 0.05) -> float:
    """
    Pocock constant z-boundary (same at every look).
    Uses the Wang-Tsiatis family approximation for speed.
    Numerically finds c such that P(reject at any of K looks | H0) ≈ alpha.
    """
    # Fast vectorized simulation: generate K correlated test statistics
    rng = np.random.default_rng(0)
    n_sim = 30000
    # Brownian motion increments → correlated Z at each look
    increments = rng.standard_normal((n_sim, K))
    cumsum = np.cumsum(increments, axis=1)
    look_ns = np.arange(1, K + 1)
    z_proc = cumsum / np.sqrt(look_ns)  # (n_sim, K)

    # Binary search for c
    lo, hi = 1.5, 5.0
    for _ in range(20):
        c = (lo + hi) / 2
        reject_any = np.any(np.abs(z_proc) > c, axis=1)
        emp_alpha = reject_any.mean()
        if emp_alpha > alpha:
            hi = c
        else:
            lo = c
    return float((lo + hi) / 2)


def haybittle_peto_z(K: int, alpha: float = 0.05) -> tuple[float, float]:
    """
    Haybittle-Peto boundary: z=3.29 at all interim looks (α≈0.001 each),
    z_α at the final look. Returns (interim_z, final_z).
    """
    interim_z = 3.29
    # Final look z chosen so overall type I ≤ alpha; standard practice is just z_α
    final_z = float(stats.norm.ppf(1 - alpha / 2))
    return interim_z, final_z


def alpha_spending_table(
    K: int,
    boundary: str = "obrien_fleming",
    alpha: float = 0.05,
) -> list:
    """Return cumulative alpha spent at each interim look."""
    rows = []
    cumulative = 0.0

    if boundary == "obrien_fleming":
        for k in range(1, K + 1):
            spent = obrien_fleming_boundary(k, K, alpha)
            incremental = max(spent - cumulative, 0.0)
            cumulative = spent
            rows.append({
                "look": k,
                "fraction_observed": round(k / K, 3),
                "cumulative_alpha_spent": round(spent, 5),
                "incremental_alpha": round(incremental, 5),
                "z_boundary": round(stats.norm.ppf(1 - spent / 2), 3),
            })
    elif boundary == "pocock":
        c = pocock_z_boundary(K, alpha)
        p_each = float(2 * (1 - stats.norm.cdf(c)))
        for k in range(1, K + 1):
            cumulative = min(k * p_each, alpha)
            rows.append({
                "look": k,
                "fraction_observed": round(k / K, 3),
                "cumulative_alpha_spent": round(cumulative, 5),
                "incremental_alpha": round(p_each, 5),
                "z_boundary": round(c, 3),
            })
    elif boundary == "haybittle_peto":
        interim_z, final_z = haybittle_peto_z(K, alpha)
        p_interim = float(2 * (1 - stats.norm.cdf(interim_z)))
        p_final = float(2 * (1 - stats.norm.cdf(final_z)))
        for k in range(1, K + 1):
            z_b = final_z if k == K else interim_z
            p_k = p_final if k == K else p_interim
            cumulative = min(cumulative + p_k, alpha)
            rows.append({
                "look": k,
                "fraction_observed": round(k / K, 3),
                "cumulative_alpha_spent": round(cumulative, 5),
                "incremental_alpha": round(p_k, 5),
                "z_boundary": round(z_b, 3),
            })
    else:  # fixed — no correction
        z_alpha = stats.norm.ppf(1 - alpha / 2)
        for k in range(1, K + 1):
            rows.append({
                "look": k,
                "fraction_observed": round(k / K, 3),
                "cumulative_alpha_spent": round(alpha, 5),
                "incremental_alpha": round(alpha / K, 5),
                "z_boundary": round(z_alpha, 3),
            })
    return rows


def simulate_type1_inflation(
    K: int,
    n_total: int,
    alpha: float = 0.05,
    boundary: str = "fixed",
    n_sim: int = 5000,
) -> dict:
    """
    Vectorized type I error simulation under repeated peeking.
    Generates all n_sim experiments at once using Brownian motion on the z-process.
    """
    rng = np.random.default_rng(42)
    n_per_arm = n_total // 2
    look_ns = np.array([int(n_per_arm * k / K) for k in range(1, K + 1)])

    # Get z-boundaries per look
    if boundary == "obrien_fleming":
        z_bounds = np.array([
            stats.norm.ppf(1 - obrien_fleming_boundary(k, K, alpha) / 2)
            for k in range(1, K + 1)
        ])
    elif boundary == "pocock":
        c = pocock_z_boundary(K, alpha)
        z_bounds = np.full(K, c)
    elif boundary == "haybittle_peto":
        interim_z, final_z = haybittle_peto_z(K, alpha)
        z_bounds = np.array([final_z if k == K else interim_z for k in range(1, K + 1)])
    else:
        z_bounds = np.full(K, stats.norm.ppf(1 - alpha / 2))

    # Generate all data at once: shape (n_sim, n_per_arm)
    # Under H0: both arms standard normal
    ctrl_all = rng.standard_normal((n_sim, n_per_arm))
    treat_all = rng.standard_normal((n_sim, n_per_arm))

    look_rejections = np.zeros(K, dtype=int)
    already_stopped = np.zeros(n_sim, dtype=bool)
    false_positives = 0

    for i, (n_look, z_bound) in enumerate(zip(look_ns, z_bounds)):
        # Compute z-stats for each experiment at this look
        ctrl_slice = ctrl_all[:, :n_look]
        treat_slice = treat_all[:, :n_look]
        diff = treat_slice.mean(axis=1) - ctrl_slice.mean(axis=1)
        se = np.sqrt(2 / n_look)
        z_stats = diff / se

        reject_now = np.abs(z_stats) > z_bound
        # Only count first rejection (sequential testing)
        new_reject = reject_now & ~already_stopped
        n_new = int(new_reject.sum())
        look_rejections[i] += n_new
        false_positives += n_new
        already_stopped |= reject_now

    return {
        "empirical_type1_error": round(false_positives / n_sim, 4),
        "look_rejections": [r / n_sim for r in look_rejections.tolist()],
        "nominal_alpha": alpha,
        "boundary": boundary,
        "K": K,
    }


def simulate_power_sequential(
    K: int,
    n_total: int,
    true_effect: float,
    baseline_std: float = 1.0,
    alpha: float = 0.05,
    boundary: str = "obrien_fleming",
    n_sim: int = 5000,
) -> dict:
    """
    Vectorized power simulation under sequential design.
    true_effect: standardized effect (Cohen's d).
    """
    rng = np.random.default_rng(42)
    n_per_arm = n_total // 2
    look_ns = np.array([int(n_per_arm * k / K) for k in range(1, K + 1)])

    if boundary == "obrien_fleming":
        z_bounds = np.array([
            stats.norm.ppf(1 - obrien_fleming_boundary(k, K, alpha) / 2)
            for k in range(1, K + 1)
        ])
    elif boundary == "pocock":
        c = pocock_z_boundary(K, alpha)
        z_bounds = np.full(K, c)
    elif boundary == "haybittle_peto":
        interim_z, final_z = haybittle_peto_z(K, alpha)
        z_bounds = np.array([final_z if k == K else interim_z for k in range(1, K + 1)])
    else:
        z_bounds = np.full(K, stats.norm.ppf(1 - alpha / 2))

    # Generate all data: ctrl ~ N(0,1), treat ~ N(effect, 1)
    ctrl_all = rng.standard_normal((n_sim, n_per_arm))
    treat_all = rng.normal(true_effect / baseline_std, 1.0, (n_sim, n_per_arm))

    rejections = 0
    ever_rejected = np.zeros(n_sim, dtype=bool)
    stopping_looks = np.zeros(n_sim, dtype=int)  # 0 = never rejected
    already_stopped = np.zeros(n_sim, dtype=bool)
    look_rejections = np.zeros(K, dtype=int)

    for i, (n_look, z_bound) in enumerate(zip(look_ns, z_bounds)):
        diff = treat_all[:, :n_look].mean(axis=1) - ctrl_all[:, :n_look].mean(axis=1)
        se = baseline_std * np.sqrt(2 / n_look)
        z_stats = diff / se

        reject_now = np.abs(z_stats) > z_bound
        new_reject = reject_now & ~already_stopped
        n_new = int(new_reject.sum())
        rejections += n_new
        look_rejections[i] += n_new
        stopping_looks[new_reject] = i + 1
        ever_rejected |= new_reject
        already_stopped |= reject_now

    # Expected stopping look computed only over experiments that actually rejected
    if ever_rejected.any():
        expected_stop = round(float(stopping_looks[ever_rejected].mean()), 2)
    else:
        expected_stop = float(K)

    return {
        "power": round(rejections / n_sim, 4),
        "expected_stopping_look": expected_stop,
        "stopping_look_distribution": look_rejections.tolist(),
        "looks": list(range(1, K + 1)),
        "boundary": boundary,
        "n_never_rejected": int(n_sim - ever_rejected.sum()),
    }
