"""
UI Tab 2: Sequential Testing Simulator
"""

import streamlit as st
import pandas as pd
from tools.sequential_testing import alpha_spending_table, simulate_type1_inflation, simulate_power_sequential
from utils.charts import alpha_spending_chart, stopping_distribution_chart


def render():
    st.header("Sequential Testing Simulator")
    st.caption("Understand alpha inflation under repeated peeking and design valid stopping rules.")

    col1, col2 = st.columns(2)

    with col1:
        K = st.slider("Number of Interim Looks (K)", 2, 10, 5, key="seq_K")
        n_total = st.number_input("Total Sample Size (both arms)", min_value=200, value=5000, step=200, key="seq_n_total")
        alpha = st.slider("Nominal Alpha (α)", 0.01, 0.10, 0.05, step=0.01, key="seq_alpha")

    with col2:
        boundary = st.selectbox(
            "Boundary / Spending Function",
            ["obrien_fleming", "pocock", "fixed"],
            format_func=lambda x: {
                "obrien_fleming": "O'Brien-Fleming (conservative early, liberal late)",
                "pocock": "Pocock (equal boundaries at each look)",
                "fixed": "Fixed — no correction (naive peeking)",
            }[x],
            key="seq_boundary",
        )
        true_effect = st.slider("True Effect (Cohen's d, for power sim)", 0.05, 0.8, 0.2, step=0.05, key="seq_true_effect")
        n_sim = st.select_slider("Simulation Runs", options=[1000, 3000, 5000], value=3000, key="seq_n_sim")

    # ── Alpha Spending Table (always show — fast) ─────────
    st.divider()
    st.subheader("Alpha Spending Schedule")
    spending = alpha_spending_table(K, boundary, alpha)
    df_spending = pd.DataFrame(spending)
    st.dataframe(
        df_spending.style.format({
            "fraction_observed": "{:.1%}",
            "cumulative_alpha_spent": "{:.5f}",
            "incremental_alpha": "{:.5f}",
            "z_boundary": "{:.3f}",
        }),
        width="stretch",
    )
    st.altair_chart(alpha_spending_chart(spending), width="stretch")

    # ── Run Button ────────────────────────────────────────
    st.divider()
    run = st.button("Run Simulation", type="primary", key="run_seq")

    if run or "seq_results" in st.session_state:
        if run:
            with st.spinner("Simulating type I error under H₀..."):
                t1 = simulate_type1_inflation(K=K, n_total=n_total, alpha=alpha, boundary=boundary, n_sim=n_sim)
            with st.spinner("Simulating power under H₁..."):
                power_res = simulate_power_sequential(K=K, n_total=n_total, true_effect=true_effect,
                                                      alpha=alpha, boundary=boundary, n_sim=n_sim)
            st.session_state["seq_results"] = {"t1": t1, "power_res": power_res}

        res = st.session_state["seq_results"]
        t1 = res["t1"]
        power_res = res["power_res"]

        # ── Type I Error ──────────────────────────────────
        st.subheader("Type I Error Inflation")
        col_a, col_b = st.columns(2)
        delta = t1["empirical_type1_error"] - alpha
        col_a.metric("Empirical Type I Error", f"{t1['empirical_type1_error']:.3f}",
                     delta=f"{delta:+.3f} vs α={alpha}", delta_color="inverse")
        col_b.metric("Nominal Alpha", f"{alpha:.3f}")

        if boundary == "fixed":
            st.warning(
                f"With no correction and {K} peeks, your effective type I error is "
                f"**{t1['empirical_type1_error']:.3f}** vs nominal **{alpha}**."
            )
        else:
            st.success(
                f"The **{boundary.replace('_', '-').title()}** boundary controls type I error "
                f"at **{t1['empirical_type1_error']:.3f}** (target ≤ {alpha})."
            )

        # ── Power & Stopping ──────────────────────────────
        st.subheader("Power & Stopping Time")
        pc1, pc2 = st.columns(2)
        pc1.metric("Sequential Design Power", f"{power_res['power']:.3f}")
        pc2.metric("Expected Stopping Look", f"{power_res['expected_stopping_look']:.1f} / {K}")

        st.altair_chart(
            stopping_distribution_chart(power_res["looks"], power_res["stopping_look_distribution"]),
            width="stretch",
        )
    else:
        st.info("Configure parameters above and click **Run Simulation**.")

    with st.expander("Interpretation Guide"):
        st.markdown("""
        **O'Brien-Fleming**: Spends little alpha early — high bar to stop early, saves budget for final look. Best for preserving power.

        **Pocock**: Equal boundary at every look — more aggressive early stopping but lower final power.

        **Fixed (no correction)**: Each peek at α inflates the family-wise error rate.
        At 5 peeks with α=0.05, your real false positive rate can reach ~18%.
        """)
