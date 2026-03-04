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

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Numerator (e.g., Clicks)")
        mean_num = st.number_input("Mean (μ_num)", value=100.0, min_value=0.001, format="%.3f", key="rat_mean_num")
        var_num = st.number_input("Variance (σ²_num)", value=500.0, min_value=0.001, format="%.3f", key="rat_var_num")

        st.subheader("Denominator (e.g., Impressions)")
        mean_denom = st.number_input("Mean (μ_denom)", value=2000.0, min_value=0.001, format="%.3f", key="rat_mean_denom")
        var_denom = st.number_input("Variance (σ²_denom)", value=1000.0, min_value=0.001, format="%.3f", key="rat_var_denom")

    with col2:
        st.subheader("Covariance & Sample")
        max_cov = float((var_num * var_denom) ** 0.5 * 0.95)
        cov = st.number_input(
            "Covariance (Cov(num, denom))",
            value=0.0,
            min_value=-max_cov,
            max_value=max_cov,
            format="%.2f",
            help=f"Valid range: [{-max_cov:.1f}, {max_cov:.1f}]",
            key="rat_cov",
        )
        n = st.number_input("Sample Size (N)", value=10000, min_value=100, step=500, key="rat_n")
        n_boot = st.select_slider("Bootstrap Resamples", options=[500, 1000, 2000], value=1000, key="rat_n_boot")

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

        st.divider()
        st.subheader("Variance Decomposition")
        st.altair_chart(variance_decomposition_bar(decomp), width="stretch")
        decomp_df = pd.DataFrame(decomp)
        decomp_df.columns = ["Component", "Absolute Contribution", "% of Total"]
        st.dataframe(
            decomp_df.style.format({"Absolute Contribution": "{:.2e}", "% of Total": "{:.1f}%"}),
            width="stretch", hide_index=True,
        )

        st.divider()
        st.subheader("Traffic Shift Impact")
        st.altair_chart(traffic_shift_chart(shift_data), width="stretch")
    else:
        st.info("Configure parameters above and click **Run Analysis**.")

    with st.expander("Why does this matter?"):
        st.markdown("""
        **The delta method** linearizes the ratio Y/X, decomposing variance into three terms:

        1. **Numerator variance** — how much clicks vary
        2. **Denominator variance** — how much impressions vary
        3. **Covariance adjustment** — positive covariance *reduces* variance

        Using naive `Var(clicks)/n` typically **underestimates** variance → your experiment is underpowered.
        """)
