# Experiment Tool

An interactive Streamlit suite of 8 tools for product data scientists covering experiment design, causal inference, and funnel analysis — all running locally with no API keys required.

Built for data scientists and analysts who want to go beyond t-tests: size experiments correctly, detect threats to validity, choose the right causal design, and model funnel-level impact before shipping.

---

## Tools

### Experiment Design & Power Suite

| # | Tool | What it does |
|---|------|--------------|
| 1 | **Power & MDE Calculator** | Plots power curves and sensitivity heatmaps; computes minimum detectable effect at a fixed sample size using analytical formulas for binary and continuous metrics |
| 2 | **Sequential Testing Analyzer** | Models alpha spending (O'Brien-Fleming, Pocock, Haybittle-Peto), quantifies type I error inflation from peeking, and shows stopping-time distributions |
| 3 | **Ratio Variance Estimator** | Decomposes variance for ratio metrics (e.g. revenue/session) using the delta method vs. bootstrap; surfaces the dominant variance component |
| 4 | **Metric Recommender** | Rule-based lookup: given a feature type and funnel stage, returns a recommended primary metric, guardrail metrics, and a rationale |
| 5 | **Risk Scanner** | Flags 6 experiment health risks — SRM, Simpson's paradox, cannibalization, novelty effects, SUTVA violations, and low-power guardrails |

### Causal Inference Toolkit

| # | Tool | What it does |
|---|------|--------------|
| 6 | **Causal Design Selector** | Walks through a decision tree (randomization possible? pre-treatment data? assignment mechanism?) and recommends a causal design with model spec and key assumptions |
| 7 | **DiD Simulator** | Simulates Difference-in-Differences under parallel trend violations; shows bias and power as a function of violation severity and pre-period length |

### Product Funnel

| # | Tool | What it does |
|---|------|--------------|
| 8 | **Funnel Simulator** | Models net MAU delta, revenue delta, and uplift × decay sensitivity across a multi-stage conversion funnel |

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
app.py              # Entry point: page config, sidebar, 8 tabs
tools/              # Math engines — pure NumPy/SciPy, no Streamlit imports
  power_simulator.py
  sequential_testing.py
  ratio_variance.py
  metric_recommender.py
  risk_scanner.py
  causal_selector.py
  did_simulator.py
  funnel_simulator.py
ui/                 # One file per tab, each exports render()
  tab_power.py
  tab_sequential.py
  tab_ratio.py
  tab_recommender.py
  tab_risk.py
  tab_causal.py
  tab_did.py
  tab_funnel.py
utils/
  charts.py         # All Altair chart constructors, return alt.Chart objects
```
