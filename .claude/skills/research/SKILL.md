---
name: research
description: Research best practices, industry standards, and academic methods for A/B testing, experiment design, statistical analysis, power analysis, sequential testing, ratio metrics, causal inference, and product analytics. Use this skill when the team needs to validate an approach, explore what industry leaders do, or find the right statistical method for a new feature. Trigger when: researching how top companies handle X, finding best practices for Y, checking if our approach Z is standard, or exploring what method to use for a new tool.
---

# Research Skill

## Purpose

Produce a structured research brief that gives the team a clear, cited, opinionated answer to a statistical or design question — not a literature dump, but a recommendation backed by evidence.

## Process

### Step 1: Scope the question
Narrow the research question to one of these domains:
- **Power & sample size**: MDE calculation, power curves, variance reduction (CUPED, stratification)
- **Sequential testing**: alpha spending, always-valid p-values, mSPRT, Bayesian sequential methods
- **Ratio metrics**: delta method, bootstrap variance, Fieller's theorem
- **Causal inference**: DiD, synthetic control, IV, regression discontinuity
- **Funnel analysis**: conversion modeling, attribution, multi-touch
- **Visualization**: how to present statistical outputs for non-statistician decision-makers
- **UX for data science tools**: interaction patterns used in tools like Statsig, Eppo, Optimizely

### Step 2: Identify sources
Priority order:
1. Major tech company engineering blogs: Airbnb (Medium/Neurips), Netflix Tech Blog, Spotify R&D, Microsoft ExP, Booking.com, LinkedIn, Uber Engineering
2. Academic: peer-reviewed papers (ICML, KDD, SIGKDD, JASA, Annals of Statistics)
3. Industry conference talks: StrangeLoop, PyData, Causal Inference Summit
4. Quality textbooks: "Trustworthy Online Controlled Experiments" (Kohavi et al.), "Causal Inference: The Mixtape" (Cunningham)

### Step 3: Synthesize findings
- Extract the 3–5 most actionable findings
- Note where the field agrees vs. where there's debate
- Flag any finding that contradicts the current tool's implementation

### Step 4: Map to the codebase
For each finding, identify:
- Which tab/tool module is affected
- What the current implementation does (if anything)
- What the recommended change would be

### Step 5: Write the brief
Save to `_workspace/research_{topic_slug}.md`:

```markdown
# Research Brief: {Topic}
Date: {date}

## Summary (Actionable Findings)
- Finding 1 [Source]
- Finding 2 [Source]
- ...

## Deep Dive
### {Sub-topic 1}
{Detailed findings with citations}

### {Sub-topic 2}
...

## Gaps in Current Tool
| Gap | Affected Tab/Module | Severity (High/Med/Low) |
|-----|--------------------|-----------------------|
| ... | ... | ... |

## Recommendations
| Recommendation | Target File | Priority |
|----------------|------------|----------|
| ... | ... | ... |
```

## Quality Bar

A good research brief:
- Has at least 2 named sources per major finding
- Gives a clear recommendation (not just "it depends")
- Is readable by someone without a PhD — explain statistical concepts in plain language where needed
- Is actionable: each recommendation maps to a specific file or feature

A weak research brief:
- Lists findings without connecting them to the tool
- Says "both approaches have merit" without recommending one
- Relies only on one source type (e.g., all blog posts, no papers)
