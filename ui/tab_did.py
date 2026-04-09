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

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **What is Difference-in-Differences (DiD)?** DiD is a causal inference method used when
        you cannot randomize. Instead, you compare the *change over time* in a treated group to
        the *change over time* in an untreated control group. The "difference in differences" is:
        (treated post − treated pre) − (control post − control pre).

        **When is DiD used in product settings?** Common scenarios: a feature launched to all
        users in one geo but not another, a policy change affecting one user cohort, or a
        non-randomized experiment where randomization was not feasible. DiD is also used
        retrospectively to evaluate past launches.

        **The parallel trends assumption:** DiD only produces an unbiased causal estimate if,
        *absent the treatment*, the treated and control groups would have followed the same
        trend over time. This is the core identifying assumption. It cannot be directly tested
        (you never observe the counterfactual), but you can check whether the groups were
        trending similarly *before* treatment — which is exactly what the pre-trend plot shows.

        **What violating parallel trends does:** If the treated group was already trending
        differently before treatment, DiD will incorrectly attribute that pre-existing trend
        to the treatment effect, biasing your estimate up or down.

        **When to use this tool vs a standard A/B test:** Use DiD (and this simulator) when
        you cannot randomize. If you can randomize, run a standard A/B test — it requires
        fewer assumptions and gives cleaner causal estimates.
        """)

    col1, col2 = st.columns(2)

    with col1:
        n_units = st.slider(
            "Number of Units (treated + control)",
            10, 200, 50, step=10,
            help="Total number of units (users, geos, markets) across both treated and control groups. More units = more power. For geo-level DiD, typical values are 10–50 markets. For user-level DiD, values can be much larger.",
            key="did_n_units",
        )
        n_pre = st.slider(
            "Pre-period Length (periods)",
            2, 20, 8,
            help="Number of time periods observed before treatment begins. More pre-periods allow better validation of the parallel trends assumption. At least 3–5 pre-periods is recommended; fewer makes assumption testing unreliable.",
            key="did_n_pre",
        )
        n_post = st.slider(
            "Post-period Length (periods)",
            1, 12, 4,
            help="Number of time periods observed after treatment begins. Longer post-periods increase power but also increase risk of parallel trends violations compounding over time. Typical range: 1–6 periods.",
            key="did_n_post",
        )
        alpha = st.slider(
            "Significance Level (α)",
            0.01, 0.10, 0.05, step=0.01,
            help="The false positive rate threshold for declaring statistical significance. Standard is 0.05 (5%). Use 0.01 for high-stakes decisions. Using a larger alpha increases power but also increases false positives.",
            key="did_alpha",
        )

    with col2:
        true_effect = st.number_input(
            "True Treatment Effect",
            value=1.0,
            format="%.2f",
            help="The actual causal effect size you want to detect. This is the ground truth in the simulation. Set it to your minimum detectable effect (MDE) — the smallest effect that would be practically meaningful for your product decision.",
            key="did_true_effect",
        )
        noise = st.slider(
            "Noise Level (σ)",
            0.1, 5.0, 1.0, step=0.1,
            help="Standard deviation of the error term in the outcome model. Higher noise = lower signal-to-noise ratio = lower power. Estimate from historical variance of your outcome metric. A noise/effect ratio above 2.0 typically requires many units.",
            key="did_noise",
        )
        trend_violation = st.slider(
            "Pre-trend Violation Magnitude",
            0.0, 3.0, 0.0, step=0.1,
            help="How much the treated group trends differently from control in the pre-period, per time unit. 0 = perfect parallel trends (assumption holds). Values above 0.5 typically cause meaningful bias. Use this to stress-test your design against assumption violations.",
            key="did_trend_violation",
        )
        n_sim = st.select_slider(
            "Simulation Runs",
            options=[500, 1000, 2000],
            value=500,
            help="Number of Monte Carlo simulation repetitions. More runs give more precise estimates of power, bias, and CI coverage, but take longer. 500 is sufficient for exploratory analysis; use 2,000 for final design decisions.",
            key="did_n_sim",
        )

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
        cov_delta = main_result.ci_coverage - 0.95
        m4.metric(
            "Empirical CI Coverage",
            f"{main_result.ci_coverage:.1%}",
            delta=f"{cov_delta:+.1%} vs 95% nominal",
            delta_color="inverse" if cov_delta < -0.03 else "normal",
            help=f"Fraction of simulations where the 95% CI contained the true effect. "
                 f"Mean estimate CI: [{main_result.ci_low:.3f}, {main_result.ci_high:.3f}]",
        )

        st.caption(
            "**True Effect** is the ground-truth causal effect set in the simulation parameters. "
            "**Estimated Effect** is the average DiD estimate across all simulation runs — the gap "
            "between these two is the **Bias** caused by the parallel trends violation you set. "
            "**Power** is the fraction of simulations where the DiD estimate was statistically "
            "significant — you want this to be at or above 0.80 (80%). "
            "**Empirical CI Coverage** should be close to 95% for a well-calibrated test; "
            "coverage well below 95% means your confidence intervals are too narrow and your "
            "false positive rate is higher than the nominal α."
        )

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

        st.info(
            "**How to read this chart:** The vertical line marks the start of treatment (period 0). "
            "Look at the lines to the *left* of that line — this is the pre-period. "
            "If the solid (treated) and dashed (control) lines are running parallel in the pre-period, "
            "the parallel trends assumption holds and the DiD estimate is likely unbiased. "
            "Any divergence or different slopes in the pre-period is a red flag — it means the two "
            "groups were already trending differently before treatment, which will bias the estimate. "
            "The three curves show what happens at different violation magnitudes: 0.0 (clean), "
            "0.5 (moderate), and 1.0 (severe)."
        )

        # ── Bias vs Violation ─────────────────────────────
        st.subheader("Bias vs Pre-trend Violation")
        st.altair_chart(bias_violation_chart(res["bias_data"]), width="stretch")

        st.info(
            "**How to read this chart:** The x-axis shows the magnitude of the pre-trend violation "
            "(how different the treated group's slope was from control before treatment). "
            "The y-axis shows the resulting bias as a percentage of the true effect. "
            "Even a small violation of 0.25 can cause meaningful bias at the magnitudes shown — "
            "this is why pre-trend testing is not optional. If you cannot rule out a pre-trend "
            "violation, your DiD estimate may be substantially over- or under-estimating the true effect."
        )

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
