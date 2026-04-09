---
name: implement-feature
description: Implement a new feature or improvement in the experiment tool — Python math engines in tools/, Streamlit UI in ui/tab_*.py, or Altair charts in utils/charts.py. Use this skill when writing new code, modifying existing tabs, adding chart functions, extending math engines, or integrating UX/visual specs into working Streamlit code. Trigger when: "implement the UX spec for X", "add this chart to the funnel tab", "build the new Y feature", "code the visual spec for Z", "update tab X to add Y", "write the math engine for W".
---

# Implement Feature Skill

## Purpose

Translate UX specs, visual specs, and research briefs into working, convention-compliant Python code for the experiment tool.

## Pre-Implementation Checklist

Before writing a single line of code:
- [ ] Read the target file(s) in full (never edit blind)
- [ ] Read the UX spec (`_workspace/ux_*.md`) if it exists
- [ ] Read the visual spec (`_workspace/visual_*.md`) if it exists
- [ ] Identify all widget keys already in use in the target file
- [ ] Identify all session state keys already in use
- [ ] Check `utils/charts.py` for existing chart functions that can be reused

## Implementation Rules by Layer

### Layer A: `tools/` — Math Engine

- **No Streamlit imports** — pure Python/NumPy/SciPy only
- **Vectorized, not looped** — generate all `n_sim` experiments as a 2D array `(n_sim, n_per_arm)`, not a Python for-loop
- **Type annotations optional** — add them only if the file already uses them
- **Return simple types** — `float`, `int`, `list[dict]`, `dict`. Don't return DataFrames from tools/ (import pandas only in utils/charts.py)
- **Deterministic by default** — use `np.random.default_rng(42)` as the default RNG; accept an optional `rng` parameter for reproducibility

```python
# GOOD — vectorized
ctrl = rng.normal(mean, std, (n_sim, n_per_arm))  # (n_sim, n_per_arm)
t_stats = (ctrl.mean(axis=1) - treat.mean(axis=1)) / pooled_se  # (n_sim,)

# BAD — Python loop
for i in range(n_sim):
    ctrl = rng.normal(mean, std, n_per_arm)
    ...
```

### Layer B: `ui/tab_*.py` — Streamlit UI

**Widget key rules:**
- Every interactive widget (`st.slider`, `st.selectbox`, `st.number_input`, `st.select_slider`, `st.radio`, `st.checkbox`, `st.text_input`) must have `key=`
- Format: `{tab_prefix}_{widget_snake_case}` (e.g., `pwr_alpha`, `seq_alpha_spending`)
- Sub-tab widgets: `{tab_prefix}_{subtab_prefix}_{widget}` (e.g., `pwr_dur_mde`)
- If adding a widget that already exists in a sibling sub-tab, add a distinct prefix

**Simulation gating pattern:**
```python
if st.button("Run Simulation", type="primary", key="run_{tab}"):
    with st.spinner("Computing..."):
        result = tools_function(...)
    st.session_state["{tab}_results"] = result

if "{tab}_results" in st.session_state:
    result = st.session_state["{tab}_results"]
    # render charts and metrics
```

**Never call heavy tools/ functions unconditionally** (they run on every Streamlit rerun).

**Column layout:** Use `st.columns([ratio1, ratio2])` for side-by-side layout. Left column: input controls specific to sub-tab. Right column: hero output (`st.metric()`).

**Progressive disclosure:** Use `st.expander()` for explanations, methodology, and secondary content.

### Layer C: `utils/charts.py` — Altair Charts

**Function signature pattern:**
```python
def {name}_chart(rows: list, param: type = default) -> alt.Chart:
    """One-line description."""
    import pandas as pd
    import altair as alt
    df = pd.DataFrame(rows)
    # ... build layers ...
    return alt.layer(*layers).properties(title="...", height=350).configure_view(strokeWidth=0)
```

**Layer composition:**
```python
layer1 = base.mark_rect().encode(...)
layer2 = base.mark_line().encode(...)
layer3 = base.mark_text().encode(...)
# ALWAYS compose before configure_view
chart = alt.layer(layer1, layer2, layer3).properties(...).configure_view(strokeWidth=0)
return chart  # configure_view is the final call — nothing after this
```

**Data prep stays in chart functions** — DataFrames, column renaming, computed columns. Keep tools/ clean.

## Post-Implementation Checklist

- [ ] No `StreamlitDuplicateElementId` — all widget keys are unique
- [ ] No unconditional simulation calls
- [ ] No Python loops in simulation code
- [ ] `.configure_view(strokeWidth=0)` is the final call in every chart function
- [ ] `st.altair_chart(chart, width="stretch")` — not `use_container_width=True`
- [ ] New tools/ functions have no Streamlit imports
- [ ] Implementation notes saved to `_workspace/impl_{feature}.md`

## Writing Implementation Notes

Save to `_workspace/impl_{feature}.md`:

```markdown
# Implementation Notes: {Feature}
Date: {date}

## Files Changed
- `tools/power_simulator.py`: Added `feasibility_curve()` (lines 273–313)
- `utils/charts.py`: Added `feasibility_zone_chart()` (lines 210–270)
- `ui/tab_power.py`: Replaced `_tradeoff_section()` with per-sub-tab chart sections

## New Widget Keys Introduced
- `pwr_dur_mde` (st.slider in sub-tab 1)
- `run_dur` (st.button in sub-tab 1)

## New Session State Keys
- `pwr_dur_results`

## Deviations from Spec
- Zone label positioning: used x_label column instead of Altair's mark_text dx offset (Altair 5 doesn't support right-anchor text on quantitative axes cleanly)

## Smoke Test
- `streamlit run app.py` ran without errors
- All 8 tabs loaded
- Sub-tab 1 feasibility chart rendered with zone bands and orange highlight
```
