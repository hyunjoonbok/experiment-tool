"""
UI Tab 9: Multiple Testing Correction
"""

import streamlit as st
import pandas as pd
from tools.multiple_testing import (
    apply_all_corrections,
    correction_threshold_curve,
    threshold_summary_table,
    bonferroni_threshold,
    sidak_threshold,
)
from utils.charts import correction_threshold_chart, rejection_heatmap_chart


_METHOD_ORDER = [
    "No Correction",
    "Bonferroni",
    "Šidák",
    "Holm-Bonferroni",
    "Benjamini-Hochberg (FDR)",
]


def render():
    st.header("Multiple Testing Correction")
    st.caption(
        "When testing several metrics in one experiment, uncorrected p-values inflate your false positive rate. "
        "This tool shows you the right alpha threshold to use for each metric."
    )

    with st.expander("📖 The multiple testing problem — click to learn more", expanded=False):
        st.markdown("""
        ### Why you can't test 5 metrics at α = 0.05 each

        Suppose you run **one** test and set α = 0.05. The probability of a false positive is 5%.

        Now suppose you test **5 independent metrics**, each at α = 0.05.
        The probability that **at least one** is a false positive is:

        > 1 − (1 − 0.05)⁵ = **22.6%**

        With 10 metrics: **40.1%** — nearly a coin flip for getting at least one false winner.

        ---
        ### The four correction methods

        | Method | Controls | Power | When to use |
        |--------|----------|-------|-------------|
        | **Bonferroni** | FWER | Lowest | Any number of tests; simplest to explain |
        | **Šidák** | FWER | Slightly > Bonferroni | Independent tests; more accurate than Bonferroni |
        | **Holm-Bonferroni** | FWER | Higher than Bonferroni | Default FWER choice; always dominates Bonferroni |
        | **Benjamini-Hochberg** | FDR | Highest | Many metrics (≥ 10); exploratory; acceptable to have some false discoveries |

        **FWER** (Family-Wise Error Rate) = probability of **any** false positive among all tests.
        **FDR** (False Discovery Rate) = expected **fraction** of rejections that are false positives.

        ---
        ### Which method should I use?

        - **Primary metric + a few guardrails (2–5 metrics):** Holm-Bonferroni. It's strictly more
          powerful than Bonferroni while controlling the same FWER guarantee.
        - **Many exploratory metrics (≥ 10):** Benjamini-Hochberg. You're willing to accept a small
          fraction of false discoveries in exchange for detecting more real effects.
        - **Regulatory / high-stakes decisions:** Bonferroni. Conservative, easy to defend, no
          assumptions about test correlation.
        - **Never use "No Correction" for multi-metric experiments** — it guarantees inflated false
          positives.

        ---
        ### What about correlated metrics?

        Bonferroni and BH both work whether metrics are correlated or not (they are conservative for
        positively correlated tests). Šidák assumes independence; it can be anti-conservative if metrics
        are negatively correlated (unusual in practice). Holm also controls FWER under any dependence structure.
        """)

    # ── Inputs ────────────────────────────────────────────────────────────────
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        n_metrics = st.slider(
            "Number of Metrics Tested",
            min_value=2, max_value=20, value=5,
            help=(
                "How many metrics are you testing simultaneously in this experiment? "
                "Include all metrics you plan to inspect for significance — primary, secondary, and guardrails. "
                "The more metrics you test, the stricter the correction needs to be."
            ),
            key="mtc_n_metrics",
        )
        alpha = st.slider(
            "Family-wise Alpha (α)",
            min_value=0.01, max_value=0.10, value=0.05, step=0.01,
            help=(
                "The overall false positive rate you want to control across ALL your metrics. "
                "Standard is 0.05. The correction methods distribute this budget across your k metrics."
            ),
            key="mtc_alpha",
        )

    with col2:
        enter_pvals = st.checkbox(
            "Enter observed p-values to see rejections",
            value=False,
            key="mtc_enter_pvals",
            help=(
                "Optional: enter the p-values from your experiment to see exactly which metrics "
                "would be declared significant under each correction method."
            ),
        )
        if enter_pvals:
            pval_input = st.text_area(
                f"P-values (one per line, {n_metrics} total)",
                value="\n".join(["0.032", "0.18", "0.004", "0.051", "0.12"][:n_metrics]),
                height=150,
                help="Enter each p-value on its own line. Values must be between 0 and 1.",
                key="mtc_pval_input",
            )
        metric_labels_raw = st.text_area(
            f"Metric names (one per line, {n_metrics} total) — optional",
            value="\n".join([f"Metric {i+1}" for i in range(n_metrics)]),
            height=100,
            key="mtc_metric_labels",
            help="Label each metric for the rejection chart. If left generic, 'Metric 1', 'Metric 2', etc. are used.",
        )

    # Parse metric labels
    raw_labels = [ln.strip() for ln in metric_labels_raw.strip().splitlines() if ln.strip()]
    metric_labels = (raw_labels + [f"Metric {i+1}" for i in range(n_metrics)])[:n_metrics]

    # ── Threshold Summary Table ────────────────────────────────────────────────
    st.divider()
    st.subheader("Adjusted Alpha Thresholds")
    st.caption(
        f"With **{n_metrics} metrics** at family-wise α = {alpha}, each correction method sets the following "
        "per-test thresholds. Use these thresholds when checking each metric's p-value."
    )

    summary = threshold_summary_table(alpha, n_metrics)
    df_summary = pd.DataFrame(summary)
    st.dataframe(df_summary, width="stretch", hide_index=True)

    # ── Threshold Shrinkage Chart ─────────────────────────────────────────────
    st.divider()
    st.subheader("How Thresholds Shrink as You Test More Metrics")
    st.caption(
        "The x-axis shows the number of metrics tested simultaneously. "
        "The y-axis shows the per-test alpha threshold — the value each individual p-value must beat. "
        "The vertical line marks your current setting."
    )

    curve_rows = correction_threshold_curve(alpha, max_tests=20)
    st.altair_chart(correction_threshold_chart(curve_rows, n_metrics), width="stretch")

    with st.expander("📊 How to read this chart", expanded=False):
        bonfr_now = bonferroni_threshold(alpha, n_metrics)
        sidk_now = sidak_threshold(alpha, n_metrics)
        st.markdown(f"""
        **At your current setting ({n_metrics} metrics, α={alpha}):**
        - **No Correction:** use α = {alpha:.4f} for each test → but your family-wise error rate is actually
          {1-(1-alpha)**n_metrics:.1%} (the true probability of at least one false positive)
        - **Bonferroni:** use α = {bonfr_now:.5f} for each test — the simplest correction
        - **Šidák:** use α = {sidk_now:.5f} — marginally less conservative than Bonferroni

        **Why does the curve flatten?** The denominator grows linearly but the threshold is already very small.
        Going from 10→15 metrics reduces Bonferroni from {bonferroni_threshold(alpha,10):.4f} to
        {bonferroni_threshold(alpha,15):.4f} — a much smaller absolute change than going from 1→5 metrics.

        **Business implication:** Adding more guardrail metrics to your experiment is not "free" —
        each additional metric tightens the threshold needed for your primary metric to be declared significant.
        """)

    # ── P-value Analysis ──────────────────────────────────────────────────────
    if enter_pvals:
        st.divider()
        st.subheader("Rejection Analysis")

        # Parse p-values
        p_values = []
        pval_errors = []
        for i, line in enumerate(pval_input.strip().splitlines()):
            line = line.strip()
            try:
                v = float(line)
                if not (0 <= v <= 1):
                    pval_errors.append(f"Line {i+1}: '{line}' is not between 0 and 1")
                else:
                    p_values.append(v)
            except ValueError:
                if line:
                    pval_errors.append(f"Line {i+1}: '{line}' is not a valid number")

        if pval_errors:
            st.error("Fix these input errors:\n" + "\n".join(pval_errors))
        elif len(p_values) == 0:
            st.info("Enter at least one p-value above.")
        else:
            # Pad or trim to n_metrics
            if len(p_values) < n_metrics:
                st.warning(
                    f"Only {len(p_values)} p-values entered for {n_metrics} metrics. "
                    "Using the values you provided."
                )
            p_values = p_values[:n_metrics]
            k_actual = len(p_values)
            labels_actual = metric_labels[:k_actual]

            all_results = apply_all_corrections(p_values, alpha)

            # ── Rejection counts per method ───────────────────────────────
            st.caption(
                "The table below shows the number of significant metrics under each correction. "
                "The heatmap shows exactly which metrics are rejected (green) or not (red) — "
                "p-values are shown inside each cell."
            )

            count_rows = []
            for method in _METHOD_ORDER:
                results = all_results[method]
                n_rejected = sum(1 for r in results if r["rejected"])
                rejection_names = [
                    labels_actual[r["metric_index"] - 1]
                    for r in results if r["rejected"]
                ]
                count_rows.append({
                    "Method": method,
                    "Significant Metrics": n_rejected,
                    "Rejected": ", ".join(rejection_names) if rejection_names else "—",
                })

            df_counts = pd.DataFrame(count_rows)
            # Highlight the row with most rejections (best power) vs fewest
            max_rej = df_counts["Significant Metrics"].max()

            def highlight_count(row):
                if row["Method"] == "No Correction":
                    return ["background-color: #f1f5f9"] * len(row)
                if row["Significant Metrics"] == max_rej and max_rej > 0:
                    return ["background-color: #d1fae5"] * len(row)
                return [""] * len(row)

            st.dataframe(
                df_counts.style.apply(highlight_count, axis=1),
                width="stretch",
                hide_index=True,
            )

            # ── Rejection Heatmap ─────────────────────────────────────────
            st.altair_chart(
                rejection_heatmap_chart(all_results, labels_actual),
                width="stretch",
            )

            # ── Per-metric detail ─────────────────────────────────────────
            with st.expander("Per-metric detail table", expanded=False):
                detail_rows = []
                for method in _METHOD_ORDER:
                    for r in all_results[method]:
                        idx = r["metric_index"] - 1
                        detail_rows.append({
                            "Method": method,
                            "Metric": labels_actual[idx] if idx < len(labels_actual) else f"M{r['metric_index']}",
                            "p-value": r["original_p"],
                            "Threshold": r["adjusted_threshold"],
                            "Decision": "Reject H₀ ✓" if r["rejected"] else "Fail to reject",
                        })
                df_detail = pd.DataFrame(detail_rows)
                st.dataframe(
                    df_detail.style.format({"p-value": "{:.4f}", "Threshold": "{:.5f}"}),
                    width="stretch",
                    hide_index=True,
                )

            # ── Interpretation ────────────────────────────────────────────
            with st.expander("📊 What do these results mean?", expanded=False):
                holm_rej = sum(1 for r in all_results["Holm-Bonferroni"] if r["rejected"])
                bh_rej = sum(1 for r in all_results["Benjamini-Hochberg (FDR)"] if r["rejected"])
                no_rej = sum(1 for r in all_results["No Correction"] if r["rejected"])

                st.markdown(f"""
                **Without correction:** {no_rej} metric(s) look significant at α={alpha}.
                But with {k_actual} simultaneous tests, the true family-wise false positive rate is
                {1-(1-alpha)**k_actual:.1%} — meaning there's a {1-(1-alpha)**k_actual:.0%} chance
                at least one of those "significant" results is a false positive.

                **After Holm-Bonferroni:** {holm_rej} metric(s) survive. These are the metrics you
                can confidently call significant while controlling the probability of **any** false
                positive to ≤ {alpha:.0%}.

                **After Benjamini-Hochberg:** {bh_rej} metric(s) survive. This method controls the
                *rate* of false discoveries (expected to be ≤ {alpha:.0%} of declared significant
                results), not the probability of any single false positive. It will typically reject
                more hypotheses than Holm-Bonferroni.

                **Recommended decision rule for this experiment:**
                - Use **Holm-Bonferroni** if you need to confidently claim each significant metric
                  is a real effect (regulatory, high-stakes, or public-facing decisions).
                - Use **Benjamini-Hochberg** if you're exploring which of many metrics to follow
                  up on in future experiments (direction-finding, not shipping decisions).
                """)

    # ── Always-on guidance ────────────────────────────────────────────────────
    st.divider()
    with st.expander("Practical guidelines for product experiments", expanded=False):
        st.markdown("""
        ### How to set up a multi-metric experiment correctly

        **1. Pre-specify your metric hierarchy before the experiment starts:**
        - **Primary metric (1):** The single decision metric. Use Holm-Bonferroni threshold.
        - **Secondary metrics (2–5):** Supporting evidence. Apply corrections across this group.
        - **Guardrail metrics:** Tested for harm only (one-sided). Apply corrections separately.

        **2. Don't add metrics retrospectively.** Adding metrics after seeing the data resets
        the multiple testing problem — you've effectively increased k without adjusting thresholds.

        **3. Correlated metrics need less correction, but it's conservative to apply it anyway.**
        If revenue and conversion are highly correlated, treating them as independent (as Bonferroni
        does) is overly conservative. However, underestimating correlation is risky — use the
        conservative method unless you have strong prior knowledge of the correlation structure.

        **4. The "10 metrics" mental model:**
        At α=0.05, Bonferroni with 10 metrics requires p < 0.005 for each test. If your effects
        are real but modest (p ~ 0.02), you'll fail Bonferroni but pass BH. This is the signal
        to run a confirmatory experiment with fewer, pre-specified metrics.

        **5. Interaction between multiple testing and sequential testing:**
        If you are also using sequential testing (interim looks), apply the alpha-spending boundary
        threshold *after* the multiple testing correction. For example, at an interim look with
        OBF boundary z=3.0 (≈ p=0.003), apply that as the family-wise threshold, then divide
        further by Bonferroni for k metrics.

        ### References
        - Holm (1979): "A Simple Sequentially Rejective Multiple Test Procedure" — *Scandinavian Journal of Statistics*
        - Benjamini & Hochberg (1995): "Controlling the False Discovery Rate" — *JRSSB*
        - Kohavi et al. (2020): *Trustworthy Online Controlled Experiments* — Chapter 17 (Multiple Testing)
        """)
