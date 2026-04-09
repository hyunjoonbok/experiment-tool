"""
Experiment Tool — Main Streamlit Entry Point
A suite of interactive experiment design tools for product data scientists.
"""

import streamlit as st

st.set_page_config(
    page_title="Experiment Tool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ── Journey definition ────────────────────────────────────────────────────────
# Each step maps to one tab. state_keys lists session_state entries written when
# that tab has been actively run; empty list means the tab renders inline.

_JOURNEY = [
    {
        "num": 1,
        "icon": "🗂️",
        "label": "Choose your metric",
        "tab": "Metric Recommender",
        "state_keys": [],          # renders inline — always done
        "why": "The metric you choose determines everything downstream.",
    },
    {
        "num": 2,
        "icon": "🛡️",
        "label": "Scan for risks",
        "tab": "Risk Scanner",
        "state_keys": [],          # renders inline
        "why": "Catch SRM, Simpson's paradox, and novelty effects before you start.",
    },
    {
        "num": 3,
        "icon": "⚡",
        "label": "Calculate sample size",
        "tab": "Experiment Planner",
        "state_keys": ["pwr_dur_results", "pwr_sens_results", "pwr_ss_results"],
        "why": "Know how many users and how many days you need.",
    },
    {
        "num": 4,
        "icon": "🧭",
        "label": "Confirm your design",
        "tab": "Causal Selector",
        "state_keys": [],          # renders inline
        "why": "RCT, DiD, or synthetic control? Pick the right method.",
        "optional": True,
    },
    {
        "num": 5,
        "icon": "📈",
        "label": "Plan stopping rules",
        "tab": "Sequential Testing",
        "state_keys": ["seq_results"],
        "why": "If you peek at results, protect your alpha with a valid boundary.",
        "optional": True,
    },
    {
        "num": 6,
        "icon": "🔬",
        "label": "Handle multiple metrics",
        "tab": "Multiple Testing",
        "state_keys": [],          # renders inline
        "why": "Testing 3+ metrics? Apply Bonferroni or Holm correction.",
        "optional": True,
    },
    {
        "num": 7,
        "icon": "🔁",
        "label": "Run an A/A test",
        "tab": "A/A Simulator",
        "state_keys": ["aa_sim_results", "aa_srm_results"],
        "why": "Validate randomization before exposing users to real treatment.",
    },
]


def _step_done(step: dict) -> bool:
    """Return True if this tab has been actively run this session."""
    if not step["state_keys"]:
        return False   # inline tabs — not trackable
    return any(k in st.session_state for k in step["state_keys"])


# ── Sidebar: Design Journey ───────────────────────────────────────────────────

with st.sidebar:
    st.title("🧪 Experiment Tool")
    st.caption("Interactive experiment design for product data scientists.")
    st.divider()

    st.subheader("🗺️ Experiment Design Journey")
    st.caption("Follow these steps to design a rigorous experiment from scratch.")
    st.markdown("")

    for step in _JOURNEY:
        done = _step_done(step)
        optional = step.get("optional", False)
        badge = "✅" if done else ("○" if optional else "●")
        opt_tag = " *(optional)*" if optional else ""
        colour = "#6b7280" if optional and not done else ("#059669" if done else "#1e293b")

        st.markdown(
            f"<span style='color:{colour}'>{badge} **{step['num']}.** "
            f"{step['icon']} {step['label']}{opt_tag}</span>",
            unsafe_allow_html=True,
        )
        st.caption(f"    → **{step['tab']}** tab")

    st.divider()

    st.markdown(
        "**Deep-dive tools**\n"
        "- 🔢 Ratio Variance — delta method vs bootstrap\n"
        "- 📊 DiD Simulator — parallel-trend validation\n"
        "- 🔀 Funnel Simulator — stage-by-stage MAU impact\n"
        "- 📋 Result Analyzer — analyze live experiment results\n",
    )

    st.divider()
    st.caption("All computations run locally — no API keys or external services required.")


# ── Getting Started banner (above tabs) ───────────────────────────────────────

with st.expander(
    "👋 New here? — Open for the Experiment Design Journey guide",
    expanded="__guide_seen" not in st.session_state,
):
    st.session_state["__guide_seen"] = True   # collapse on next rerun

    st.markdown("### How to run a rigorous experiment — start to finish")

    g1, g2, g3, g4, g5 = st.columns(5)
    guide_cols = [g1, g2, g3, g4, g5]
    guide_steps = [
        ("🗂️", "**1. Metric**", "Metric Recommender", "Pick the metric that best captures your hypothesis."),
        ("⚡", "**2. Power**", "Experiment Planner", "Set sample size and runtime before any data is collected."),
        ("🔁", "**3. A/A test**", "A/A Simulator", "Confirm randomization is working. Never skip this."),
        ("📈", "**4. Run**", "Sequential Testing", "Use a valid stopping rule if you plan to peek early."),
        ("🚀", "**5. Ship**", "", "Interpret results using pre-specified metrics and thresholds."),
    ]
    for col, (icon, title, tab, desc) in zip(guide_cols, guide_steps):
        with col:
            st.markdown(f"#### {icon} {title}")
            if tab:
                st.caption(f"→ **{tab}**")
            st.caption(desc)

    st.divider()

    faq_col1, faq_col2 = st.columns(2)
    with faq_col1:
        st.markdown(
            "**I don't know which metric to use →** Start with 🗂️ **Metric Recommender**\n\n"
            "**I need to know how many users →** Go to ⚡ **Experiment Planner**\n\n"
            "**I'm testing 5 metrics at once →** Use 🔬 **Multiple Testing**\n\n"
            "**My traffic split looks off →** Use 🔁 **A/A Simulator → Randomization Check**"
        )
    with faq_col2:
        st.markdown(
            "**I want to check results weekly →** Use 📈 **Sequential Testing**\n\n"
            "**I can't randomise at user level →** Use 🧭 **Causal Selector** or 📊 **DiD Simulator**\n\n"
            "**My metric is clicks/sessions (ratio) →** Use 🔢 **Ratio Variance** first\n\n"
            "**I think my experiment has a bug →** Check 🛡️ **Risk Scanner** + 🔁 **A/A Simulator**"
        )


# ── Helper: next-step hint (rendered inside each tab's `with` block) ──────────

def _next(hint: str) -> None:
    """Render a consistent 'what to do next' nudge at the bottom of a tab."""
    st.divider()
    st.info(f"💡 **What to do next:** {hint}")


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11 = st.tabs([
    "⚡ Experiment Planner",
    "📈 Sequential Testing",
    "🔢 Ratio Variance",
    "🗂️ Metric Recommender",
    "🛡️ Risk Scanner",
    "🧭 Causal Selector",
    "📊 DiD Simulator",
    "🔀 Funnel Simulator",
    "🔬 Multiple Testing",
    "🔁 A/A Simulator",
    "📋 Result Analyzer",
])

with tab1:
    from ui.tab_power import render as render_power
    render_power()
    _next(
        "If you plan to check results before the experiment ends, go to "
        "**📈 Sequential Testing** to define valid stopping thresholds. "
        "If you're testing multiple metrics, go to **🔬 Multiple Testing** to correct your alpha. "
        "When ready to launch, validate your randomisation with **🔁 A/A Simulator**."
    )

with tab2:
    from ui.tab_sequential import render as render_sequential
    render_sequential()
    _next(
        "Record the z-boundary for your chosen boundary type — you'll apply it when you look at live data. "
        "Next, run an **🔁 A/A Simulator** to confirm p-values are calibrated before launch. "
        "If testing several metrics simultaneously, also visit **🔬 Multiple Testing**."
    )

with tab3:
    from ui.tab_ratio import render as render_ratio
    render_ratio()
    _next(
        "Take the estimated variance back to **⚡ Experiment Planner** and enter it as your Baseline Std Dev "
        "to get an accurate sample size for ratio metrics. "
        "If your ratio metric shows high variance, CUPED (R² setting in the Planner) can help substantially."
    )

with tab4:
    from ui.tab_recommender import render as render_recommender
    render_recommender()
    _next(
        "Once you've chosen your primary and guardrail metrics, go to **⚡ Experiment Planner** "
        "to calculate the sample size you'll need to detect a meaningful lift. "
        "Then check **🛡️ Risk Scanner** for experiment design pitfalls specific to your scenario."
    )

with tab5:
    from ui.tab_risk import render as render_risk
    render_risk()
    _next(
        "Address any red or yellow flags before proceeding. "
        "If SRM risk is flagged, plan to use the **🔁 A/A Simulator → Randomization Check** before launch. "
        "If cannibalization or novelty concerns appear, revisit your experiment scope in **🧭 Causal Selector**. "
        "Once risks are managed, go to **⚡ Experiment Planner** to lock in your sample size."
    )

with tab6:
    from ui.tab_causal import render as render_causal
    render_causal()
    _next(
        "If the recommended design is a randomised experiment (RCT), proceed to **⚡ Experiment Planner** "
        "to size it. If DiD or synthetic control is recommended, use **📊 DiD Simulator** to stress-test "
        "the parallel-trend assumption before committing to that approach."
    )

with tab7:
    from ui.tab_did import render as render_did
    render_did()
    _next(
        "If the pre-trend violation is small (bias < 5% of effect size), your DiD design is defensible. "
        "Go to **⚡ Experiment Planner** to confirm the required number of units and time periods. "
        "For funnel-level impact, combine DiD estimates with **🔀 Funnel Simulator**."
    )

with tab8:
    from ui.tab_funnel import render as render_funnel
    render_funnel()
    _next(
        "Use the net MAU delta and revenue estimates here to frame the business case for your experiment. "
        "Bring the estimated effect size back to **⚡ Experiment Planner** to confirm you're powered to "
        "detect it. For stage-specific metric recommendations, visit **🗂️ Metric Recommender**."
    )

with tab9:
    from ui.tab_mtc import render as render_mtc
    render_mtc()
    _next(
        "Record the adjusted alpha threshold for each of your metrics — these are the p-value cutoffs "
        "you'll apply when reading out results. Before launch, run **🔁 A/A Simulator** to confirm the "
        "corrected thresholds are well-calibrated for your traffic and metric type."
    )

with tab10:
    from ui.tab_aa import render as render_aa
    render_aa()
    _next(
        "If the A/A simulation shows a well-calibrated FPR and no SRM — you're ready to launch. "
        "Keep the Randomization Check handy during the experiment: re-run it on observed traffic counts "
        "every few days to catch any randomization drift early. "
        "After the experiment, use **🗂️ Metric Recommender** and **🛡️ Risk Scanner** for the next one."
    )

with tab11:
    from ui.tab_results import render as render_results
    render_results()
    _next(
        "Results look good? Use **🔁 A/A Simulator → Randomization Check** to confirm the traffic split was clean. "
        "For the next experiment, start fresh at **🗂️ Metric Recommender**."
    )
