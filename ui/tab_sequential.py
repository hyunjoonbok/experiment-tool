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

    with st.expander("📖 About this tool — click to learn how to use it", expanded=False):
        st.markdown("""
        ### The peeking problem
        It is tempting to check your experiment results every day and stop early if you see p<0.05.
        This practice — called **peeking** — is statistically invalid and will inflate your false positive rate far above the intended α.

        **Example:** With α=0.05 and 5 peeks at equal intervals, your true false positive rate is ~18%,
        not 5%. You will incorrectly conclude the treatment works 1 in 5 times when it has zero effect.

        ---
        ### Sequential testing to the rescue
        Sequential testing provides **valid stopping rules** that let you look at data multiple times
        while keeping the overall false positive rate at α. Each method allocates alpha differently across looks:

        | Method | Philosophy | Best for |
        |---|---|---|
        | **O'Brien-Fleming** | Very conservative early, spends most alpha at the final look | Preserving power while allowing planned early stopping |
        | **Pocock** | Equal chance to stop at every look | When early stopping is the primary goal |
        | **Haybittle-Peto** | Near-impossible to stop early (z=3.29), standard final look | Simplest to explain to stakeholders |
        | **Fixed (no correction)** | ⚠️ Invalid — illustrates peeking inflation for educational purposes | Do not use in production |

        ---
        ### How to use this tool
        1. Set **K** to the number of pre-planned interim looks you want (e.g., weekly reviews for a 5-week experiment → K=5).
        2. Choose the boundary that matches your priorities.
        3. The **Alpha Spending Table** (shown immediately) tells you the exact z-threshold at each look.
        4. Click **Run Simulation** to see the empirical false positive rate and power.
        5. Compare the sequential design power to a fixed-design power — well-designed sequential tests lose very little power.

        ---
        ### Key outputs
        - **Empirical Type I Error**: Should be ≤ α. If it's much higher, the boundary is not controlling the error rate.
        - **Sequential Design Power**: Probability of detecting the true effect at any of the K looks. Should be close to the fixed-design power.
        - **Expected Stopping Look**: On average, at which look do experiments stop (among those that reject)? Earlier = less data collected = cheaper experiment.
        - **Never Rejected**: Experiments where the true effect existed but no look detected it (missed detections). This is 1 - Power.
        """)

    col1, col2 = st.columns(2)

    with col1:
        K = st.slider(
            "Number of Interim Looks (K)",
            2, 10, 5,
            help=(
                "How many times you plan to analyze the data during the experiment. "
                "For a 4-week experiment with weekly reviews: K=4. "
                "**You must pre-specify K before the experiment starts.** "
                "Adding unplanned looks invalidates the sequential design. "
                "More looks = more flexibility, but also more alpha spent per look = higher z-boundary."
            ),
            key="seq_K",
        )
        n_total = st.number_input(
            "Total Sample Size (both arms)",
            min_value=200, value=5000, step=200,
            help=(
                "The maximum total sample size across both arms if the experiment runs to completion. "
                "This determines the N at each interim look — look k sees k/K × n_total observations. "
                "Use the required sample size from the Power & MDE tab as your starting point."
            ),
            key="seq_n_total",
        )
        alpha = st.slider(
            "Nominal Alpha (α)",
            0.01, 0.10, 0.05, step=0.01,
            help=(
                "The overall false positive rate you want to control across ALL looks. "
                "This is the same α as in your power calculation. "
                "The boundary ensures that even with K looks, the total probability of a false positive ≤ α. "
                "Standard: 0.05."
            ),
            key="seq_alpha",
        )

    with col2:
        boundary = st.selectbox(
            "Boundary / Spending Function",
            ["obrien_fleming", "pocock", "haybittle_peto", "fixed"],
            format_func=lambda x: {
                "obrien_fleming": "O'Brien-Fleming (conservative early, liberal late)",
                "pocock": "Pocock (equal boundaries at each look)",
                "haybittle_peto": "Haybittle-Peto (z=3.29 interim, z_α final — simplest to explain)",
                "fixed": "Fixed — no correction (naive peeking) ⚠️",
            }[x],
            help=(
                "The rule for how much alpha to spend at each look. "
                "**O'Brien-Fleming**: spends almost no alpha early; nearly all alpha is saved for the final look. "
                "Great for experiments where early stopping is a bonus, not the goal. "
                "**Pocock**: equal chance of stopping at any look; final look has a higher threshold than α. "
                "**Haybittle-Peto**: interim threshold of z=3.29 (p≈0.001) — practically impossible to stop early by chance; "
                "final look uses standard z_α. Simplest to explain: 'interim stops require overwhelming evidence.' "
                "**Fixed (no correction)**: educationally shows the inflation from uncorrected peeking. Do not use for real experiments."
            ),
            key="seq_boundary",
        )
        true_effect = st.slider(
            "True Effect (Cohen's d, for power simulation)",
            0.05, 0.8, 0.2, step=0.05,
            help=(
                "Cohen's d = (mean_treatment - mean_control) / pooled_std. "
                "This is the standardized effect size used in the power simulation under H₁. "
                "Typical values: small=0.2, medium=0.5, large=0.8. "
                "For a 10% lift on a binary metric with baseline p=0.10: "
                "d ≈ (0.11-0.10) / sqrt(0.10×0.90) ≈ 0.033 (small). "
                "Set this to your expected effect from the Power tab."
            ),
            key="seq_true_effect",
        )
        n_sim = st.select_slider(
            "Simulation Runs",
            options=[1000, 3000, 5000],
            value=3000,
            help=(
                "Number of simulated experiments for the type I error and power estimates. "
                "More simulations = more accurate empirical estimates. "
                "3000 gives ~±1.5pp confidence interval on a 5% rate. "
                "Use 5000 for final precision."
            ),
            key="seq_n_sim",
        )

    # ── Alpha Spending Table (always show — fast) ─────────
    st.divider()
    st.subheader("Alpha Spending Schedule")
    st.caption(
        "This table tells you the **exact z-score threshold to use at each look**. "
        "At look k, if |z-statistic| > z_boundary, you reject H₀ and stop the experiment. "
        "If not, you continue to the next look. "
        "The cumulative alpha spent shows how much of your total α budget has been used by that look."
    )
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

    if boundary == "fixed":
        st.error(
            "⚠️ **Fixed (no correction) selected.** This is for educational illustration only. "
            "Using the same z-threshold at every look inflates the false positive rate far above α. "
            "Never use this boundary for real experiment decisions."
        )

    st.altair_chart(alpha_spending_chart(spending), width="stretch")
    st.caption(
        "The curve shows how the alpha budget is consumed across looks. "
        "O'Brien-Fleming hugs the bottom left (spends almost nothing early). "
        "Pocock is a straight line (equal spending at every look). "
        "Haybittle-Peto spends tiny amounts early, then the rest at the final look."
    )

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
        st.subheader("Type I Error (False Positive Rate under H₀)")
        st.caption(
            "These simulations run the experiment assuming **zero true effect** — H₀ is true. "
            "The empirical type I error tells you: with this boundary, if there is no real effect, "
            "what fraction of experiments would still reject H₀? This should be ≤ α."
        )
        col_a, col_b = st.columns(2)
        delta = t1["empirical_type1_error"] - alpha
        col_a.metric(
            "Empirical Type I Error",
            f"{t1['empirical_type1_error']:.3f}",
            delta=f"{delta:+.3f} vs α={alpha}",
            delta_color="inverse",
            help=(
                "The fraction of simulated experiments (all run under H₀) that incorrectly rejected H₀. "
                f"Should be ≤ {alpha}. If it is much higher, the boundary is not controlling the error rate. "
                "Negative delta (shown in green) = the boundary is conservative — actual false positives < α."
            ),
        )
        col_b.metric(
            "Nominal Alpha",
            f"{alpha:.3f}",
            help="The target false positive rate you set. The empirical value should be at or below this.",
        )

        if boundary == "fixed":
            st.error(
                f"Without correction, {K} peeks inflates your effective false positive rate to "
                f"**{t1['empirical_type1_error']:.3f}** ({t1['empirical_type1_error']/alpha:.1f}× the intended α={alpha}). "
                "This means you are {:.0f}× more likely to declare a winner incorrectly than you planned.".format(
                    t1["empirical_type1_error"] / alpha
                )
            )
        else:
            if t1["empirical_type1_error"] <= alpha * 1.1:
                st.success(
                    f"The **{boundary.replace('_', '-').title()}** boundary successfully controls type I error "
                    f"at **{t1['empirical_type1_error']:.3f}** ≤ α={alpha}. "
                    "Your false positive rate is protected even with multiple looks."
                )
            else:
                st.warning(
                    f"Type I error ({t1['empirical_type1_error']:.3f}) slightly exceeds α={alpha}. "
                    "This may be simulation noise — run more simulations for a tighter estimate."
                )

        # ── Power & Stopping ──────────────────────────────
        st.divider()
        st.subheader("Power & Stopping Time (under H₁)")
        st.caption(
            "These simulations run the experiment assuming the **true effect = Cohen's d you specified**. "
            "This tells you: if the treatment truly works, will this sequential design detect it?"
        )
        pc1, pc2, pc3 = st.columns(3)
        pc1.metric(
            "Sequential Design Power",
            f"{power_res['power']:.3f}",
            help=(
                "Fraction of simulated experiments (all run under H₁) that correctly rejected H₀ at any look. "
                "Compare to your target power from the Power & MDE tab. "
                "A well-designed sequential test loses <5% power vs a fixed-N test."
            ),
        )
        pc2.metric(
            "Expected Stopping Look",
            f"{power_res['expected_stopping_look']:.1f} / {K}",
            help=(
                "Average look number at which experiments that rejected H₀ first stopped. "
                "Only counts experiments that actually rejected (not the ones that missed). "
                f"If this is well below K, the sequential design is saving data — "
                "experiments are stopping early when the effect is large and clear."
            ),
        )
        never_rej = power_res.get("n_never_rejected", 0)
        n_sim_used = n_sim
        never_pct = never_rej / n_sim_used if n_sim_used > 0 else 0
        pc3.metric(
            "Never Rejected",
            f"{never_rej:,}",
            help=(
                f"Experiments where the true effect existed but no look detected it ({never_pct:.1%} of {n_sim_used:,} simulations). "
                "This is the missed detection rate = 1 - Power. "
                "High values indicate you are underpowered for this effect size."
            ),
        )

        if power_res['power'] < 0.70:
            st.warning(
                f"Power is only **{power_res['power']:.3f}** for Cohen's d={true_effect}. "
                "You will miss this effect more than 30% of the time. "
                "Consider increasing total sample size or choosing a less conservative boundary."
            )

        st.altair_chart(
            stopping_distribution_chart(power_res["looks"], power_res["stopping_look_distribution"]),
            width="stretch",
        )
        st.caption(
            "Shows at which look experiments that detected the effect first stopped. "
            "A tall bar at look 1 means many experiments had a strong enough signal to stop early — "
            "saving a large fraction of the planned sample size. "
            "A tall bar at look K means most experiments ran to completion before detecting the effect."
        )
    else:
        st.info("Configure parameters above and click **Run Simulation**.")

    with st.expander("Interpretation Guide"):
        st.markdown("""
        **O'Brien-Fleming**: Spends very little alpha early — very high bar to stop early (large z-boundary),
        saves most budget for the final look. Best for preserving power while allowing planned early stopping.
        If the effect is large, you'll still stop early; if it's modest, you'll run to the final look.

        **Pocock**: Equal z-boundary at every look — more aggressive early stopping potential,
        but the final-look boundary is higher than z_α so you lose power at the end.
        Preferred when early stopping is the primary goal and you're willing to accept lower final power.

        **Haybittle-Peto**: Uses z=3.29 (α≈0.001) at all interim looks and the standard z_α at the final look.
        The simplest to explain to stakeholders: "interim stops require overwhelming evidence (p<0.001);
        final analysis uses normal threshold." Barely affects final-look power (<1% loss vs fixed design).

        **Fixed (no correction)**: Each peek at α inflates the family-wise error rate.
        At 5 peeks with α=0.05, your real false positive rate can reach ~18%.
        **Never use this for real experiment decisions.**

        ---
        **"Never Rejected" metric**: Under H₁, this is the number of missed detections —
        experiments where the true effect existed but all K looks failed to reject.
        High values indicate insufficient power or an overly conservative boundary.
        """)
