# Experiment Tool

An interactive Streamlit suite of **11 tools** for product data scientists — covering the full lifecycle of experiment design, statistical validation, causal inference, and result analysis. Everything runs locally with no API keys required.

Built for data scientists and analysts who want to go beyond t-tests: design experiments correctly from the start, catch validity threats before launch, choose the right causal method, and communicate results clearly to non-technical stakeholders.

---

## Tools

### Experiment Design & Planning

| # | Tool | What it does |
|---|------|--------------|
| 1 | **Experiment Planner** | Three sub-tabs answer the three pre-launch questions: *How long to run? What can I detect? How many users?* Paired with a Feasibility Zone chart (VIABLE / PATIENCE / MARGINAL / NOT VIABLE) and a Power Sensitivity Matrix showing the full effect-size × sample-size space |
| 2 | **Sequential Testing** | Models alpha spending (O'Brien-Fleming, Pocock, Haybittle-Peto), quantifies type I error inflation from peeking, and shows stopping-time distributions |
| 3 | **Multiple Testing Correction** | Applies Bonferroni, Šidák, Holm-Bonferroni (FWER), and Benjamini-Hochberg (FDR) corrections when testing multiple metrics; shows a threshold shrinkage chart and a rejection heatmap for entered p-values |
| 4 | **A/A Simulator** | Simulates experiments with no true effect to validate randomization quality; reports empirical false positive rate, KS uniformity test, z-stat calibration, and a Sample Ratio Mismatch (SRM) chi-square check |

### Metric & Risk

| # | Tool | What it does |
|---|------|--------------|
| 5 | **Metric Recommender** | Rule-based lookup: given a feature type and funnel stage, returns a recommended primary metric, guardrail metrics, and rationale |
| 6 | **Risk Scanner** | Flags 6 experiment health risks — SRM, Simpson's paradox, cannibalization, novelty effects, SUTVA violations, and low-power guardrails |
| 7 | **Ratio Variance Estimator** | Decomposes variance for ratio metrics (e.g. revenue/session) using the delta method vs. bootstrap; surfaces the dominant variance component |

### Causal Inference

| # | Tool | What it does |
|---|------|--------------|
| 8 | **Causal Design Selector** | Walks through a decision tree (randomization possible? pre-treatment data? assignment mechanism?) and recommends a causal design with model spec and key assumptions |
| 9 | **DiD Simulator** | Simulates Difference-in-Differences under parallel trend violations; shows bias and power as a function of violation severity and pre-period length |
| 10 | **Funnel Simulator** | Models net MAU delta, revenue delta, and uplift × decay sensitivity across a multi-stage conversion funnel |

### Result Analysis

| # | Tool | What it does |
|---|------|--------------|
| 11 | **Result Analyzer** | Accepts raw query numbers (users, events, means, std devs) for up to 6 metrics across North Star / Supporting / Guardrail roles; computes significance, confidence intervals, and a forest plot; renders a color-coded SHIP IT / DON'T SHIP / INCONCLUSIVE verdict designed for non-technical stakeholders |

---

## Guided Experiment Design Journey

The sidebar walks you through a 7-step experiment design checklist that links the tabs in the recommended order:

1. 🗂️ **Choose your metric** → Metric Recommender
2. 🛡️ **Scan for risks** → Risk Scanner
3. ⚡ **Calculate sample size** → Experiment Planner
4. 🧭 **Confirm your design** → Causal Selector *(optional)*
5. 📈 **Plan stopping rules** → Sequential Testing *(optional)*
6. 🔬 **Handle multiple metrics** → Multiple Testing *(optional)*
7. 🔁 **Run an A/A test** → A/A Simulator

Steps with active computations show a live ✅ once completed in the current session.

---

## Getting Started

**Prerequisites:** Python 3.10+

```bash
# Install dependencies
pip3 install -r requirements.txt

# Launch
streamlit run app.py
```

The app opens at `http://localhost:8501`. No accounts, no API keys, no build step.

---

## Tech Stack

| Layer | Library |
|-------|---------|
| UI | [Streamlit](https://streamlit.io) |
| Math | NumPy, SciPy |
| Charts | [Altair](https://altair-viz.github.io) 5.x |
| Data | Pandas |
| Language | Python 3.10+ |

---

## Project Structure

```
app.py                  # Entry point: page config, sidebar journey, 11 tabs
tools/                  # Math engines — pure NumPy/SciPy, no Streamlit imports
  power_simulator.py    # Power curves, MDE, sample size, feasibility curve
  sequential_testing.py # Alpha spending, type I error inflation
  ratio_variance.py     # Delta method vs bootstrap variance
  metric_recommender.py # Rule-based metric lookup
  risk_scanner.py       # 6 experiment health risk flags
  causal_selector.py    # Causal design decision tree
  did_simulator.py      # DiD bias/power simulation
  funnel_simulator.py   # Funnel MAU/revenue model
  multiple_testing.py   # Bonferroni, Šidák, Holm, BH corrections
  aa_simulator.py       # A/A FPR simulation + SRM chi-square check
  result_analyzer.py    # Per-metric stats + overall verdict logic
ui/                     # One file per tab, each exports render()
  tab_power.py
  tab_sequential.py
  tab_ratio.py
  tab_recommender.py
  tab_risk.py
  tab_causal.py
  tab_did.py
  tab_funnel.py
  tab_mtc.py
  tab_aa.py
  tab_results.py
utils/
  charts.py             # All Altair chart constructors, return alt.Chart objects
```
