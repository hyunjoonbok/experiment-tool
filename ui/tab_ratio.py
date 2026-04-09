"""
UI Tab 3: Ratio Metric Variance Decomposition Tool
"""

import streamlit as st
import pandas as pd
from tools.ratio_variance import (
    delta_method_variance,
    bootstrap_variance,
    traffic_shift_impact,
    variance_decomposition_chart_data,
)
from utils.charts import variance_decomposition_bar, traffic_shift_chart


def render():
    st.header("Ratio Metric Variance Decomposition")
    st.caption(
        "Understand why your power calculation is wrong for CTR/CVR-type metrics. "
        "Uses the delta method and bootstrap to decompose variance."
    )

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **What is a ratio metric?** A ratio metric is any metric of the form numerator ÷ denominator.
        Common examples: CTR = clicks / impressions, CVR = conversions / sessions,
        revenue per visit = revenue / visits. These are among the most common primary metrics in product experiments.

        **Why naive variance is wrong:** Standard power calculators assume your metric is a simple mean.
        For ratio metrics, this is mathematically incorrect — the variance of Y/X depends on the variance
        of both components *and* their covariance. Using naive variance leads to miscalibrated sample sizes:
        you may run an underpowered experiment and miss real effects.

        **What the delta method does:** It uses a first-order Taylor expansion to analytically decompose
        ratio variance into three additive terms: numerator variance, denominator variance, and a
        covariance adjustment. This gives you the correct standard error for power calculations.

        **When to use this tool:** Before any experiment where your primary metric is a ratio.
        Plug in historical estimates of mean and variance for numerator and denominator, then use
        the resulting Delta SE in your sample size formula.

        **How to interpret the main result:** The Delta/Bootstrap ratio tells you how reliable the
        analytical formula is. A value close to 1.0 means the delta method is accurate for your metric.
        Use the Delta SE in downstream power calculations.
        """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Numerator (e.g., Clicks)")
        mean_num = st.number_input(
            "Mean (μ_num)",
            value=100.0,
            min_value=0.001,
            format="%.3f",
            help="Average value of the numerator per user or session. For CTR, this is average clicks per user. Estimate from historical data. Typical range: 1–500 depending on your product surface.",
            key="rat_mean_num",
        )
        var_num = st.number_input(
            "Variance (σ²_num)",
            value=500.0,
            min_value=0.001,
            format="%.3f",
            help="Variance of the numerator across users. Higher variance means wider confidence intervals and requires larger samples. Estimate from historical logs using np.var(). Typical range: 10–100,000.",
            key="rat_var_num",
        )

        st.subheader("Denominator (e.g., Impressions)")
        mean_denom = st.number_input(
            "Mean (μ_denom)",
            value=2000.0,
            min_value=0.001,
            format="%.3f",
            help="Average value of the denominator per user or session. For CTR, this is average impressions per user. Should typically be larger than mean_num. Estimate from historical data.",
            key="rat_mean_denom",
        )
        var_denom = st.number_input(
            "Variance (σ²_denom)",
            value=1000.0,
            min_value=0.001,
            format="%.3f",
            help="Variance of the denominator across users. Contributes to ratio variance through the squared ratio term. High denominator variance amplifies total variance. Estimate from logs.",
            key="rat_var_denom",
        )

    with col2:
        st.subheader("Covariance & Sample")
        max_cov = float((var_num * var_denom) ** 0.5 * 0.95)
        cov = st.number_input(
            "Covariance (Cov(num, denom))",
            value=0.0,
            min_value=-max_cov,
            max_value=max_cov,
            format="%.2f",
            help=f"How much numerator and denominator co-vary per user. Positive covariance (users with more impressions also click more) REDUCES ratio variance. Negative covariance increases it. Valid range: [{-max_cov:.1f}, {max_cov:.1f}]. Estimate with np.cov().",
            key="rat_cov",
        )
        n = st.number_input(
            "Sample Size (N)",
            value=10000,
            min_value=100,
            step=500,
            help="Number of users or sessions in one experiment arm. Variance scales as 1/N — doubling N halves variance. Use this to explore how many users you need. Typical range: 1,000–1,000,000.",
            key="rat_n",
        )
        n_boot = st.select_slider(
            "Bootstrap Resamples",
            options=[500, 1000, 2000],
            value=1000,
            help="Number of bootstrap iterations for the simulation-based variance estimate. More resamples = more accurate but slower. 1,000 is a good default. Use 2,000 when the delta/bootstrap ratio is far from 1.0.",
            key="rat_n_boot",
        )

    implied_ratio = mean_num / mean_denom
    st.info(f"Implied ratio (μ_num / μ_denom): **{implied_ratio:.5f}** — this is your metric value (e.g., CTR)")

    run = st.button("Run Analysis", type="primary", key="run_ratio")

    if run or "ratio_results" in st.session_state:
        if run:
            delta = delta_method_variance(mean_num, var_num, mean_denom, var_denom, cov, int(n))
            with st.spinner("Running bootstrap..."):
                boot = bootstrap_variance(mean_num, var_num, mean_denom, var_denom, cov, int(n), n_boot)
            decomp = variance_decomposition_chart_data(mean_num, var_num, mean_denom, var_denom, cov, int(n))
            shifts = [-50, -25, -10, 0, 10, 25, 50, 100]
            shift_data = traffic_shift_impact(mean_num, var_num, mean_denom, var_denom, cov, int(n), shifts)
            st.session_state["ratio_results"] = {
                "delta": delta, "boot": boot, "decomp": decomp, "shift_data": shift_data
            }

        res = st.session_state["ratio_results"]
        delta = res["delta"]
        boot = res["boot"]
        decomp = res["decomp"]
        shift_data = res["shift_data"]

        st.divider()
        st.subheader("Variance Estimates")
        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("Delta Method Variance", f"{delta['total_variance']:.2e}")
        rc2.metric("Bootstrap Variance", f"{boot['bootstrap_variance']:.2e}")
        rc3.metric("Delta / Bootstrap Ratio",
                   f"{boot['delta_vs_bootstrap_ratio']:.3f}" if boot["delta_vs_bootstrap_ratio"] else "N/A")

        rc4, rc5, rc6 = st.columns(3)
        rc4.metric("Delta SE", f"{delta['std_error']:.6f}")
        rc5.metric("Bootstrap SE", f"{boot['bootstrap_std_error']:.6f}")
        rc6.metric("95% CI for Ratio", f"[{boot['ci_95_low']:.5f}, {boot['ci_95_high']:.5f}]")

        ratio_val = boot["delta_vs_bootstrap_ratio"]
        if ratio_val is not None:
            if 0.9 <= ratio_val <= 1.1:
                st.info(
                    f"**Delta/Bootstrap ratio = {ratio_val:.3f}** — Close to 1.0. The analytical delta method "
                    "formula is reliable for this metric. You can safely use the **Delta SE** in your "
                    "sample size / power calculations."
                )
            elif 0.8 <= ratio_val <= 1.2:
                st.warning(
                    f"**Delta/Bootstrap ratio = {ratio_val:.3f}** — Moderate deviation from 1.0. The ratio metric "
                    "may have mild non-normality or skew. Use the **Bootstrap SE** for power calculations "
                    "to be conservative."
                )
            else:
                st.error(
                    f"**Delta/Bootstrap ratio = {ratio_val:.3f}** — Large deviation from 1.0. The linearization "
                    "assumption of the delta method is violated — the metric is likely heavily skewed or "
                    "has extreme outliers. Use the Bootstrap SE and consider log-transforming the metric "
                    "or using a non-parametric test."
                )

        st.caption(
            "**Delta SE** is the standard error you should plug into your sample size formula instead of "
            "the naive SE. The **95% CI for Ratio** shows the sampling variability of the baseline metric "
            "estimate itself — it is not a treatment effect confidence interval."
        )

        st.divider()
        st.subheader("Variance Decomposition")
        st.altair_chart(variance_decomposition_bar(decomp), width="stretch")
        decomp_df = pd.DataFrame(decomp)
        decomp_df.columns = ["Component", "Absolute Contribution", "% of Total"]
        st.dataframe(
            decomp_df.style.format({"Absolute Contribution": "{:.2e}", "% of Total": "{:.1f}%"}),
            width="stretch", hide_index=True,
        )

        if len(decomp_df) > 0:
            dominant = decomp_df.loc[decomp_df["% of Total"].idxmax(), "Component"]
            dominant_pct = decomp_df["% of Total"].max()
            st.caption(
                f"The dominant variance component is **{dominant}** ({dominant_pct:.1f}% of total variance). "
                "If **numerator variance** dominates: focus variance reduction techniques (e.g., CUPED) on "
                "the numerator variable. If **covariance** dominates and is positive: your metric is "
                "lower-variance than naive estimates suggest — you may need fewer samples than expected. "
                "If **denominator variance** dominates: consider whether you can reduce exposure variability."
            )

        st.divider()
        st.subheader("Traffic Shift Impact")
        st.altair_chart(traffic_shift_chart(shift_data), width="stretch")

        st.info(
            "**How to use this chart for experiment sizing:** The x-axis shows % change in traffic volume "
            "relative to your current N. The y-axis shows how the standard error (SE) changes. "
            "SE drops as traffic increases following a 1/√N relationship. Find the traffic level where SE "
            "is small enough to detect your minimum detectable effect (MDE). If SE drops sharply with a "
            "moderate traffic increase (e.g., +25%), a longer ramp or broader eligibility criteria will "
            "meaningfully improve experiment sensitivity."
        )

    else:
        st.info("Configure parameters above and click **Run Analysis**.")

    with st.expander("Why does this matter?"):
        st.markdown("""
        **The delta method** linearizes the ratio Y/X, decomposing variance into three terms:

        1. **Numerator variance** — how much clicks (or numerator) vary per user
        2. **Denominator variance** — how much impressions (or denominator) vary per user
        3. **Covariance adjustment** — positive covariance *reduces* variance; negative covariance *increases* it

        The direction of the error depends on the covariance:
        - **Zero or negative covariance**: naive `Var(numerator)/N` underestimates ratio variance → your experiment is underpowered if you use it.
        - **Large positive covariance**: the delta method variance can be *smaller* than naive variance — users with high impressions also have high clicks, reducing the ratio's uncertainty.

        **Always compute the delta method variance.** Do not assume direction. The covariance term is often the dominant factor.

        > The 95% CI displayed in the results describes the *sampling variability of the ratio estimator* — it is not an experiment treatment effect CI.
        """)
