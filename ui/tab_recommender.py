"""
UI Tab 4: Feature → Metric Recommender
"""

import streamlit as st
from tools.metric_recommender import (
    get_metric_bundle,
    list_feature_types,
    list_funnel_stages,
    bundle_to_dict,
)


FEATURE_TYPE_LABELS = {
    "engagement": "Engagement",
    "monetization": "Monetization",
    "ai_usage": "AI / ML Usage",
    "retention": "Retention",
    "migration": "Migration",
    "marketplace": "Marketplace",
}

FUNNEL_STAGE_LABELS = {
    "awareness": "Awareness",
    "acquisition": "Acquisition",
    "activation": "Activation",
    "retention": "Retention",
    "revenue": "Revenue",
    "referral": "Referral",
}

SURFACE_LABELS = ["Mobile", "Desktop", "Creator", "Viewer", "Both"]


def render():
    st.header("Feature → Metric Recommender")
    st.caption(
        "Describe your feature and get a curated set of primary, secondary, and guardrail metrics, "
        "along with suggested experiment duration and known risks."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_type = st.selectbox(
            "Feature Type",
            list_feature_types(),
            format_func=lambda x: FEATURE_TYPE_LABELS.get(x, x.title()),
        )

    with col2:
        funnel_stage = st.selectbox(
            "Funnel Stage",
            list_funnel_stages(),
            format_func=lambda x: FUNNEL_STAGE_LABELS.get(x, x.title()),
        )

    with col3:
        surface = st.selectbox("Surface", SURFACE_LABELS)

    st.divider()

    bundle = get_metric_bundle(feature_type, funnel_stage)

    if bundle.notes:
        st.info(f"Note: {bundle.notes}")

    # ── Primary Metric ───────────────────────────────────
    st.subheader("Primary Metric")
    st.markdown(f"### {bundle.primary_metric}")
    st.markdown(f"> {bundle.primary_definition}")

    st.divider()

    # ── Secondary & Guardrail ────────────────────────────
    col_sec, col_guard = st.columns(2)

    with col_sec:
        st.subheader("Secondary Metrics")
        for m in bundle.secondary_metrics:
            st.markdown(f"- {m}")

    with col_guard:
        st.subheader("Guardrail Metrics")
        for m in bundle.guardrail_metrics:
            st.markdown(f"- {m}")

    st.divider()

    # ── Leading vs Lagging ───────────────────────────────
    col_lead, col_lag = st.columns(2)

    with col_lead:
        st.subheader("Leading Indicators")
        st.caption("Move first — useful for early signal during ramp.")
        for m in bundle.leading_indicators:
            st.markdown(f"- {m}")

    with col_lag:
        st.subheader("Lagging Indicators")
        st.caption("Move later — use for post-launch monitoring.")
        for m in bundle.lagging_indicators:
            st.markdown(f"- {m}")

    st.divider()

    # ── Duration & Risk ──────────────────────────────────
    dur_col, risk_col = st.columns(2)

    with dur_col:
        st.subheader("Suggested Experiment Duration")
        st.metric("Minimum Days", bundle.suggested_duration_days)
        st.caption(
            "This is the minimum for a full business cycle. "
            "Add 50% buffer for AI/novelty-prone features."
        )

    with risk_col:
        st.subheader("Risk Metrics to Watch")
        for r in bundle.risk_metrics:
            st.markdown(f"- {r}")

    st.divider()

    # ── Export ───────────────────────────────────────────
    with st.expander("Export Metric Plan as Text"):
        d = bundle_to_dict(bundle)
        lines = [f"# Metric Plan: {FEATURE_TYPE_LABELS.get(feature_type, feature_type)} | {FUNNEL_STAGE_LABELS.get(funnel_stage, funnel_stage)} | {surface}\n"]
        for k, v in d.items():
            if isinstance(v, list):
                lines.append(f"\n## {k}")
                for item in v:
                    lines.append(f"- {item}")
            else:
                lines.append(f"\n## {k}\n{v}")
        st.code("\n".join(lines), language="markdown")
