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

    with st.expander("📖 About this tool", expanded=False):
        st.markdown("""
        **What this tool does:** Before you launch an experiment, this scanner checks your design
        against 6 common failure modes that cause experiment results to be unreliable or
        uninterpretable. It assigns a risk score (0–100) and severity level to each check.

        **Why run a risk audit?** Shipping an experiment with a design flaw doesn't just waste
        engineering time — it can produce false positives that lead to bad product decisions.
        A 5-minute pre-launch audit catches the most common issues.

        **Severity levels:**
        - 🔴 **Red (Critical):** Your results are likely unreliable. Fix this before launching.
        - 🟡 **Yellow (Warning):** A potential issue that may bias results. Mitigate if possible.
        - 🟢 **Green (Clear):** This check passed. No action needed.

        **The 6 checks this tool runs:**
        1. **SRM (Sample Ratio Mismatch):** Actual arm sizes differ from expected allocation — usually signals a randomization bug or a logging issue.
        2. **Simpson's Paradox:** The overall result may contradict segment-level results due to an omitted confounding variable.
        3. **Cannibalization:** Treatment may be affecting control through shared inventory, budget, or user behavior.
        4. **Novelty Effect:** Users behave differently just because the feature is new — not because it is better. Inflates early metrics.
        5. **SUTVA Violation:** One user's treatment status affects another user's outcome (network effects, social features).
        6. **Low-Power Guardrail:** You have guardrail metrics but may lack statistical power to detect degradation in them.
        """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Traffic & Allocation")
        n_control = st.number_input(
            "Control Arm Size (n)",
            min_value=10,
            value=5000,
            step=100,
            help="Actual number of users assigned to the control arm. Used to detect Sample Ratio Mismatch (SRM). If this differs substantially from what the randomization system intended, a bug may be present.",
            key="rsk_n_control",
        )
        n_treatment = st.number_input(
            "Treatment Arm Size (n)",
            min_value=10,
            value=5050,
            step=100,
            help="Actual number of users assigned to the treatment arm. Compare to control arm size — a large imbalance relative to the expected split is a red flag for SRM. For a 50/50 split, both arms should be very close in size.",
            key="rsk_n_treatment",
        )
        expected_allocation = st.slider(
            "Expected Control Allocation (%)",
            30,
            70,
            50,
            help="The intended fraction of traffic assigned to control. For a standard 50/50 experiment, set to 50%. For a 10% treatment holdout, set to 90%. The scanner uses this to compute the SRM chi-squared test.",
            key="rsk_expected_allocation",
        ) / 100

        st.subheader("Segmentation")
        n_segments = st.slider(
            "Number of Segments Analyzed",
            1,
            20,
            3,
            help="How many post-hoc segments you plan to analyze (e.g., country, device, user tier). Each additional segment increases the risk of Simpson's paradox and multiple comparison inflation. Keep below 5 for low risk.",
            key="rsk_n_segments",
        )
        segment_size_imbalance = st.slider(
            "Segment Size Imbalance (0=balanced, 1=extreme)",
            0.0,
            1.0,
            0.2,
            step=0.1,
            help="How unevenly sized your segments are. 0 = all segments same size. 1 = one segment dominates. High imbalance combined with high metric-segment correlation is the classic setup for Simpson's paradox. Values above 0.5 are risky.",
            key="rsk_segment_imbalance",
        )
        metric_correlation = st.slider(
            "Metric–Segment Correlation",
            -1.0,
            1.0,
            0.3,
            step=0.1,
            help="Correlation between segment membership and the outcome metric. High correlation (>0.5) means segments have very different baseline metric values — a prerequisite for Simpson's paradox. Estimate from historical data.",
            key="rsk_metric_correlation",
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
            help="The unit of randomization. User-level is safest for most features because it prevents the same person from seeing both treatment and control. Session-level is risky because repeat users will experience both variants, causing contamination. Geo-level is appropriate when network effects or marketplace dynamics make user-level randomization unreliable.",
            key="rsk_randomization_unit",
        )
        feature_type = st.selectbox(
            "Feature Type",
            ["engagement", "monetization", "ai_usage", "retention", "migration", "marketplace", "social", "referral"],
            format_func=lambda x: x.replace("_", " ").title(),
            help="The type of feature being tested. This determines which risk checks are most relevant. Social and marketplace features have high SUTVA violation risk. AI/ML features have high novelty effect risk. Monetization features trigger cannibalization checks.",
            key="rsk_feature_type",
        )
        experiment_duration_days = st.slider(
            "Planned Experiment Duration (days)",
            1,
            60,
            14,
            help="How many days you plan to run the experiment. Experiments shorter than 7 days miss a full business cycle (weekday vs weekend behavior differs). Experiments shorter than 14 days for new features may be dominated by novelty effects. 14–21 days is the standard minimum.",
            key="rsk_duration_days",
        )
        is_new_feature = st.checkbox(
            "This is a brand-new feature (higher novelty risk)",
            value=True,
            help="Check this if users have never seen this feature before. New features often see inflated early engagement because users are curious, not because the feature is better. This novelty effect typically decays over 1–2 weeks and can cause false positives if the experiment is too short.",
            key="rsk_is_new_feature",
        )

        st.subheader("Metric Properties")
        metric_type = st.text_input(
            "Primary Metric Name",
            value="click_through_rate",
            help="Used to assess metric gaming vulnerability (e.g., 'ctr', 'revenue', 'retention')",
            key="rsk_metric_type",
        )
        has_pre_experiment_data = st.checkbox(
            "Pre-experiment data available (CUPED eligible)",
            value=True,
            help="Check this if you have historical metric data for the same users before the experiment started. Pre-experiment data enables CUPED (Controlled-experiment Using Pre-Experiment Data), which can reduce variance by 20–50% and increase effective power. Without it, you may be underpowered for guardrail metrics.",
            key="rsk_pre_exp_data",
        )

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

    st.caption(
        "**Critical risks (red)** mean your experiment results are likely unreliable or uninterpretable — "
        "do not make ship/no-ship decisions based on a flawed experiment. "
        "**Warnings (yellow)** are issues worth noting but may not require blocking the launch; use judgment "
        "based on the specific check and your product context. "
        "**Green** means that particular check passed — it does not guarantee the overall experiment is valid."
    )

    # ── Gauge Chart ────────────────────────────────────────
    st.altair_chart(risk_gauge_chart(flags), width="stretch")

    # ── Detailed Flags ─────────────────────────────────────
    st.subheader("Risk Details")

    st.info(
        "**What to do after this scan:** Fix all 🔴 red flags before launching — these represent "
        "fundamental design flaws that invalidate your results. 🟡 Yellow flags are judgment calls: "
        "document your reasoning for accepting the risk and add notes to your experiment spec. "
        "🟢 Green flags mean the check passed — no action needed for those items."
    )

    for flag in flags:
        emoji = LEVEL_EMOJI[flag.level]
        with st.expander(f"{emoji} {flag.name} — Score: {flag.score:.0f}/100", expanded=(flag.level == "red")):
            getattr(st, LEVEL_COLOR[flag.level])(flag.explanation)
            st.markdown(f"**Recommendation:** {flag.recommendation}")
