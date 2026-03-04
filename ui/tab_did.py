"""
UI Tab 7: DiD & Synthetic Control Simulator
"""

import streamlit as st
import pandas as pd
from tools.did_simulator import simulate_did, bias_vs_violation, power_vs_n, pre_trend_data
from utils.charts import did_trajectory_chart, bias_violation_chart, did_power_chart


def render():
    st.header("DiD & Synthetic Control Simulator")
    st.caption(
        "Simulate bias, power, and CI coverage under varying parallel trend violations, "
        "noise levels, and sample sizes."
    )

    col1, col2 = st.columns(2)

    with col1:
        n_units = st.slider("Number of Units (treated + control)", 10, 200, 50, step=10, key="did_n_units")
        n_pre = st.slider("Pre-period Length (periods)", 2, 20, 8, key="did_n_pre")
        n_post = st.slider("Post-period Length (periods)", 1, 12, 4, key="did_n_post")
        alpha = st.slider("Significance Level (α)", 0.01, 0.10, 0.05, step=0.01, key="did_alpha")

    with col2:
        true_effect = st.number_input("True Treatment Effect", value=1.0, format="%.2f",
                                      help="Magnitude of the true causal effect", key="did_true_effect")
        noise = st.slider("Noise Level (σ)", 0.1, 5.0, 1.0, step=0.1,
                          help="Standard deviation of the error term", key="did_noise")
        trend_violation = st.slider(
            "Pre-trend Violation Magnitude",
            0.0, 3.0, 0.0, step=0.1,
            help="How much the treated group trends differently in the pre-period (0 = perfect parallel trends)",
            key="did_trend_violation",
        )
        n_sim = st.select_slider("Simulation Runs", options=[500, 1000, 2000], value=500, key="did_n_sim")

    st.divider()
    run = st.button("Run Simulation", type="primary", key="run_did")

    if run or "did_results" in st.session_state:
        if run:
            with st.spinner("Simulating DiD..."):
                main_result = simulate_did(
                    n_units, n_pre, n_post, true_effect, noise, trend_violation, n_sim, alpha
                )
            with st.spinner("Computing bias vs violation curve..."):
                violations = [0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
                bias_data = bias_vs_violation(n_units, n_pre, n_post, true_effect, noise, violations, n_sim)

            with st.spinner("Computing power curve..."):
                n_units_list = [10, 20, 30, 50, 75, 100, 150, 200]
                power_data = power_vs_n(n_units_list, n_pre, n_post, true_effect, noise, trend_violation, n_sim, alpha)

            with st.spinner("Generating pre-trend trajectories..."):
                traj_data = pre_trend_data(
                    min(n_units, 40), n_pre, true_effect, noise,
                    trend_violations=[0.0, 0.5, 1.0],
                    n_post=n_post,
                )

            st.session_state["did_results"] = {
                "main": main_result,
                "bias_data": bias_data,
                "power_data": power_data,
                "traj_data": traj_data,
                "true_effect": true_effect,
            }

        res = st.session_state["did_results"]
        main_result = res["main"]

        # ── Key Metrics ───────────────────────────────────
        st.subheader("Results")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("True Effect", f"{main_result.true_effect:.3f}")
        m2.metric("Estimated Effect", f"{main_result.estimated_effect:.3f}",
                  delta=f"Bias: {main_result.bias:+.3f}")
        m3.metric("Power", f"{main_result.power:.3f}")
        m4.metric("CI Coverage", f"{main_result.covers_truth}",
                  help=f"95% CI: [{main_result.ci_low:.3f}, {main_result.ci_high:.3f}]")

        if abs(main_result.bias_pct) > 20:
            st.error(
                f"Parallel trend violation causes **{main_result.bias_pct:.1f}%** bias in the DiD estimate. "
                "Consider a sensitivity analysis or alternative design."
            )
        elif abs(main_result.bias_pct) > 5:
            st.warning(f"Moderate bias detected: **{main_result.bias_pct:.1f}%** of true effect.")
        else:
            st.success(f"Bias is small (**{main_result.bias_pct:.1f}%**). Parallel trends assumption plausible.")

        st.divider()

        # ── Trajectory Chart ──────────────────────────────
        st.subheader("Pre/Post Trajectories")
        st.caption("Solid = treated group, dashed = control. Divergence in pre-period signals violation.")
        st.altair_chart(did_trajectory_chart(res["traj_data"]), width="stretch")

        # ── Bias vs Violation ─────────────────────────────
        st.subheader("Bias vs Pre-trend Violation")
        st.altair_chart(bias_violation_chart(res["bias_data"]), width="stretch")

        with st.expander("Bias Detail Table"):
            st.dataframe(
                pd.DataFrame(res["bias_data"]).style.format({
                    "bias": "{:.4f}", "bias_pct": "{:.2f}%", "power": "{:.3f}"
                }),
                width="stretch",
            )

        # ── Power Curve ───────────────────────────────────
        st.subheader("Power vs Number of Units")
        st.altair_chart(did_power_chart(res["power_data"]), width="stretch")

        with st.expander("Interpretation Guide"):
            st.markdown(f"""
            **True effect**: {res['true_effect']:.2f}

            **Parallel trends assumption**: If units that received treatment would have followed the same
            trend as control units absent treatment. The pre-period visualization tests this visually.

            **Bias formula**: Bias ≈ (trend_violation × post_period_length / pre_period_length).
            A violation of 1.0 with 4 post-periods and 8 pre-periods → ~50% of true effect as bias.

            **When bias is large**: Consider Synthetic Control (weights donors to match pre-trend),
            Callaway-Sant'Anna (controls for staggered rollout), or Event Study plots to document the violation.
            """)
    else:
        st.info("Configure parameters above and click **Run Simulation**.")
