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

This is a single-page Streamlit app (`app.py`) with 11 tabs. Each tab is a self-contained module under `ui/` that calls pure-Python math engines under `tools/`. Charts are built in `utils/charts.py` using Altair 5.x (pinned `<6.0.0` — Streamlit's bundled Vega-Lite renderer is v5).

```
app.py              # Entry point: sets page config, sidebar journey, declares 11 tabs, lazy-imports ui/
tools/              # Math engines — no Streamlit imports, pure NumPy/SciPy
ui/                 # One file per tab, each exports a single render() function
utils/charts.py     # All Altair chart constructors, return alt.Chart objects
```

**Data flow per tab:** user widgets → `render()` calls `tools/` functions → results passed to `utils/charts.*_chart()` → `st.altair_chart(chart, width="stretch")`.

## Key conventions

**Widget keys**: Every `st.slider`, `st.selectbox`, `st.number_input`, and `st.select_slider` must have a unique `key=` argument prefixed by tab abbreviation. Current prefixes:

| Tab | Prefix |
|-----|--------|
| Experiment Planner | `pwr_` |
| Sequential Testing | `seq_` |
| Ratio Variance | `rat_` |
| Metric Recommender | `rec_` |
| Risk Scanner | `risk_` |
| Causal Selector | `csl_` |
| DiD Simulator | `did_` |
| Funnel Simulator | `fun_` |
| Multiple Testing | `mtc_` |
| A/A Simulator | `aa_` |
| Result Analyzer | `res_` |

Streamlit raises `StreamlitDuplicateElementId` if two widgets across tabs share the same label + parameters without explicit keys.

**Simulation gating**: Heavy computations are behind a `st.button(..., type="primary", key="run_<tab>")` and results cached in `st.session_state["<tab>_results"]`. Do not call simulation functions unconditionally on render — all 11 tabs execute on every Streamlit rerun.

**Performance**: `tools/` functions use vectorized NumPy (generate all `n_sim` experiments in a single array op). Never add Python `for _ in range(n_sim)` loops — use broadcasting or matrix ops. Binary and continuous metrics use analytical power formulas (instant); only ratio metrics use Monte Carlo.

**Charts**: Use `width="stretch"` (not `use_container_width=True`, deprecated). Each chart function in `utils/charts.py` calls `.configure_view(strokeWidth=0)` — this returns a top-level chart that can't be composed further, so build the full chart before calling it.

## Tools (tabs) overview

| Tab | Tool | `tools/` module | Key output |
|-----|------|-----------------|------------|
| 1 | Experiment Planner | `power_simulator.py` | Runtime, MDE, sample size; feasibility zone chart; power sensitivity matrix |
| 2 | Sequential Testing | `sequential_testing.py` | Alpha spending table, type I error inflation, stopping distribution |
| 3 | Ratio Variance | `ratio_variance.py` | Delta method vs bootstrap variance decomposition |
| 4 | Metric Recommender | `metric_recommender.py` | Rule-based `(feature_type, funnel_stage) → MetricBundle` lookup |
| 5 | Risk Scanner | `risk_scanner.py` | 6 `RiskFlag` objects (SRM, Simpson's, cannibalization, novelty, etc.) |
| 6 | Causal Selector | `causal_selector.py` | Decision tree → recommended design + assumptions + model spec |
| 7 | DiD Simulator | `did_simulator.py` | Bias/power under parallel trend violations |
| 8 | Funnel Simulator | `funnel_simulator.py` | Net MAU delta, revenue delta, uplift × decay sensitivity |
| 9 | Multiple Testing | `multiple_testing.py` | Bonferroni / Šidák / Holm / BH corrections; rejection heatmap |
| 10 | A/A Simulator | `aa_simulator.py` | Empirical FPR, KS uniformity, SRM chi-square check |
| 11 | Result Analyzer | `result_analyzer.py` | Per-metric significance + CI; overall SHIP/DON'T SHIP verdict |

## Sidebar & guided flow

`app.py` renders a `_JOURNEY` list in the sidebar — 7 ordered steps that map to specific tabs. Steps with `state_keys` show a live ✅ once the tab has been actively run this session. Optional steps are marked `○` in grey. A "Getting Started" expander above the tabs renders on first visit only (`__guide_seen` session state flag). Each `with tab_n:` block ends with `_next(hint)` which renders a blue info box pointing to the next recommended tab.

## Session state keys (important for sidebar progress)

| Key | Set by | Meaning |
|-----|--------|---------|
| `pwr_dur_results` | Planner sub-tab 1 | Runtime calculation done |
| `pwr_sens_results` | Planner sub-tab 2 | MDE calculation done |
| `pwr_ss_results` | Planner sub-tab 3 | Sample size calculation done |
| `seq_results` | Sequential Testing | Boundary computation done |
| `aa_sim_results` | A/A Simulator | FPR simulation done |
| `aa_srm_results` | A/A Simulator | SRM check done |
| `res_results` | Result Analyzer | Analysis run |
| `__guide_seen` | app.py | Collapse "Getting Started" on next rerun |

## Extending the app

**Adding a new tool:**
1. Create `tools/new_tool.py` with pure math functions (no Streamlit).
2. Create `ui/tab_new.py` with a `render()` function; prefix all widget keys with a unique abbreviation.
3. Add any new chart constructors to `utils/charts.py` following the existing pattern (return `alt.Chart`, end with `.configure_view(strokeWidth=0)`).
4. In `app.py`, add a new tab to `st.tabs([...])`, unpack it, and add a `with tab_n:` block with a lazy import of `render` and a `_next(...)` call at the end.
5. If the tab writes a session state key, add it to `_JOURNEY` with the appropriate `state_keys` entry so it appears in the sidebar progress tracker.

**Multiple Testing corrections** (`tools/multiple_testing.py`): `apply_all_corrections(p_values, alpha)` returns a dict keyed by method name. Each value is a list of result dicts with keys `metric_index`, `original_p`, `adjusted_threshold`, `rejected`. The method order is defined by `_METHOD_ORDER` in `ui/tab_mtc.py`.

**Result Analyzer verdict logic** (`tools/result_analyzer.py`): `overall_verdict(results)` iterates roles in priority order — guardrail failures override everything and return `DON'T SHIP`. If no North Star metric is defined, verdict is `REVIEW RESULTS`. North Star significant + positive → `SHIP IT`; significant + negative → `DON'T SHIP`; not significant → `INCONCLUSIVE`.

**Metric Recommender rules** (`tools/metric_recommender.py`): The lookup table `METRIC_RULES` is keyed by `(feature_type, funnel_stage)` tuples. Add new combinations directly to that dict as `MetricBundle` instances. The fallback for unmatched combinations is `_DEFAULT_BUNDLE`.

## Harness: Experiment Tool Agent Team

**Goal:** A 4-agent team (researcher + UX designer + visual designer + software engineer) that researches, designs, and implements improvements to this experiment tool.

**Trigger:** Use the `orchestrate` skill for any feature work, UX improvement, chart redesign, research question, or "what should we build next" request. Direct bug fixes or one-line changes can be done without the harness.

**Agents:** `.claude/agents/` — `industry-researcher`, `ux-designer`, `visual-designer`, `software-engineer`

**Skills:** `.claude/skills/` — `orchestrate` (entry point), `research`, `ux-review`, `visual-concept`, `implement-feature`

**Change History:**
| Date | Change | Target | Reason |
|------|--------|--------|--------|
| 2026-04-08 | Initial harness setup | All agents + skills | New harness for experiment tool |
| 2026-04-09 | Added tabs 9–11 + sidebar flow | Multiple Testing, A/A Simulator, Result Analyzer, app.py | Feature additions |
| 2026-04-09 | Decision-oriented visuals for Planner | tab_power.py, power_simulator.py, charts.py | Feasibility zone + power matrix charts |
