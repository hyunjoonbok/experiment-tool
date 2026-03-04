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

    st.subheader("Study Characteristics")

    col1, col2 = st.columns(2)

    with col1:
        can_randomize = st.toggle("Can you randomize assignment?", value=True)
        has_spillover = st.toggle(
            "Risk of spillover / network effects?",
            value=False,
            help="e.g., social features, marketplace, referrals where treatment spreads to control",
        )
        has_staggered_rollout = st.toggle(
            "Staggered / phased rollout?",
            value=False,
            help="Different units receive treatment at different times",
        )

    with col2:
        has_panel_data = st.toggle(
            "Panel data available (multiple periods per unit)?",
            value=True,
        )
        has_strong_pre_period = st.toggle(
            "Strong pre-period (3+ periods before treatment)?",
            value=True,
        )
        has_instrument = st.toggle(
            "Valid natural experiment / instrument available?",
            value=False,
            help="e.g., lottery, geographic discontinuity, threshold rule",
        )
        n_treated_units = st.number_input(
            "Number of treated units (markets/geos/teams)",
            min_value=1, value=10, step=1,
            help="Relevant for Synthetic Control — works best with 1–5 treated units",
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
        for a in design.required_assumptions:
            st.markdown(f"- {a}")

        st.subheader("Pros")
        for p in design.pros:
            st.markdown(f"✓ {p}")

    with col2:
        st.subheader("Sensitivity Checks")
        for s in design.sensitivity_checks:
            st.markdown(f"- {s}")

        st.subheader("Cons")
        for c in design.cons:
            st.markdown(f"✗ {c}")

    st.subheader("Model Specification")
    st.code(design.model_spec, language="text")
