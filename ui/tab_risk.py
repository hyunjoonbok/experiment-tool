"""
UI Tab 5: Experiment Risk Scanner
"""

import streamlit as st
from tools.risk_scanner import run_risk_scan, RiskFlag
from utils.charts import risk_gauge_chart


LEVEL_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
LEVEL_COLOR = {"green": "success", "yellow": "warning", "red": "error"}


def render():
    st.header("Experiment Risk Scanner")
    st.caption(
        "Input your experiment design parameters and get an automated risk audit "
        "before you ship."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Traffic & Allocation")
        n_control = st.number_input("Control Arm Size (n)", min_value=10, value=5000, step=100)
        n_treatment = st.number_input("Treatment Arm Size (n)", min_value=10, value=5050, step=100)
        expected_allocation = st.slider(
            "Expected Control Allocation (%)", 30, 70, 50
        ) / 100

        st.subheader("Segmentation")
        n_segments = st.slider(
            "Number of Segments Analyzed",
            1, 20, 3,
            help="More post-hoc segments = higher Simpson's paradox risk",
        )
        segment_size_imbalance = st.slider(
            "Segment Size Imbalance (0=balanced, 1=extreme)",
            0.0, 1.0, 0.2, step=0.1,
        )
        metric_correlation = st.slider(
            "Metric–Segment Correlation",
            -1.0, 1.0, 0.3, step=0.1,
            help="Correlation between segment membership and the outcome metric",
        )

    with col2:
        st.subheader("Experiment Setup")
        randomization_unit = st.selectbox(
            "Randomization Unit",
            ["user", "session", "geo", "device"],
            format_func=lambda x: {
                "user": "User (recommended for most features)",
                "session": "Session (risk: same user in both arms)",
                "geo": "Geo / Market (good for network effects)",
                "device": "Device (risk: cross-device contamination)",
            }[x],
        )
        feature_type = st.selectbox(
            "Feature Type",
            ["engagement", "monetization", "ai_usage", "retention", "migration", "marketplace", "social", "referral"],
            format_func=lambda x: x.replace("_", " ").title(),
        )
        experiment_duration_days = st.slider("Planned Experiment Duration (days)", 1, 60, 14)
        is_new_feature = st.checkbox("This is a brand-new feature (higher novelty risk)", value=True)

        st.subheader("Metric Properties")
        metric_type = st.text_input(
            "Primary Metric Name",
            value="click_through_rate",
            help="Used to assess metric gaming vulnerability (e.g., 'ctr', 'revenue', 'retention')",
        )
        has_pre_experiment_data = st.checkbox("Pre-experiment data available (CUPED eligible)", value=True)

    st.divider()

    # ── Run Scan ─────────────────────────────────────────
    flags = run_risk_scan(
        n_control=n_control,
        n_treatment=n_treatment,
        expected_allocation=expected_allocation,
        n_segments=n_segments,
        segment_size_imbalance=segment_size_imbalance,
        metric_correlation=metric_correlation,
        randomization_unit=randomization_unit,
        feature_type=feature_type,
        experiment_duration_days=experiment_duration_days,
        is_new_feature=is_new_feature,
        metric_type=metric_type,
        has_pre_experiment_data=has_pre_experiment_data,
    )

    # ── Summary ───────────────────────────────────────────
    red_count = sum(1 for f in flags if f.level == "red")
    yellow_count = sum(1 for f in flags if f.level == "yellow")
    green_count = sum(1 for f in flags if f.level == "green")

    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Critical Risks 🔴", red_count)
    sc2.metric("Warnings 🟡", yellow_count)
    sc3.metric("Clear ✅", green_count)

    if red_count > 0:
        st.error(f"**{red_count} critical risk(s) detected.** Review flags below before shipping.")
    elif yellow_count > 0:
        st.warning(f"**{yellow_count} warning(s) detected.** Consider mitigations before shipping.")
    else:
        st.success("All checks passed. Your experiment design looks solid!")

    # ── Gauge Chart ────────────────────────────────────────
    st.altair_chart(risk_gauge_chart(flags), width="stretch")

    # ── Detailed Flags ─────────────────────────────────────
    st.subheader("Risk Details")

    for flag in flags:
        emoji = LEVEL_EMOJI[flag.level]
        with st.expander(f"{emoji} {flag.name} — Score: {flag.score:.0f}/100", expanded=(flag.level == "red")):
            getattr(st, LEVEL_COLOR[flag.level])(flag.explanation)
            st.markdown(f"**Recommendation:** {flag.recommendation}")
