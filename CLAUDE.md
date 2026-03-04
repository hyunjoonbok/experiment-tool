# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
# Install dependencies
pip3 install -r requirements.txt

# Launch
streamlit run app.py
```

No build step, no test suite, no linter configured. The app runs entirely locally — no API keys or external services required.

## Architecture

This is a single-page Streamlit app (`app.py`) with 8 tabs. Each tab is a self-contained module under `ui/` that calls pure-Python math engines under `tools/`. Charts are built in `utils/charts.py` using Altair 5.x (pinned `<6.0.0` — Streamlit's bundled Vega-Lite renderer is v5).

```
app.py              # Entry point: sets page config, sidebar, declares 8 tabs, lazy-imports ui/
tools/              # Math engines — no Streamlit imports, pure NumPy/SciPy
ui/                 # One file per tab, each exports a single render() function
utils/charts.py     # All Altair chart constructors, return alt.Chart objects
```

**Data flow per tab:** user widgets → `render()` calls `tools/` functions → results passed to `utils/charts.*_chart()` → `st.altair_chart(chart, width="stretch")`.

## Key conventions

**Widget keys**: Every `st.slider`, `st.selectbox`, `st.number_input`, and `st.select_slider` must have a unique `key=` argument prefixed by tab abbreviation (e.g. `pwr_`, `seq_`, `rat_`, `did_`, `fun_`). Streamlit raises `StreamlitDuplicateElementId` if two widgets across tabs share the same label + parameters without explicit keys.

**Simulation gating**: Heavy computations are behind a `st.button("Run Simulation", type="primary", key="run_<tab>")` and results cached in `st.session_state["<tab>_results"]`. Do not call simulation functions unconditionally on render — all 8 tabs execute on every Streamlit rerun.

**Performance**: `tools/` functions use vectorized NumPy (generate all `n_sim` experiments in a single array op). Never add Python `for _ in range(n_sim)` loops — use broadcasting or matrix ops. Binary and continuous metrics use analytical power formulas (instant); only ratio metrics use Monte Carlo.

**Charts**: Use `width="stretch"` (not `use_container_width=True`, deprecated). Each chart function in `utils/charts.py` calls `.configure_view(strokeWidth=0)` — this returns a top-level chart that can't be composed further, so build the full chart before calling it.

## Tools (tabs) overview

| Tab | Tool | `tools/` module | Key output |
|-----|------|-----------------|------------|
| 1 | Power & MDE | `power_simulator.py` | Power curve, sensitivity heatmap, MDE at fixed N |
| 2 | Sequential Testing | `sequential_testing.py` | Alpha spending table, type I error inflation, stopping distribution |
| 3 | Ratio Variance | `ratio_variance.py` | Delta method vs bootstrap variance decomposition |
| 4 | Metric Recommender | `metric_recommender.py` | Rule-based `(feature_type, funnel_stage) → MetricBundle` lookup |
| 5 | Risk Scanner | `risk_scanner.py` | 6 `RiskFlag` objects (SRM, Simpson's, cannibalization, novelty, etc.) |
| 6 | Causal Selector | `causal_selector.py` | Decision tree → recommended design + assumptions + model spec |
| 7 | DiD Simulator | `did_simulator.py` | Bias/power under parallel trend violations |
| 8 | Funnel Simulator | `funnel_simulator.py` | Net MAU delta, revenue delta, uplift × decay sensitivity |

## Extending the app

**Adding a new tool:**
1. Create `tools/new_tool.py` with pure math functions (no Streamlit).
2. Create `ui/tab_new.py` with a `render()` function; prefix all widget keys with a unique abbreviation.
3. Add any new chart constructors to `utils/charts.py` following the existing pattern (return `alt.Chart`, end with `.configure_view(strokeWidth=0)`).
4. In `app.py`, add a new tab to `st.tabs([...])`, unpack it, and add a `with tab_n:` block with a lazy import of `render`.

**Metric Recommender rules** (`tools/metric_recommender.py`): The lookup table `METRIC_RULES` is keyed by `(feature_type, funnel_stage)` tuples. Add new combinations directly to that dict as `MetricBundle` instances. The fallback for unmatched combinations is `_DEFAULT_BUNDLE`.
