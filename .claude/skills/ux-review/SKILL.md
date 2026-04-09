---
name: ux-review
description: Audit and redesign the UX of a tab or feature in the experiment tool. Use this skill when reviewing a tab's user flow, designing how inputs map to outputs, defining widget layout and information hierarchy, specifying progressive disclosure patterns, or ensuring consistency across tabs. Trigger when: "UX of tab X is confusing", "how should we lay out the new feature", "what widgets does this tab need", "improve the information flow", "design the interaction for Y".
---

# UX Review Skill

## Purpose

Produce a UX spec that the Visual Designer and Software Engineer can act on without ambiguity — not a mood board or general guidance, but a concrete layout and interaction design.

## Process

### Step 1: Audit the current state
Read the relevant `ui/tab_*.py` file and identify:
- **What works**: patterns already well-executed (good progressive disclosure, clear hero metric, etc.)
- **What doesn't**: cognitive overload, buried key numbers, missing empty states, inconsistency with other tabs
- **Consistency check**: compare against 2–3 other tabs to spot divergences in patterns

### Step 2: Define the user journey
Map the end-to-end flow:
```
[User arrives at tab]
  → [Sees: global context / what this tab does — 1 sentence]
  → [Configures: inputs in sidebar or top section]
  → [Triggers: "Run" button]
  → [Sees: hero output — the most critical number/decision]
  → [Explores: supporting charts with interpretation]
  → [Reads: explanations in expanders if needed]
```

### Step 3: Widget inventory
List every widget the tab needs:

| Widget type | Label | Default | Key prefix | Placement |
|-------------|-------|---------|-----------|-----------|
| st.selectbox | Metric Type | binary | pwr_ | Shared params |
| st.slider | Alpha | 0.05 | pwr_ | Shared params |
| ... | ... | ... | ... | ... |

Rules:
- Key prefixes: `pwr_` (power), `seq_` (sequential), `rat_` (ratio), `did_` (DiD), `fun_` (funnel), `csl_` (causal), `rsk_` (risk), `rec_` (recommender)
- Add `_{widget_label_snake_case}` suffix for uniqueness within a tab
- Sub-tab widgets need an additional prefix: `pwr_dur_`, `pwr_sens_`, `pwr_ss_`

### Step 4: Output layout
Specify the output area structure using a hierarchy:

```
st.header("Tab Title")
  st.expander("About this tool")
  [shared params section]
  st.divider()
  sub1, sub2, sub3 = st.tabs(["...", "...", "..."])
    with sub1:
      col_left, col_right = st.columns([1, 2])
        col_left: [input widgets specific to this sub-tab]
        col_right: [hero metric in st.metric()]
      st.divider()
      st.subheader("Chart Section Title")
      [chart + expander]
```

### Step 5: Progressive disclosure plan
Define three tiers:
- **Tier 1 (always visible):** Hero number, critical decision
- **Tier 2 (visible but secondary):** Supporting charts, comparison tables
- **Tier 3 (in expanders):** Statistical explanation, business framing, methodology notes

### Step 6: Edge cases
Document behavior for:
- Empty state (no run yet): show placeholder text or greyed-out chart
- Loading state: use `st.spinner("Computing...")`
- Error state: what if daily_traffic=0, or n_per_arm is too small?
- Extreme values: what if power=100% or MDE=0%?

### Step 7: Write the spec
Save to `_workspace/ux_{tab_or_feature}.md`:

```markdown
# UX Spec: {Tab or Feature Name}
Date: {date}

## Current State Audit
### What Works
- ...
### Issues Found
- ...
### Consistency Gaps (vs. other tabs)
- ...

## Proposed User Flow
[Step-by-step or ASCII diagram]

## Widget Inventory
[Table from Step 3]

## Output Layout
[Indented hierarchy from Step 4]

## Progressive Disclosure Plan
[Tier 1/2/3 breakdown]

## Edge Cases
[List from Step 6]

## Open Questions
[Anything that needs Visual Designer or Software Engineer input]
```

## Quality Bar

A good UX spec:
- Can be handed to a developer who has never seen the tab and they know exactly what to build
- Every widget has a key, default, and placement specified
- Every possible user state (empty, loading, error, success) is addressed
- Decision-making is front-and-center: the first thing a user sees after running tells them what to do

A weak UX spec:
- Says "show a chart here" without specifying what type, what data, what title
- Doesn't address the empty/error state
- Uses vague language like "make it cleaner" without specific changes
