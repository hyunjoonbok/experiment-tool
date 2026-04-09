---
name: orchestrate
description: Orchestrate the experiment tool agent team to research, design, and implement improvements. Use this skill when the user wants to add a new feature, improve an existing tab, research a statistical approach, redesign UX, create new charts, or evolve the tool in any direction. Also trigger for: "what should we build next", "improve tab X", "add a feature for Y", "research how to do Z", "redesign the UX of W", "re-run the team", "update the implementation", "iterate on the previous result", "make it better", "fix the design". This orchestrator coordinates four agents: industry-researcher, ux-designer, visual-designer, software-engineer.
---

# Experiment Tool Orchestrator

## Team Members
- **industry-researcher** — statistical best practices, industry research
- **ux-designer** — user flows, widget layout, information hierarchy
- **visual-designer** — Altair chart specifications, visual encoding
- **software-engineer** — Python/Streamlit/Altair implementation

## Execution Mode: Hybrid
- **Phase 1–3 (Research + Design):** Agent Team — fan-out parallel research and design, then fan-in synthesis
- **Phase 4 (Implementation):** Software Engineer primary with workspace files as input

---

## Phase 0: Context Check

Before starting, check for existing workspace:

```
_workspace/ exists?
  YES + user requests partial update → PARTIAL RE-RUN (run only affected agents)
  YES + user provides new input/scope → NEW RUN (rename _workspace/ to _workspace_prev/)
  NO → INITIAL RUN (proceed to Phase 1)
```

Read `_workspace/` if it exists to understand what was previously built.

---

## Phase 1: Scope Definition

Determine what the user wants to accomplish. Map to one of these task types:

| Task Type | Phases to run | Primary agents |
|-----------|--------------|----------------|
| Research only | 1–2 | industry-researcher |
| UX redesign | 1–3 (no Phase 2 research if scope is clear) | ux-designer, visual-designer |
| New feature (full) | 1–4 all phases | All 4 agents |
| Chart improvement | 1 (brief), 3, 4 | visual-designer, software-engineer |
| Bug fix / code change | 4 only | software-engineer |

Confirm the task type and scope with yourself before spawning agents.

---

## Phase 2: Research + Design (Agent Team — Fan-Out)

**Execution mode: Agent Team**

Spawn the team in parallel for their respective work:

```python
# Parallel fan-out
TeamCreate(
    team_name="experiment-tool-design",
    members=["industry-researcher", "ux-designer", "visual-designer"]
)

# Assign tasks (can be parallel if independent)
TaskCreate("research-task", assigned_to="industry-researcher",
    description="Research {topic}. Save brief to _workspace/research_{slug}.md")

TaskCreate("ux-task", assigned_to="ux-designer",
    description="Audit and design UX for {tab/feature}. Read research brief when available. Save to _workspace/ux_{slug}.md")

TaskCreate("visual-task", assigned_to="visual-designer",
    description="Design chart(s) for {feature}. Read UX spec when available. Save to _workspace/visual_{slug}.md")
```

**Data flow within the team:**
- Researcher → saves `_workspace/research_{slug}.md` → notifies UX Designer and Visual Designer via SendMessage
- UX Designer → reads research brief, saves `_workspace/ux_{slug}.md` → notifies Visual Designer via SendMessage
- Visual Designer → reads UX spec and research brief, saves `_workspace/visual_{slug}.md` → notifies Orchestrator

**Fan-in:** When all three workspace files exist, review and synthesize:
- Check alignment: does the visual spec implement the UX layout?
- Check alignment: does the UX layout reflect the research recommendations?
- If misaligned: send correction via SendMessage to the relevant agent
- When aligned: proceed to Phase 3

---

## Phase 3: Implementation (Software Engineer Primary)

**Execution mode: Subagent (Software Engineer)**

```python
Agent(
    subagent_type="general-purpose",
    model="opus",
    prompt="""
You are the software-engineer agent for the experiment tool.
Read these workspace files:
- _workspace/research_{slug}.md (if exists)
- _workspace/ux_{slug}.md
- _workspace/visual_{slug}.md

Then read the relevant source files:
- {list of files to modify}

Implement the feature following the implement-feature skill at
.claude/skills/implement-feature/SKILL.md.

Save implementation notes to _workspace/impl_{slug}.md.
"""
)
```

After implementation:
- Review `_workspace/impl_{slug}.md`
- Spot-check the implementation against the UX spec and visual spec
- If significant deviations exist, send correction back to software-engineer

---

## Phase 4: Summary & Feedback

Report to the user:
1. **What was built** — list of files changed, new functions, new widget keys
2. **What was researched** — key findings from the research brief
3. **How it was designed** — UX and visual decisions made and why
4. **How to test it** — `streamlit run app.py`, which tab, what to look for

Then ask: "Is there anything you'd like to adjust — UX layout, chart aesthetics, or the statistical approach?"

---

## Error Handling

| Error | Action |
|-------|--------|
| Agent produces empty workspace file | Re-assign task with more specific instructions |
| Visual spec conflicts with Altair constraints | Send correction to visual-designer: "Altair 5 can't do X; use Y instead" |
| Implementation deviates significantly from spec | Re-run software-engineer with specific correction |
| Research finds no industry consensus | Proceed with most defensible approach; document the uncertainty |
| Widget key conflict detected | Send to software-engineer: "key X already used in {file}; use {alternative}" |

If any agent fails after one retry, proceed without their output and note the gap in the final summary.

---

## Data Flow Map

```
Orchestrator
  → _workspace/research_{slug}.md    (industry-researcher output)
  → _workspace/ux_{slug}.md          (ux-designer output)
  → _workspace/visual_{slug}.md      (visual-designer output)
  → [modified source files]          (software-engineer output)
  → _workspace/impl_{slug}.md        (software-engineer notes)
```

Final outputs → source files (`tools/`, `ui/`, `utils/`, `app.py`)
Intermediate files → `_workspace/` (preserved for audit and iteration)

---

## Test Scenarios

### Scenario 1: New feature (normal flow)
- Input: "Add a Bayesian stopping rule option to the sequential testing tab"
- Expected: Researcher briefs on Bayesian sequential methods → UX spec with new widget layout → Visual spec for any new charts → Implementation in `tools/sequential_testing.py` + `ui/tab_sequential.py`

### Scenario 2: Error flow — research produces no clear recommendation
- Input: "Should we use mSPRT or always-valid confidence intervals?"
- Expected: Researcher notes the debate, recommends mSPRT for product DS context → UX designer and visual designer proceed with mSPRT approach → Implementation follows

### Scenario 3: Partial re-run
- Input: "The chart from yesterday looks fine but the UX layout is confusing"
- Expected: Phase 0 detects existing `_workspace/` → run only ux-designer and software-engineer (skip researcher and visual-designer if chart is approved)

---

## Workspace File Naming Convention

| File | Producer | Consumer |
|------|----------|----------|
| `_workspace/research_{slug}.md` | industry-researcher | ux-designer, visual-designer, software-engineer |
| `_workspace/ux_{slug}.md` | ux-designer | visual-designer, software-engineer |
| `_workspace/visual_{slug}.md` | visual-designer | software-engineer |
| `_workspace/impl_{slug}.md` | software-engineer | orchestrator (review) |

Slug = short kebab-case label for the feature (e.g., `bayesian-stopping`, `funnel-ux-v2`, `power-heatmap`).
