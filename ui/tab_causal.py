"""
UI Tab 6: Causal Design Selector
"""

import streamlit as st
from tools.causal_selector import select_design, get_design, DESIGNS


CONFIDENCE_COLOR = {"High": "success", "Medium": "warning", "Low": "error"}


def render():
    st.header("Causal Design Selector")
    st.caption(
        "Answer a few questions about your study and get a recommended causal inference method, "
        "required assumptions, sensitivity checks, and a ready-to-use model specification."
    )

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **Causation vs correlation:** A correlation tells you two things move together. Causation
        tells you that changing one thing *causes* a change in the other. Product decisions require
        causal estimates — if you observe that users who see Feature X have higher retention, that
        could be because Feature X improves retention, or because high-retention users are more
        likely to discover Feature X. Without the right design, you cannot tell the difference.

        **Why the right design depends on your data:** The gold standard for causal inference is
        a randomized controlled trial (A/B test). When randomization is not possible — for example,
        a full product launch, a geo rollout, or a policy change — you need a quasi-experimental
        method that can approximate causal estimates under specific assumptions.

        **What "identification confidence" means:**
        - **High:** The design has a strong theoretical guarantee of causality (e.g., randomization).
          Trust the estimate as causal.
        - **Medium:** The design relies on assumptions that are plausible but not guaranteed
          (e.g., parallel trends in DiD). The estimate is likely causal if assumptions hold — validate them.
        - **Low:** The best available method given your data, but the causal interpretation is fragile.
          Report results with appropriate uncertainty and conduct sensitivity analyses.

        **When to use this tool:** At the study design stage, before committing to an analysis
        approach. Answer the questions honestly based on your actual data availability and
        product context.
        """)

    st.subheader("Study Characteristics")

    col1, col2 = st.columns(2)

    with col1:
        can_randomize = st.toggle(
            "Can you randomize assignment?",
            value=True,
            help="Can you flip a coin to decide which users get the feature — before the feature launches? If yes, you can run a standard A/B test. If the feature is being rolled out to all users at once, or you cannot control who sees it, answer No.",
        )
        has_spillover = st.toggle(
            "Risk of spillover / network effects?",
            value=False,
            help="Could a treated user's behavior change an untreated user's outcome? Examples: social features (user A shares content with user B who is in control), marketplace (treatment arm bids drive up prices for control arm buyers), referral programs. If yes, user-level randomization may be contaminated.",
        )
        has_staggered_rollout = st.toggle(
            "Staggered / phased rollout?",
            value=False,
            help="Are different units (users, geos, cohorts) receiving the treatment at different points in time? For example, launching to US first, then EU, then APAC. Staggered rollouts require special DiD estimators (Callaway-Sant'Anna) to avoid bias from heterogeneous treatment timing.",
        )

    with col2:
        has_panel_data = st.toggle(
            "Panel data available (multiple periods per unit)?",
            value=True,
            help="Do you have multiple time periods of data for each unit (user, market, geo) — both before and after treatment? Panel data enables Difference-in-Differences and Synthetic Control. If you only have a single cross-section, these methods are not available.",
        )
        has_strong_pre_period = st.toggle(
            "Strong pre-period (3+ periods before treatment)?",
            value=True,
            help="Do you have at least 3 time periods of pre-treatment data for all units? A strong pre-period lets you validate the parallel trends assumption visually and statistically (pre-trend test). Fewer than 3 pre-periods makes assumption validation very difficult.",
        )
        has_instrument = st.toggle(
            "Valid natural experiment / instrument available?",
            value=False,
            help="Is there an external variable that affects treatment assignment but has no direct effect on the outcome except through treatment? Examples: lottery results, geographic policy boundaries, age cutoffs, quota thresholds. A valid instrument enables Instrumental Variables (IV) estimation.",
        )
        n_treated_units = st.number_input(
            "Number of treated units (markets/geos/teams)",
            min_value=1, value=10, step=1,
            help="Relevant for Synthetic Control — works best with 1–5 treated units. With more treated units, DiD or staggered DiD is typically preferred. For user-level studies, this field is less relevant.",
        )

    st.divider()

    # ── Recommendation ────────────────────────────────────
    primary, secondary = select_design(
        can_randomize=can_randomize,
        has_spillover=has_spillover,
        has_staggered_rollout=has_staggered_rollout,
        has_panel_data=has_panel_data,
        has_strong_pre_period=has_strong_pre_period,
        has_instrument=has_instrument,
        n_treated_units=n_treated_units,
    )

    primary_design = get_design(primary)
    secondary_design = get_design(secondary)

    # Primary recommendation
    conf_level = primary_design.confidence
    getattr(st, CONFIDENCE_COLOR[conf_level])(
        f"**Recommended: {primary_design.method}** — Identification confidence: {conf_level}"
    )
    st.caption(primary_design.when_to_use)

    st.caption(
        "**What identification confidence means for your decisions:** "
        "**High confidence** — treat the estimate as causal; standard statistical tests apply. "
        "**Medium confidence** — the estimate is likely causal if the listed assumptions hold; "
        "always run the sensitivity checks before drawing conclusions. "
        "**Low confidence** — the causal interpretation is fragile; report results as suggestive "
        "and be explicit about limitations in any decision document."
    )

    tabs = st.tabs(["Primary Design", "Alternative Design", "All Designs"])

    with tabs[0]:
        _render_design(primary_design)

    with tabs[1]:
        st.info(f"If the primary design isn't feasible, consider: **{secondary_design.method}**")
        _render_design(secondary_design)

    with tabs[2]:
        selected = st.selectbox("Explore any design:", list(DESIGNS.keys()))
        _render_design(get_design(selected))


def _render_design(design):
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Required Assumptions")
        st.caption(
            "These assumptions must hold for your estimate to be causally valid. "
            "If you cannot verify them, your estimate may be biased. "
            "Document how you will test or argue for each assumption in your analysis plan."
        )
        for a in design.required_assumptions:
            st.markdown(f"- {a}")

        st.subheader("Pros")
        for p in design.pros:
            st.markdown(f"✓ {p}")

    with col2:
        st.subheader("Sensitivity Checks")
        st.caption(
            "Run these checks AFTER your analysis to test whether your result holds under "
            "alternative assumptions. A result that changes substantially under minor assumption "
            "perturbations should be reported with caution."
        )
        for s in design.sensitivity_checks:
            st.markdown(f"- {s}")

        st.subheader("Cons")
        for c in design.cons:
            st.markdown(f"✗ {c}")

    st.subheader("Model Specification")
    st.code(design.model_spec, language="text")
