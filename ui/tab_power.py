"""
UI Tab 1: Advanced Power & MDE Simulator
"""

import streamlit as st
import pandas as pd
from tools.power_simulator import power_curve, sensitivity_heatmap, mde_for_power
from utils.charts import power_curve_chart, sensitivity_heatmap_chart


def render():
    st.header("Power & MDE Simulator")
    st.caption("Analytical + Monte Carlo engine for binary, continuous, and ratio metrics. Supports CUPED and clustering adjustments.")

    # ── Controls ─────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        metric_type = st.selectbox(
            "Metric Type",
            ["binary", "continuous", "ratio"],
            help="Binary: conversion/click. Continuous: revenue/time. Ratio: CTR = clicks/impressions.",
            key="pwr_metric_type",
        )
        if metric_type == "binary":
            baseline_mean = st.number_input("Baseline Conversion Rate", value=0.05, min_value=0.001, max_value=0.999, format="%.4f", key="pwr_baseline_mean_bin")
            baseline_std = float((baseline_mean * (1 - baseline_mean)) ** 0.5)
            st.caption(f"Auto std = sqrt(p·(1-p)) = **{baseline_std:.4f}**")
        else:
            baseline_mean = st.number_input("Baseline Mean", value=10.0, min_value=0.001, format="%.3f", key="pwr_baseline_mean")
            baseline_std = st.number_input("Baseline Std Dev", value=5.0, min_value=0.0001, format="%.3f", key="pwr_baseline_std")

    with col2:
        effect_size = st.slider("Treatment Effect (%)", 1, 50, 10, help="Relative lift over baseline", key="pwr_effect_size") / 100
        alpha = st.slider("Significance Level (α)", 0.01, 0.10, 0.05, step=0.01, key="pwr_alpha")
        target_power = st.slider("Target Power", 0.60, 0.99, 0.80, step=0.05, key="pwr_target_power")
        n_sim = st.select_slider(
            "MC Simulation Runs (ratio only)",
            options=[500, 1000, 2000, 5000],
            value=1000,
            help="Only used for ratio metrics. Binary/continuous use analytical formulas.",
            key="pwr_n_sim",
        )

    # ── Advanced Adjustments ─────────────────────────────
    with st.expander("CUPED & Clustering Adjustments", expanded=False):
        adj1, adj2 = st.columns(2)
        with adj1:
            r_squared = st.slider("CUPED R²", 0.0, 0.9, 0.0, step=0.05,
                                  help="Pre-experiment correlation. R²=0.5 → 50% variance reduction.",
                                  key="pwr_r_squared")
            st.caption(f"Variance multiplier: **{(1 - r_squared)**0.5:.3f}**")
        with adj2:
            icc = st.slider("Clustering ICC", 0.0, 0.3, 0.0, step=0.01,
                            help="Intra-cluster correlation for geo/team-level experiments.",
                            key="pwr_icc")
            cluster_size = st.number_input("Avg Cluster Size", min_value=1, value=50, step=10, key="pwr_cluster_size")
            if icc > 0:
                deff = 1 + (cluster_size - 1) * icc
                st.caption(f"Design effect: **{deff:.2f}x** — effective N ÷ {deff:.2f}")

    # ── Run Button ────────────────────────────────────────
    run = st.button("Run Simulation", type="primary", key="run_power")

    if run or "power_results" in st.session_state:
        if run:
            sample_sizes = list(range(100, 5001, 250))
            with st.spinner("Computing power curve..."):
                pc_data = power_curve(
                    metric_type=metric_type,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    effect_size=effect_size,
                    alpha=alpha,
                    n_sim=n_sim,
                    r_squared=r_squared,
                    icc=icc,
                    cluster_size=float(cluster_size),
                    sample_sizes=sample_sizes,
                )

            with st.spinner("Computing MDEs..."):
                mde_results = {
                    n: mde_for_power(metric_type, baseline_mean, baseline_std,
                                     target_power, alpha, n, r_squared, icc, float(cluster_size))
                    for n in [1000, 2000, 5000]
                }

            with st.spinner("Computing sensitivity heatmap..."):
                heatmap_data = sensitivity_heatmap(
                    metric_type=metric_type,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    effect_sizes=[0.05, 0.10, 0.15, 0.20, 0.30],
                    sample_sizes=[500, 1000, 2000, 3000, 5000],
                    alpha=alpha,
                    n_sim=n_sim,
                    r_squared=r_squared,
                    icc=icc,
                    cluster_size=float(cluster_size),
                )

            st.session_state["power_results"] = {
                "pc_data": pc_data,
                "mde_results": mde_results,
                "heatmap_data": heatmap_data,
                "target_power": target_power,
            }

        res = st.session_state["power_results"]
        pc_data = res["pc_data"]
        mde_results = res["mde_results"]
        heatmap_data = res["heatmap_data"]
        target_power_val = res["target_power"]

        st.subheader("Results")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("MDE @ n=1,000/arm", f"{mde_results[1000]:.1%}")
        mc2.metric("MDE @ n=2,000/arm", f"{mde_results[2000]:.1%}")
        mc3.metric("MDE @ n=5,000/arm", f"{mde_results[5000]:.1%}")

        st.altair_chart(power_curve_chart(pc_data, target_power_val), width="stretch")

        st.subheader("Sensitivity Heatmap")
        st.altair_chart(sensitivity_heatmap_chart(heatmap_data), width="stretch")

        with st.expander("Raw Data"):
            st.dataframe(pd.DataFrame(pc_data), width="stretch")
    else:
        st.info("Configure parameters above and click **Run Simulation**.")
