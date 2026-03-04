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

# ── Sidebar: Global Settings ─────────────────────────────
with st.sidebar:
    st.title("🧪 Experiment Tool")
    st.caption("Interactive tools for product data scientists.")
    st.divider()

    st.subheader("Global Settings")
    global_alpha = st.slider("Default α (significance level)", 0.01, 0.10, 0.05, step=0.01)
    global_power = st.slider("Default Target Power", 0.60, 0.99, 0.80, step=0.05)
    global_n_sim = st.select_slider(
        "Default Simulation Runs",
        options=[500, 1000, 2000, 5000],
        value=2000,
        help="Higher = more accurate but slower. 2000 is a good balance.",
    )

    st.divider()
    st.markdown("""
    **Experiment Design**
    1. Power & MDE Simulator
    2. Sequential Testing
    3. Ratio Metric Variance
    4. Metric Recommender
    5. Risk Scanner

    **Causal Inference**

    6. Causal Design Selector
    7. DiD & Synthetic Control

    **Funnel & Product**

    8. Funnel Transition Simulator
    """)
    st.divider()
    st.caption("Built for product data scientists. All computations run locally.")

# ── Tabs ─────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
    "⚡ Power & MDE",
    "📈 Sequential Testing",
    "🔢 Ratio Variance",
    "🗂️ Metric Recommender",
    "🛡️ Risk Scanner",
    "🧭 Causal Selector",
    "📊 DiD Simulator",
    "🔀 Funnel Simulator",
])

# Lazy imports to keep startup fast
with tab1:
    from ui.tab_power import render as render_power
    render_power()

with tab2:
    from ui.tab_sequential import render as render_sequential
    render_sequential()

with tab3:
    from ui.tab_ratio import render as render_ratio
    render_ratio()

with tab4:
    from ui.tab_recommender import render as render_recommender
    render_recommender()

with tab5:
    from ui.tab_risk import render as render_risk
    render_risk()

with tab6:
    from ui.tab_causal import render as render_causal
    render_causal()

with tab7:
    from ui.tab_did import render as render_did
    render_did()

with tab8:
    from ui.tab_funnel import render as render_funnel
    render_funnel()
