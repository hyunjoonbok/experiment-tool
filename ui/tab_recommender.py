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

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **What this tool does:** Given your feature type and funnel stage, this tool recommends a
        curated metric plan: one primary metric, supporting secondary metrics, guardrail metrics,
        and leading/lagging indicators. It uses a rule-based lookup table keyed by
        (feature_type × funnel_stage) pairs, built from experimentation best practices.

        **Primary vs Secondary vs Guardrail:**
        - **Primary metric**: The single metric your experiment is powered to detect. Choosing one
          (and only one) primary metric before the experiment controls the false discovery rate.
          More than one primary metric inflates Type I error.
        - **Secondary metrics**: Directional signals that help you understand *why* the primary moved.
          They are not decision criteria — they provide context.
        - **Guardrail metrics**: Metrics that must not degrade. Even if your primary metric improves,
          a guardrail violation (e.g., latency increase, support ticket spike) may be grounds to block launch.

        **Why choosing the right primary metric matters:** The primary metric defines what you are
        optimizing. A poorly chosen primary metric can lead to shipping features that improve a proxy
        but hurt the business outcome you actually care about.

        **When to use this tool:** At the experiment design stage, before writing the experiment spec.
        Copy the recommended metric plan into your spec document and adjust definitions as needed.
        """)

    col1, col2, col3 = st.columns(3)

    with col1:
        feature_type = st.selectbox(
            "Feature Type",
            list_feature_types(),
            format_func=lambda x: FEATURE_TYPE_LABELS.get(x, x.title()),
            help="The broad category of feature you are testing. Engagement = features that increase user interaction. Monetization = features that affect revenue. AI/ML Usage = model-powered features. Retention = features targeting churn. Migration = moving users between surfaces or products. Marketplace = supply/demand matching features.",
        )

    with col2:
        funnel_stage = st.selectbox(
            "Funnel Stage",
            list_funnel_stages(),
            format_func=lambda x: FUNNEL_STAGE_LABELS.get(x, x.title()),
            help="Where in the user lifecycle your feature operates. Awareness = top of funnel, new user discovery. Acquisition = first-time sign-up or install. Activation = first meaningful action. Retention = repeat engagement. Revenue = monetization events. Referral = viral sharing or invite behavior.",
        )

    with col3:
        surface = st.selectbox(
            "Surface",
            SURFACE_LABELS,
            help="Surface is recorded in the metric plan export. Metric rules are currently feature-type × funnel-stage based and do not vary by surface.",
        )

    st.divider()

    bundle = get_metric_bundle(feature_type, funnel_stage)

    if bundle.notes:
        st.info(f"Note: {bundle.notes}")
    else:
        st.caption(f"Showing metrics for: **{FEATURE_TYPE_LABELS.get(feature_type, feature_type)}** × **{FUNNEL_STAGE_LABELS.get(funnel_stage, funnel_stage)}** on **{surface}**")

    # ── Primary Metric ───────────────────────────────────
    st.subheader("Primary Metric")
    st.markdown(f"### {bundle.primary_metric}")
    st.markdown(f"> {bundle.primary_definition}")

    st.markdown(
        "**Why one primary metric?** Committing to a single primary metric before the experiment "
        "is a statistical best practice. Every additional metric you test as a primary outcome "
        "inflates your false positive rate — with 5 primary metrics each at α=0.05, your "
        "experiment-wide false positive rate approaches 23%. One primary metric keeps the "
        "decision rule clean and the interpretation honest. Ensure the definition is precise "
        "(exact numerator, denominator, time window, and eligible user population) so there "
        "is no ambiguity when you read out results."
    )

    st.divider()

    # ── Secondary & Guardrail ────────────────────────────
    st.markdown(
        "**Secondary metrics** provide directional context — they help you understand *why* "
        "the primary metric moved, but they are not decision criteria. "
        "**Guardrail metrics** are hard constraints — a statistically significant degradation "
        "in a guardrail is grounds to block launch even if the primary metric improves."
    )

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
    st.markdown(
        "**Leading indicators** move quickly — often within the first few days of an experiment. "
        "Monitor them during ramp to get an early signal before the full experiment completes. "
        "**Lagging indicators** reflect longer-term behavior (e.g., 30-day retention, LTV). "
        "They are less useful for experiment readouts but critical for post-launch monitoring "
        "to confirm that short-term gains hold over time."
    )

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
        st.markdown(
            "**Why duration matters:** Running an experiment for less than one full business cycle "
            "(typically 7 days) biases results because weekday and weekend behavior differ. "
            "For AI and new features, **novelty effects** inflate early engagement — users interact "
            "more simply because the feature is new, not because it is better. Allow at least 2 weeks "
            "for novelty effects to decay. The 50% buffer rule of thumb accounts for both business "
            "cycle completeness and novelty effect decay."
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
