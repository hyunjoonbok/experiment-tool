"""
Tool: Multiple Testing Correction
Bonferroni, Šidák, Holm-Bonferroni, and Benjamini-Hochberg methods for
controlling error rates when testing multiple metrics in one experiment.
"""


def bonferroni_threshold(alpha: float, n_tests: int) -> float:
    """Per-test alpha under Bonferroni: α/k. Controls FWER."""
    return alpha / n_tests


def sidak_threshold(alpha: float, n_tests: int) -> float:
    """Per-test alpha under Šidák: 1-(1-α)^(1/k). Controls FWER for independent tests."""
    return 1.0 - (1.0 - alpha) ** (1.0 / n_tests)


def holm_bonferroni(p_values: list, alpha: float) -> list:
    """
    Holm-Bonferroni step-down procedure. Controls FWER.
    More powerful than Bonferroni: applies a stricter threshold only to the most
    significant metric, relaxing progressively for less significant ones.

    Returns list of dicts in original metric order (not sorted by p-value).
    """
    k = len(p_values)
    order = sorted(range(k), key=lambda i: p_values[i])  # ascending p-value

    results = [None] * k
    reject_continues = True
    for step, orig_idx in enumerate(order):
        threshold = alpha / (k - step)
        p = p_values[orig_idx]
        if reject_continues and p <= threshold:
            rejected = True
        else:
            rejected = False
            reject_continues = False
        results[orig_idx] = {
            "metric_index": orig_idx + 1,
            "original_p": p,
            "adjusted_threshold": round(threshold, 6),
            "rejected": rejected,
        }
    return results


def benjamini_hochberg(p_values: list, alpha: float) -> list:
    """
    Benjamini-Hochberg step-up procedure. Controls FDR (not FWER).
    More permissive than FWER methods — accepts some false discoveries in exchange
    for detecting more true effects.

    Returns list of dicts in original metric order.
    """
    k = len(p_values)
    order = sorted(range(k), key=lambda i: p_values[i])  # ascending p-value

    # Find largest rank i where p_(i) <= (i/k) * alpha
    max_reject_rank = -1
    for step, orig_idx in enumerate(order):
        threshold = (step + 1) / k * alpha
        if p_values[orig_idx] <= threshold:
            max_reject_rank = step

    results = [None] * k
    for step, orig_idx in enumerate(order):
        threshold = (step + 1) / k * alpha
        results[orig_idx] = {
            "metric_index": orig_idx + 1,
            "original_p": p_values[orig_idx],
            "adjusted_threshold": round(threshold, 6),
            "rejected": step <= max_reject_rank,
        }
    return results


def apply_all_corrections(p_values: list, alpha: float) -> dict:
    """
    Apply all correction methods to observed p-values.
    Returns dict: {method_name: list[result_dict]}.
    Each result_dict: {metric_index, original_p, adjusted_threshold, rejected}.
    """
    k = len(p_values)
    bonfr_t = bonferroni_threshold(alpha, k)
    sidk_t = sidak_threshold(alpha, k)

    return {
        "No Correction": [
            {"metric_index": i + 1, "original_p": p, "adjusted_threshold": alpha, "rejected": p <= alpha}
            for i, p in enumerate(p_values)
        ],
        "Bonferroni": [
            {"metric_index": i + 1, "original_p": p, "adjusted_threshold": bonfr_t, "rejected": p <= bonfr_t}
            for i, p in enumerate(p_values)
        ],
        "Šidák": [
            {"metric_index": i + 1, "original_p": p, "adjusted_threshold": sidk_t, "rejected": p <= sidk_t}
            for i, p in enumerate(p_values)
        ],
        "Holm-Bonferroni": holm_bonferroni(p_values, alpha),
        "Benjamini-Hochberg (FDR)": benjamini_hochberg(p_values, alpha),
    }


def correction_threshold_curve(alpha: float, max_tests: int = 20) -> list:
    """
    Per-test threshold vs number of tests for Bonferroni and Šidák.
    Used to show how thresholds shrink as more metrics are tested.
    Returns list of dicts: {n_tests, method, threshold}.
    """
    rows = []
    for k in range(1, max_tests + 1):
        rows.append({"n_tests": k, "method": "No Correction", "threshold": alpha})
        rows.append({"n_tests": k, "method": "Bonferroni",    "threshold": round(bonferroni_threshold(alpha, k), 6)})
        rows.append({"n_tests": k, "method": "Šidák",         "threshold": round(sidak_threshold(alpha, k), 6)})
    return rows


def threshold_summary_table(alpha: float, n_tests: int) -> list:
    """
    Summary table for the current (alpha, n_tests) configuration.
    Returns list of dicts for st.dataframe display.
    """
    bonfr = bonferroni_threshold(alpha, n_tests)
    sidk = sidak_threshold(alpha, n_tests)
    # Holm: thresholds range from alpha/k (rank 1) to alpha (rank k)
    holm_min = alpha / n_tests
    # BH: thresholds range from alpha/k (rank 1) to alpha (rank k)
    bh_min = alpha / n_tests

    return [
        {
            "Method":          "No Correction",
            "Controls":        "—",
            "Per-test α":      f"{alpha:.4f}",
            "vs Uncorrected":  "—",
            "Use when":        "Exploratory; single primary metric",
        },
        {
            "Method":          "Bonferroni",
            "Controls":        "FWER",
            "Per-test α":      f"{bonfr:.5f}",
            "vs Uncorrected":  f"÷ {n_tests}",
            "Use when":        "Conservative; any number of tests",
        },
        {
            "Method":          "Šidák",
            "Controls":        "FWER",
            "Per-test α":      f"{sidk:.5f}",
            "vs Uncorrected":  f"÷ {n_tests} (less conservative)",
            "Use when":        "Independent tests; slightly more power than Bonferroni",
        },
        {
            "Method":          "Holm-Bonferroni",
            "Controls":        "FWER",
            "Per-test α":      f"{holm_min:.5f} – {alpha:.4f} (step-down)",
            "vs Uncorrected":  "Uniformly ≥ Bonferroni power",
            "Use when":        "Default FWER choice; always prefer over Bonferroni",
        },
        {
            "Method":          "Benjamini-Hochberg",
            "Controls":        "FDR",
            "Per-test α":      f"{bh_min:.5f} – {alpha:.4f} (step-up)",
            "vs Uncorrected":  "Most permissive; allows some false discoveries",
            "Use when":        "Exploratory multi-metric analysis; many tests (≥10)",
        },
    ]
