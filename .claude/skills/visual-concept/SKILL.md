---
name: visual-concept
description: Design Altair 5.x chart specifications for the experiment tool — chart type selection, layer stack, color encoding, annotation strategy, and tooltip design. Use this skill when designing a new chart, redesigning an existing chart's aesthetics, choosing the right visualization for a statistical output, or specifying how data should be encoded visually. Trigger when: "design a chart for X", "how should we visualize Y", "what chart type for Z data", "improve the aesthetics of the power chart", "add an annotation to the heatmap".
---

# Visual Concept Skill

## Purpose

Produce a concrete, implementable Altair 5.x chart specification — not a wireframe or mood board, but a layer-by-layer blueprint that a software engineer can translate directly into `utils/charts.py`.

## Altair 5.x Constraints (Read First)

These are hard constraints from the project's architecture:

1. **`.configure_view(strokeWidth=0)` is terminal** — it must be the last call. After it, you cannot add layers, properties, or compose further. Design the entire layer stack first.
2. **`width="stretch"`** — charts are rendered with `st.altair_chart(chart, width="stretch")`. Don't hardcode pixel widths.
3. **Ordinal axes can't have quantitative reference lines** — workaround: use `mark_point(filled=False)` on ordinal cells, or duplicate data with a flag column to filter.
4. **Layer charts need consistent data shape** — each layer can have its own data, but type mismatches cause silent rendering failures.
5. **Altair version: 5.x (Vega-Lite 5)** — not Altair 4 or 6. Use `alt.Chart`, `alt.layer()`, `alt.condition()`. Avoid Vega-Lite 6 features.

## Standard Color System

Use this palette consistently across all charts:

| Semantic | Background | Foreground / Stroke |
|----------|-----------|---------------------|
| VIABLE (good) | #d1fae5 | #16a34a |
| PATIENCE (caution) | #fef3c7 | #92400e |
| MARGINAL (warning) | #ffedd5 | #c2410c |
| NOT VIABLE (bad) | #fee2e2 | #dc2626 |
| Boundary / highlight | — | #f97316 (amber-orange) |
| Primary data line | — | #1e293b (dark slate) |
| Secondary / grid | — | #94a3b8 (light slate) |
| Text on dark bg | — | #ffffff |
| Text on light bg | — | #374151 |

## Chart Type Selection Guide

| Data shape | Recommended chart |
|-----------|-----------------|
| Single metric over N (power curve) | `mark_line` + threshold `mark_rule` |
| 2D grid of power values (effect × N) | `mark_rect` heatmap + `mark_text` + `mark_point` boundary |
| Scalar metric × colored zones (feasibility) | `mark_rect` bands + `mark_line` curve + `mark_circle` points |
| Distribution of stopping times | `mark_bar` histogram |
| Categorical comparison | `mark_bar` horizontal |
| Time series with events | `mark_line` + `mark_point` + `mark_rule` for events |
| Variance decomposition | `mark_bar` stacked |
| Funnel stages | `mark_bar` + `mark_text` annotations |

## Process

### Step 1: Clarify the question the chart answers
Write one sentence: "This chart answers: {question}". Examples:
- "How long will the experiment take at different sensitivity levels?"
- "What is my statistical power at each effect size × sample size combination?"

This becomes the chart's subtitle.

### Step 2: Define data shape
Specify the expected input data structure:
```python
# Expected: list of dicts
[
    {"mde_pct": 5, "weeks": 2.3, "n_per_arm": 16100, "zone": "VIABLE"},
    ...
]
```

### Step 3: Design the layer stack
List each layer from bottom to top:

```
Layer 1 (bottom): mark_rect — zone background bands
  data: zone_df (separate DataFrame with y1, y2, x_min, x_max, zone columns)
  x: x_min:Q, x2: x_max:Q, y: y1:Q, y2: y2:Q
  color: zone:N, scale={"domain": [...], "range": ["#d1fae5", ...]}
  opacity: 0.4

Layer 2: mark_text — zone labels
  data: zone_df
  text: zone:N
  x: fixed x position (e.g., x_label column)
  y: midpoint of band
  color: semantic foreground color
  align: "right", fontWeight: "bold"

Layer 3: mark_line — main data curve
  data: main_df
  x: mde_pct:Q, y: weeks:Q
  color: "#1e293b", strokeWidth: 2.5

Layer 4: mark_circle — data points colored by zone
  data: main_df
  x: mde_pct:Q, y: weeks:Q
  color: zone:N (same scale as Layer 1)
  size: 60

Layer 5 (conditional): mark_point — highlighted target point
  data: highlight_df (filtered to target row)
  x: mde_pct:Q, y: weeks:Q
  color: "#f97316", size: 200, filled: True

Layer 6 (conditional): mark_text — annotation on highlight
  data: highlight_df
  text: annotation string (e.g., "n=16,100")
  dx: 8, dy: -10
```

### Step 4: Define axes and scales
```
X axis: title="MDE (% relative lift)", format=".0f", grid=False
Y axis: title="Weeks to significance", domain=[0, 20], zero=True
```

### Step 5: Tooltip design
List tooltip fields and formatting:
```python
tooltip=[
    alt.Tooltip("mde_pct:Q", title="MDE", format=".1f"),
    alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
    alt.Tooltip("n_per_arm:Q", title="N per arm", format=","),
    alt.Tooltip("zone:N", title="Zone"),
]
```

### Step 6: Write the visual spec
Save to `_workspace/visual_{chart_name}.md`:

```markdown
# Visual Spec: {Chart Name}
Date: {date}

## Question This Chart Answers
{One sentence}

## Expected Data Shape
{Python snippet showing dict keys and types}

## Layer Stack
{Layer-by-layer description from Step 3}

## Axes & Scales
{From Step 4}

## Tooltip Design
{From Step 5}

## Color Decisions
{Any deviations from standard palette + rationale}

## Edge Cases
- Empty data: {behavior}
- Single data point: {behavior}
- All same zone: {behavior}

## Altair Code Sketch
{Python pseudocode showing the layer construction}
```

## Quality Bar

A good visual spec:
- The Software Engineer can implement it without asking any follow-up questions
- Every layer is specified (mark type, data, encoding, properties)
- Color choices are semantic (meaning is encoded in color, not arbitrary)
- Edge cases are handled (no empty chart errors, no NaN rendering)

A weak visual spec:
- Says "use a heatmap" without specifying the color scheme, text overlay, or boundary marking
- Doesn't specify tooltip content
- Uses colors that don't match the existing palette
