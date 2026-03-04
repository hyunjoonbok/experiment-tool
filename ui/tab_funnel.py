"""
UI Tab 8: Funnel Transition Simulator
"""

import streamlit as st
import pandas as pd
from tools.funnel_simulator import simulate_funnel, funnel_chart_data, cvr_comparison_data, sensitivity_sweep
from utils.charts import funnel_bar_chart, funnel_incremental_chart, sensitivity_heatmap_funnel

DEFAULT_STAGES = ["Impression", "Click", "Sign-up", "Activation", "Retention"]
DEFAULT_CVRS = [0.10, 0.30, 0.50, 0.60, 0.70]


def render():
    st.header("Funnel Transition Simulator")
    st.caption(
        "Model multi-stage funnel behavior under a treatment uplift. "
        "See net MAU impact, revenue delta, and sensitivity across uplift × decay combinations."
    )

    # ── Funnel Definition ─────────────────────────────────
    st.subheader("Funnel Definition")

    n_stages = st.slider("Number of Stages", 2, 7, 5, key="fun_n_stages")
    stages = DEFAULT_STAGES[:n_stages]
    default_cvrs = DEFAULT_CVRS[:n_stages]

    stage_cols = st.columns(n_stages)
    stage_names = []
    baseline_cvrs = []
    for i, col in enumerate(stage_cols):
        with col:
            name = col.text_input(f"Stage {i+1}", value=stages[i], key=f"stage_{i}")
            cvr = col.number_input(
                "CVR (%)", min_value=0.1, max_value=100.0,
                value=default_cvrs[i] * 100, step=1.0, key=f"cvr_{i}",
                format="%.1f",
            ) / 100
            stage_names.append(name)
            baseline_cvrs.append(cvr)

    st.divider()

    # ── Treatment Parameters ───────────────────────────────
    st.subheader("Treatment Parameters")
    col1, col2 = st.columns(2)

    with col1:
        top_n = st.number_input("Top-of-Funnel Users", min_value=1000, value=100_000, step=10_000, key="fun_top_n")
        treatment_stage = st.selectbox(
            "Stage Where Treatment is Applied",
            options=list(range(n_stages)),
            format_func=lambda i: f"Stage {i+1}: {stage_names[i]}",
            key="fun_treatment_stage",
        )
        treatment_uplift = st.slider("Treatment Uplift at Stage (%)", 1, 50, 10, key="fun_uplift") / 100

    with col2:
        downstream_decay = st.slider(
            "Downstream Uplift Retention (%)",
            10, 100, 80, step=5,
            help="What % of the uplift carries through to the next stage. 100% = full carry-through.",
            key="fun_decay",
        ) / 100
        retention_multiplier = st.slider(
            "Final Retention Multiplier",
            0.5, 2.0, 1.0, step=0.05,
            help="Multiplier on bottom-of-funnel MAU (accounts for long-term retention effects)",
            key="fun_retention_mult",
        )
        spillover = st.slider(
            "Spillover to Adjacent Stage (%)",
            -20, 20, 0, step=1,
            help="Positive = boost to stage before treatment. Negative = cannibalization.",
            key="fun_spillover",
        ) / 100
        revenue_per_user = st.number_input("Revenue per MAU ($)", value=10.0, min_value=0.0, format="%.2f", key="fun_revenue")

    st.divider()
    run = st.button("Run Simulation", type="primary", key="run_funnel")

    if run or "funnel_results" in st.session_state:
        if run:
            result = simulate_funnel(
                stage_names=stage_names,
                baseline_cvrs=baseline_cvrs,
                top_of_funnel_n=top_n,
                treatment_stage=treatment_stage,
                treatment_uplift=treatment_uplift,
                downstream_decay=downstream_decay,
                retention_multiplier=retention_multiplier,
                spillover_effect=spillover,
                revenue_per_user=revenue_per_user,
            )
            sweep = sensitivity_sweep(
                stage_names=stage_names,
                baseline_cvrs=baseline_cvrs,
                top_of_funnel_n=top_n,
                treatment_stage=treatment_stage,
                treatment_uplifts=[0.05, 0.10, 0.15, 0.20, 0.30],
                downstream_decays=[0.50, 0.60, 0.70, 0.80, 0.90, 1.00],
                revenue_per_user=revenue_per_user,
            )
            st.session_state["funnel_results"] = {"result": result, "sweep": sweep}

        res = st.session_state["funnel_results"]
        result = res["result"]
        sweep = res["sweep"]

        # ── Summary Metrics ───────────────────────────────
        st.subheader("Impact Summary")
        m1, m2, m3 = st.columns(3)
        delta_color = "normal" if result.net_mau_delta >= 0 else "inverse"
        m1.metric("Net MAU Delta", f"{result.net_mau_delta:+,.0f}",
                  delta=f"{result.net_mau_delta_pct:+.2f}%", delta_color=delta_color)
        m2.metric("Revenue Delta", f"${result.revenue_delta:+,.0f}",
                  delta=f"{result.revenue_delta_pct:+.2f}%", delta_color=delta_color)
        m3.metric("Treatment Stage", f"{stage_names[treatment_stage]} (+{treatment_uplift:.0%})")

        st.divider()

        # ── Funnel Volumes ────────────────────────────────
        st.subheader("Funnel Volumes")
        st.altair_chart(funnel_bar_chart(funnel_chart_data(result)), width="stretch")

        # ── Incremental Users ─────────────────────────────
        st.subheader("Incremental Users per Stage")
        st.altair_chart(
            funnel_incremental_chart(result.stage_names, result.incremental_users_per_stage),
            width="stretch",
        )

        # ── CVR Table ─────────────────────────────────────
        st.subheader("CVR Comparison")
        cvr_df = pd.DataFrame({
            "Stage": stage_names,
            "Baseline CVR": [f"{c:.2%}" for c in result.baseline_cvrs],
            "Treatment CVR": [f"{c:.2%}" for c in result.treated_cvrs],
            "CVR Δ (pp)": [f"{(t-b)*100:+.2f}" for t, b in zip(result.treated_cvrs, result.baseline_cvrs)],
            "Baseline Users": [f"{v:,.0f}" for v in result.baseline_volumes],
            "Treatment Users": [f"{v:,.0f}" for v in result.treated_volumes],
            "Incremental": [f"{i:+,.0f}" for i in result.incremental_users_per_stage],
        })
        st.dataframe(cvr_df, width="stretch", hide_index=True)

        st.divider()

        # ── Sensitivity Heatmap ───────────────────────────
        st.subheader("Sensitivity: Net MAU Δ% (Uplift × Decay)")
        st.caption("How robust is the impact estimate to assumptions about treatment strength and decay?")
        st.altair_chart(sensitivity_heatmap_funnel(sweep), width="stretch")

        with st.expander("Sensitivity Table"):
            st.dataframe(
                pd.DataFrame(sweep).style.format({
                    "net_mau_delta": "{:,.0f}",
                    "net_mau_delta_pct": "{:.2f}%",
                    "revenue_delta": "${:,.0f}",
                }),
                width="stretch", hide_index=True,
            )
    else:
        st.info("Configure your funnel above and click **Run Simulation**.")
