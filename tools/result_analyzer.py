"""
Tool: Experiment Result Analyzer
Statistical analysis of A/B test results for binary and continuous metrics.
"""
import numpy as np
from scipy import stats


def analyze_binary(ctrl_n, ctrl_events, treat_n, treat_events, alpha=0.05, direction="higher"):
    """
    Two-proportion z-test (pooled) for binary metrics.
    CI uses unpooled standard error (more accurate for effect CI).
    Returns a rich result dict.
    """
    ctrl_rate = ctrl_events / ctrl_n
    treat_rate = treat_events / treat_n
    abs_change = treat_rate - ctrl_rate
    rel_change = abs_change / ctrl_rate if ctrl_rate > 1e-10 else 0.0

    # Pooled z-test for p-value
    p_pool = (ctrl_events + treat_events) / (ctrl_n + treat_n)
    se_pool = np.sqrt(p_pool * (1 - p_pool) * (1 / ctrl_n + 1 / treat_n))
    z = abs_change / se_pool if se_pool > 1e-10 else 0.0
    p_val = float(2 * stats.norm.sf(abs(z)))

    # Unpooled SE for CI
    se_un = np.sqrt(ctrl_rate * (1 - ctrl_rate) / ctrl_n + treat_rate * (1 - treat_rate) / treat_n)
    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lo = abs_change - z_crit * se_un
    ci_hi = abs_change + z_crit * se_un

    return _build_result(
        ctrl_val=ctrl_rate, treat_val=treat_rate,
        abs_change=abs_change, rel_change=rel_change,
        ci_lo=ci_lo, ci_hi=ci_hi,
        test_stat=z, p_val=p_val,
        alpha=alpha, direction=direction,
        value_type="rate",
    )


def analyze_continuous(ctrl_n, ctrl_mean, ctrl_std, treat_n, treat_mean, treat_std, alpha=0.05, direction="higher"):
    """
    Welch's t-test for continuous metrics.
    Returns a rich result dict.
    """
    abs_change = treat_mean - ctrl_mean
    rel_change = abs_change / ctrl_mean if abs(ctrl_mean) > 1e-10 else 0.0

    v1 = (ctrl_std ** 2) / ctrl_n
    v2 = (treat_std ** 2) / treat_n
    se = np.sqrt(v1 + v2)
    t = abs_change / se if se > 1e-10 else 0.0

    dof_num = (v1 + v2) ** 2
    dof_den = (v1 ** 2 / max(ctrl_n - 1, 1)) + (v2 ** 2 / max(treat_n - 1, 1))
    dof = dof_num / dof_den if dof_den > 0 else ctrl_n + treat_n - 2
    p_val = float(2 * stats.t.sf(abs(t), df=max(dof, 1)))

    z_crit = stats.norm.ppf(1 - alpha / 2)
    ci_lo = abs_change - z_crit * se
    ci_hi = abs_change + z_crit * se

    return _build_result(
        ctrl_val=ctrl_mean, treat_val=treat_mean,
        abs_change=abs_change, rel_change=rel_change,
        ci_lo=ci_lo, ci_hi=ci_hi,
        test_stat=t, p_val=p_val,
        alpha=alpha, direction=direction,
        value_type="mean",
    )


def _build_result(ctrl_val, treat_val, abs_change, rel_change, ci_lo, ci_hi, test_stat, p_val, alpha, direction, value_type):
    significant = p_val < alpha
    dir_positive = (abs_change > 0) == (direction == "higher")
    verdict = (
        "win" if significant and dir_positive else
        "loss" if significant and not dir_positive else
        "neutral"
    )
    rel_ci_lo = ci_lo / ctrl_val if abs(ctrl_val) > 1e-10 else ci_lo
    rel_ci_hi = ci_hi / ctrl_val if abs(ctrl_val) > 1e-10 else ci_hi

    return {
        "ctrl_val": ctrl_val,
        "treat_val": treat_val,
        "absolute_change": abs_change,
        "relative_change": rel_change,
        "ci_lo": ci_lo,
        "ci_hi": ci_hi,
        "rel_ci_lo": rel_ci_lo,
        "rel_ci_hi": rel_ci_hi,
        "test_stat": test_stat,
        "p_value": p_val,
        "significant": significant,
        "direction_positive": dir_positive,
        "verdict": verdict,
        "value_type": value_type,
    }


def overall_verdict(results):
    """
    Derive the overall experiment shipping decision from all metric results.
    results: list of result dicts with added keys: name, role, direction.
    Returns a verdict dict with display info.
    """
    north_stars = [r for r in results if r.get("role") == "North Star ⭐"]
    guardrails  = [r for r in results if r.get("role") == "Guardrail 🛡️"]
    guardrail_fails = [r for r in guardrails if r["significant"] and not r["direction_positive"]]

    if guardrail_fails:
        names = ", ".join(r["name"] for r in guardrail_fails)
        return {
            "verdict": "DON'T SHIP",
            "emoji": "🚫",
            "bg": "#fef2f2", "border": "#ef4444", "fg": "#b91c1c",
            "summary": f"Guardrail violated: {names}.",
            "detail": "The experiment caused measurable harm on a protected metric. Do not ship until the root cause is resolved.",
        }

    ns = north_stars[0] if north_stars else None
    if ns is None:
        wins = sum(1 for r in results if r["verdict"] == "win")
        return {
            "verdict": "REVIEW RESULTS",
            "emoji": "🔍",
            "bg": "#fffbeb", "border": "#f59e0b", "fg": "#92400e",
            "summary": f"{wins} of {len(results)} metric(s) show improvement. No primary metric defined.",
            "detail": "Define a North Star metric to get a clear go/no-go recommendation.",
        }

    rel_pct = f"{ns['relative_change'] * 100:+.1f}%"
    if ns["significant"] and ns["direction_positive"]:
        return {
            "verdict": "SHIP IT",
            "emoji": "🚀",
            "bg": "#f0fdf4", "border": "#10b981", "fg": "#065f46",
            "summary": f"Primary metric improved by {rel_pct} (p = {ns['p_value']:.3f}). All guardrails passed.",
            "detail": "The experiment achieved its goal with statistical confidence. Shipping is recommended.",
        }
    elif ns["significant"] and not ns["direction_positive"]:
        return {
            "verdict": "DON'T SHIP",
            "emoji": "🚫",
            "bg": "#fef2f2", "border": "#ef4444", "fg": "#b91c1c",
            "summary": f"Primary metric moved in the wrong direction by {rel_pct} (p = {ns['p_value']:.3f}).",
            "detail": "The treatment hurt the main metric. Keep users on the current experience.",
        }
    else:
        return {
            "verdict": "INCONCLUSIVE",
            "emoji": "🔄",
            "bg": "#fffbeb", "border": "#f59e0b", "fg": "#92400e",
            "summary": f"Primary metric change ({rel_pct}) is not statistically significant (p = {ns['p_value']:.3f}).",
            "detail": "We cannot confidently say whether the treatment helped or hurt. Run longer or increase traffic.",
        }
