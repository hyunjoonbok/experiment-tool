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

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **What is a conversion funnel?** A funnel models the sequential stages users pass through
        on the way to a desired outcome — for example: Impression → Click → Sign-up → Activation → Retention.
        At each stage, a fraction of users convert to the next stage (the conversion rate, CVR).
        Users who don't convert drop off.

        **Why model the full funnel?** A treatment applied at sign-up doesn't just affect sign-ups —
        it affects every downstream stage, all the way to revenue. If you only measure sign-up rate,
        you'll miss the compounded effect on MAU and revenue. Modeling the full funnel gives you a
        more accurate business case for the feature.

        **What is downstream decay?** In practice, an improvement at an early funnel stage does not
        fully carry through to later stages. Users acquired through a slightly better sign-up flow
        may have lower long-term retention than organic users. Downstream decay captures this:
        a decay of 80% means each subsequent stage retains only 80% of the uplift from the previous
        stage. 100% means the uplift carries fully through; lower values model attrition.

        **When is this tool most useful?**
        - Building a business case: translating a measured experiment lift into revenue impact.
        - Sizing experiments: if your primary metric is a downstream outcome (e.g., MAU), use this
          tool to figure out how large an upstream uplift you need to detect a meaningful downstream signal.
        - Stress-testing assumptions: the sensitivity heatmap shows how robust the business case is
          to different uplift and decay assumptions.
        """)

    # ── Funnel Definition ─────────────────────────────────
    st.subheader("Funnel Definition")

    n_stages = st.slider(
        "Number of Stages",
        2, 7, 5,
        help="How many conversion stages your funnel has. More stages give a more realistic model but require more parameter estimates. Typical product funnels have 3–6 stages.",
        key="fun_n_stages",
    )
    stages = DEFAULT_STAGES[:n_stages]
    default_cvrs = DEFAULT_CVRS[:n_stages]

    stage_cols = st.columns(n_stages)
    stage_names = []
    baseline_cvrs = []
    for i, col in enumerate(stage_cols):
        with col:
            name = col.text_input(
                f"Stage {i+1}",
                value=stages[i],
                help=f"Name of funnel stage {i+1}. Label it to match your product's terminology (e.g., 'Install', 'First Session', 'Purchase').",
                key=f"stage_{i}",
            )
            cvr = col.number_input(
                "CVR (%)",
                min_value=0.1,
                max_value=100.0,
                value=default_cvrs[i] * 100,
                step=1.0,
                key=f"cvr_{i}",
                format="%.1f",
                help=f"Baseline conversion rate from stage {i+1} to stage {i+2} (or the final stage rate). Estimate from historical data. This is the fraction of users entering this stage who successfully complete it.",
            ) / 100
            stage_names.append(name)
            baseline_cvrs.append(cvr)

    st.divider()

    # ── Treatment Parameters ───────────────────────────────
    st.subheader("Treatment Parameters")
    col1, col2 = st.columns(2)

    with col1:
        top_n = st.number_input(
            "Top-of-Funnel Users",
            min_value=1000,
            value=100_000,
            step=10_000,
            help="Total number of users entering the top of the funnel (before any conversion). This is your eligible experiment population — e.g., total daily active users, or total users exposed to the feature surface.",
            key="fun_top_n",
        )
        treatment_stage = st.selectbox(
            "Stage Where Treatment is Applied",
            options=list(range(n_stages)),
            format_func=lambda i: f"Stage {i+1}: {stage_names[i]}",
            help="The funnel stage where your treatment intervention acts. The treatment uplift is applied to the CVR at this stage. Downstream stages receive the compounded effect, reduced by the decay rate.",
            key="fun_treatment_stage",
        )
        treatment_uplift = st.slider(
            "Treatment Uplift at Stage (%)",
            1, 50, 10,
            help="Relative improvement in CVR at the treatment stage. A 10% uplift on a 30% baseline CVR yields 33% treated CVR. Set this to the effect size from your experiment or your hypothesis. Typical detectable lifts: 2–20%.",
            key="fun_uplift",
        ) / 100

    with col2:
        downstream_decay = st.slider(
            "Downstream Uplift Retention (%)",
            10, 100, 80, step=5,
            help="What % of the uplift carries through to the next stage. 100% = full carry-through (optimistic). 50% = half the uplift is lost at each stage (conservative). Use 70–80% as a reasonable default for most product features.",
            key="fun_decay",
        ) / 100
        retention_multiplier = st.slider(
            "Final Retention Multiplier",
            0.5, 2.0, 1.0, step=0.05,
            help="Multiplier on bottom-of-funnel MAU to account for long-term retention effects not captured in the funnel stages. 1.0 = no adjustment. Values below 1.0 model worse long-term retention for treatment-acquired users; values above 1.0 model better retention.",
            key="fun_retention_mult",
        )
        spillover = st.slider(
            "Spillover to Adjacent Stage (%)",
            -20, 20, 0, step=1,
            help="Positive = boost to the stage immediately before the treatment stage (e.g., awareness created by the new feature). Negative = cannibalization (the treatment stage draws users away from an adjacent funnel). 0 = no spillover (most common assumption).",
            key="fun_spillover",
        ) / 100
        revenue_per_user = st.number_input(
            "Revenue per MAU ($)",
            value=10.0,
            min_value=0.0,
            format="%.2f",
            help="Average monthly revenue per monthly active user (ARPU). Used to convert net MAU delta into revenue delta. This assumes constant ARPU across treatment and control — if the treatment changes monetization behavior, adjust accordingly.",
            key="fun_revenue",
        )

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

        st.caption(
            "**Net MAU Delta** is the additional monthly active users at the bottom of the funnel "
            "attributable to the treatment uplift, after applying downstream decay. "
            "**Revenue Delta** is Net MAU Delta × Revenue per MAU — this assumes constant ARPU "
            "across all users. If your treatment changes the *quality* of acquired users "
            "(e.g., they spend more or less), adjust the Revenue per MAU input accordingly. "
            "These are modeled estimates, not measured experiment results."
        )

        st.divider()

        # ── Funnel Volumes ────────────────────────────────
        st.subheader("Funnel Volumes")
        st.altair_chart(funnel_bar_chart(funnel_chart_data(result)), width="stretch")

        st.caption(
            "Each bar pair shows the number of users at that funnel stage for baseline (control) "
            "and treatment. The bars narrow as users drop off at each stage. The gap between "
            "treatment and baseline bars represents the incremental users created by the treatment "
            "uplift, compounded through downstream stages with decay applied."
        )

        # ── Incremental Users ─────────────────────────────
        st.subheader("Incremental Users per Stage")
        st.altair_chart(
            funnel_incremental_chart(result.stage_names, result.incremental_users_per_stage),
            width="stretch",
        )

        st.caption(
            "**Green bars** indicate stages where the treatment adds incremental users relative to baseline. "
            "**Red bars** (if present) indicate stages where the treatment reduces users — this can occur "
            "at stages before the treatment stage if a negative spillover effect is set, or if the "
            "downstream decay is severe enough to cause negative compounding. "
            "The final bar represents the net MAU impact shown in the summary metrics above."
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

        st.caption(
            "**CVR Δ (pp)** is expressed in absolute percentage points, not relative lift. "
            "A +2.00 pp change on a 10% baseline CVR is a +20% relative lift — these are very "
            "different numbers and easy to confuse. Always clarify whether you mean absolute or "
            "relative lift when communicating experiment results."
        )

        st.divider()

        # ── Sensitivity Heatmap ───────────────────────────
        st.subheader("Sensitivity: Net MAU Δ% (Uplift × Decay)")
        st.caption("How robust is the impact estimate to assumptions about treatment strength and decay?")
        st.altair_chart(sensitivity_heatmap_funnel(sweep), width="stretch")

        st.info(
            "**How to read this heatmap:** Each cell shows the Net MAU Δ% for a combination of "
            "treatment uplift (x-axis) and downstream decay (y-axis). Your current settings correspond "
            "to one cell in this grid. "
            "**If all cells are green:** the result is robust — even pessimistic assumptions yield "
            "a positive impact, and you have a strong business case. "
            "**If there is a sharp color cliff:** the result is sensitive to assumptions — a small "
            "change in decay or uplift flips the sign. In this case, gather better estimates of the "
            "decay rate before making a launch decision, and widen your confidence intervals accordingly."
        )

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
