"""
UI Tab 11: Experiment Result Analyzer
Analyzes A/B test results across multiple metrics (north star + supporting + guardrail).
Designed for both technical and non-technical stakeholders.
"""

import streamlit as st
import pandas as pd

from tools.result_analyzer import analyze_binary, analyze_continuous, overall_verdict
from utils.charts import results_forest_plot, results_traffic_chart


_ROLE_OPTIONS = ["North Star ⭐", "Supporting 📊", "Guardrail 🛡️"]
_TYPE_OPTIONS = ["binary", "continuous"]
_DIR_OPTIONS  = ["higher", "lower"]


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_rate(v):   return f"{v * 100:.3f}%"
def _fmt_mean(v):   return f"{v:,.3f}"
def _fmt_pct(v):    return f"{v * 100:+.2f}%"
def _fmt_pp(v):     return f"{v * 100:+.3f} pp"
def _fmt_p(v):      return f"{v:.4f}" if v >= 0.0001 else "< 0.0001"


def _val_label(result):
    """Format the control / treatment values for display."""
    if result["value_type"] == "rate":
        return _fmt_rate(result["ctrl_val"]), _fmt_rate(result["treat_val"])
    return _fmt_mean(result["ctrl_val"]), _fmt_mean(result["treat_val"])


def _change_labels(result):
    """Return (relative_label, absolute_label) strings."""
    rel = _fmt_pct(result["relative_change"])
    if result["value_type"] == "rate":
        abs_lbl = _fmt_pp(result["absolute_change"])
    else:
        abs_lbl = f"{result['absolute_change']:+,.3f}"
    return rel, abs_lbl


def _ci_labels(result):
    """Return (ci_lo_str, ci_hi_str) in the natural unit for display."""
    if result["value_type"] == "rate":
        return _fmt_pp(result["ci_lo"]), _fmt_pp(result["ci_hi"])
    return f"{result['ci_lo']:+,.3f}", f"{result['ci_hi']:+,.3f}"


# ── Verdict banner ────────────────────────────────────────────────────────────

def _render_verdict_banner(verdict: dict):
    st.markdown(
        f"""
        <div style="
            background:{verdict['bg']};
            border:2px solid {verdict['border']};
            border-radius:12px;
            padding:24px 32px;
            margin:8px 0 20px 0;
        ">
            <div style="display:flex; align-items:center; gap:12px;">
                <span style="font-size:2.4rem;">{verdict['emoji']}</span>
                <div>
                    <p style="margin:0; font-size:1.8rem; font-weight:800;
                               color:{verdict['fg']}; letter-spacing:-0.5px;">
                        {verdict['verdict']}
                    </p>
                    <p style="margin:4px 0 0 0; font-size:1rem; color:{verdict['fg']}; opacity:0.85;">
                        {verdict['summary']}
                    </p>
                </div>
            </div>
            <p style="margin:12px 0 0 0; font-size:0.88rem; color:{verdict['fg']}; opacity:0.75;
                       border-top:1px solid {verdict['border']}; padding-top:12px;">
                {verdict['detail']}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── CI bar (HTML, single metric) ───────────────────────────────────────────────

def _render_ci_bar(result: dict, alpha: float):
    """Proportional horizontal CI bar with zero line, styled in HTML."""
    ci_lo = result["ci_lo"]
    ci_hi = result["ci_hi"]
    point = result["absolute_change"]
    is_rate = result["value_type"] == "rate"

    max_abs = max(abs(ci_lo), abs(ci_hi), 1e-9)
    scale   = 38.0 / max_abs          # maps max_abs → 38% from centre

    lo_pct  = 50 + ci_lo  * scale
    hi_pct  = 50 + ci_hi  * scale
    pt_pct  = 50 + point  * scale
    lo_pct  = max(4.0, min(96.0, lo_pct))
    hi_pct  = max(4.0, min(96.0, hi_pct))
    pt_pct  = max(4.0, min(96.0, pt_pct))

    if ci_lo > 0:
        bar_color = "#10b981"
    elif ci_hi < 0:
        bar_color = "#ef4444"
    else:
        bar_color = "#f59e0b"   # crosses zero

    ci_lo_lbl, ci_hi_lbl = _ci_labels(result)
    rel_lbl, abs_lbl      = _change_labels(result)
    ci_pct = int((1 - alpha) * 100)

    st.markdown(
        f"""
        <div style="margin:8px 0 20px 0;">
            <div style="display:flex; justify-content:space-between;
                        font-size:0.78rem; color:#6b7280; margin-bottom:4px;">
                <span>{ci_pct}% Confidence Interval</span>
                <span style="font-weight:600; color:{bar_color};">{abs_lbl} ({rel_lbl})</span>
            </div>
            <div style="position:relative; height:28px; background:#f1f5f9;
                        border-radius:6px; overflow:hidden;">
                <!-- CI bar -->
                <div style="position:absolute; left:{lo_pct:.1f}%;
                            width:{hi_pct - lo_pct:.1f}%; height:100%;
                            background:{bar_color}; opacity:0.35; border-radius:3px;"></div>
                <!-- Zero rule -->
                <div style="position:absolute; left:50%; width:2px; height:100%;
                            background:#64748b; opacity:0.5;"></div>
                <!-- Point estimate tick -->
                <div style="position:absolute; left:{pt_pct:.1f}%;
                            transform:translateX(-50%); width:4px; height:100%;
                            background:{bar_color}; border-radius:2px;"></div>
            </div>
            <div style="display:flex; justify-content:space-between;
                        font-size:0.75rem; color:#6b7280; margin-top:4px;">
                <span>{ci_lo_lbl}</span>
                <span style="color:#374151; font-weight:500;">
                    {"← 0 →" if ci_lo <= 0 <= ci_hi else ("→ all positive" if ci_lo > 0 else "← all negative")}
                </span>
                <span>{ci_hi_lbl}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Metric summary card ────────────────────────────────────────────────────────

_VERDICT_STYLES = {
    "win":     {"bg": "#f0fdf4", "border": "#10b981", "badge_bg": "#dcfce7", "badge_fg": "#065f46", "label": "Improved ✓"},
    "loss":    {"bg": "#fef2f2", "border": "#ef4444", "badge_bg": "#fee2e2", "badge_fg": "#b91c1c", "label": "Declined ✗"},
    "neutral": {"bg": "#f8fafc", "border": "#cbd5e1", "badge_bg": "#f1f5f9", "badge_fg": "#475569", "label": "No change —"},
}

def _render_metric_card(result: dict):
    s = _VERDICT_STYLES[result["verdict"]]
    rel_lbl, abs_lbl = _change_labels(result)
    ctrl_v, treat_v  = _val_label(result)
    role_icon = result.get("role", "").split()[0] if result.get("role") else ""
    sign_txt  = "Yes ✓" if result["significant"] else "No"

    st.markdown(
        f"""
        <div style="
            background:{s['bg']}; border:1.5px solid {s['border']};
            border-radius:10px; padding:16px; height:100%;
        ">
            <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                <span style="font-weight:700; font-size:0.95rem; color:#1e293b;">
                    {role_icon} {result['name']}
                </span>
                <span style="
                    background:{s['badge_bg']}; color:{s['badge_fg']};
                    font-size:0.72rem; font-weight:700; padding:2px 8px;
                    border-radius:99px; white-space:nowrap;
                ">{s['label']}</span>
            </div>
            <div style="font-size:2rem; font-weight:800; color:{s['border']}; margin:4px 0;">
                {rel_lbl}
            </div>
            <div style="font-size:0.82rem; color:#64748b;">{abs_lbl} absolute</div>
            <hr style="margin:10px 0; border:none; border-top:1px solid {s['border']}; opacity:0.3;">
            <div style="font-size:0.78rem; color:#475569; line-height:1.6;">
                <div><b>Control:</b> {ctrl_v}</div>
                <div><b>Treatment:</b> {treat_v}</div>
                <div><b>Significant:</b> {sign_txt} &nbsp;|&nbsp; <b>p =</b> {_fmt_p(result['p_value'])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Per-metric detail expander ────────────────────────────────────────────────

def _render_metric_detail(i: int, result: dict, alpha: float, ctrl_name: str, treat_name: str):
    s = _VERDICT_STYLES[result["verdict"]]
    rel_lbl, abs_lbl = _change_labels(result)
    ctrl_v, treat_v  = _val_label(result)

    with st.expander(
        f"{result['name']}  ·  {result.get('role','')}  ·  {rel_lbl}  ·  {s['label']}",
        expanded=(i == 0),
    ):
        c_l, c_r = st.columns([1, 1])

        with c_l:
            st.markdown("#### Results at a glance")
            m1, m2 = st.columns(2)
            m1.metric("Relative Change",  rel_lbl,
                       help="Percentage change from control to treatment.")
            m2.metric("Absolute Change",  abs_lbl,
                       help="Raw difference between control and treatment rates/means.")
            m3, m4 = st.columns(2)
            m3.metric(f"{ctrl_name} ({result['value_type']})",   ctrl_v)
            m4.metric(f"{treat_name} ({result['value_type']})", treat_v,
                       delta=rel_lbl, delta_color="normal" if result["direction_positive"] else "inverse")

            # Plain-English interpretation
            sig_word = "a statistically significant" if result["significant"] else "no statistically significant"
            dir_word = ("improvement" if result["direction_positive"] else "decline") if result["significant"] else "change"
            st.info(
                f"The experiment shows **{sig_word} {dir_word}** in **{result['name']}**. "
                + (f"The treatment {'outperformed' if result['direction_positive'] else 'underperformed'} "
                   f"the control by {rel_lbl} ({abs_lbl})."
                   if result["significant"]
                   else f"The observed difference ({rel_lbl}) could be due to random chance (p = {_fmt_p(result['p_value'])})."),
                icon=("✅" if result["verdict"] == "win" else "❌" if result["verdict"] == "loss" else "ℹ️"),
            )

        with c_r:
            st.markdown("#### Confidence interval")
            st.caption(
                "The bar shows the range of plausible true effects. "
                "Green = entirely positive. Red = entirely negative. "
                "Amber = crosses zero (uncertain direction)."
            )
            _render_ci_bar(result, alpha)

            with st.expander("🔬 Technical details", expanded=False):
                test_name = "Two-proportion z-test" if result["value_type"] == "rate" else "Welch's t-test"
                st.markdown(f"""
                | Parameter | Value |
                |-----------|-------|
                | Statistical test | {test_name} |
                | Test statistic | {result['test_stat']:+.4f} |
                | p-value | {_fmt_p(result['p_value'])} |
                | Significant (α = {alpha}) | {"Yes" if result["significant"] else "No"} |
                | CI lower | {_ci_labels(result)[0]} |
                | CI upper | {_ci_labels(result)[1]} |
                """)


# ── Metric input form ─────────────────────────────────────────────────────────

def _render_metric_input(i: int, ctrl_name: str, treat_name: str) -> dict | None:
    """Render input widgets for metric i. Returns a config dict or None if incomplete."""
    role_default = 0 if i == 0 else (1 if i < 3 else 2)
    is_first = i == 0

    with st.expander(
        f"{'⭐ ' if i == 0 else ''} Metric {i + 1}"
        + (f"  —  {st.session_state.get(f'res_name_{i}', '')}" if st.session_state.get(f"res_name_{i}") else ""),
        expanded=is_first,
    ):
        row1 = st.columns([3, 2, 2, 2])
        name = row1[0].text_input(
            "Metric name",
            value=(["North Star Metric", "Supporting Metric", "Guardrail Metric"][i] if i < 3 else f"Metric {i+1}")
                  if not st.session_state.get(f"res_name_{i}") else st.session_state.get(f"res_name_{i}"),
            key=f"res_name_{i}",
            placeholder="e.g. Checkout Conversion",
        )
        role = row1[1].selectbox("Role", _ROLE_OPTIONS, index=role_default, key=f"res_role_{i}")
        mtype = row1[2].selectbox("Metric type", _TYPE_OPTIONS,
                                   format_func=lambda x: "Binary (rate)" if x == "binary" else "Continuous (mean)",
                                   key=f"res_type_{i}")
        direction = row1[3].selectbox(
            "Higher is…",
            ["better", "worse"],
            key=f"res_dir_{i}",
            help="Determines whether an increase in this metric is a positive or negative outcome.",
        )
        dir_val = "higher" if direction == "better" else "lower"

        # ── Data inputs ───────────────────────────────────────────────────
        if mtype == "binary":
            st.caption(f"Enter the output of: `SELECT arm, COUNT(*) AS users, SUM(converted) AS conversions FROM experiment GROUP BY arm`")
            row2 = st.columns(4)
            ctrl_n       = row2[0].number_input(f"{ctrl_name} — Users",        min_value=1, value=10000, step=100,  key=f"res_cn_{i}")
            ctrl_events  = row2[1].number_input(f"{ctrl_name} — Conversions",  min_value=0, value=523,   step=10,   key=f"res_ce_{i}")
            treat_n      = row2[2].number_input(f"{treat_name} — Users",       min_value=1, value=10200, step=100,  key=f"res_tn_{i}")
            treat_events = row2[3].number_input(f"{treat_name} — Conversions", min_value=0, value=589,   step=10,   key=f"res_te_{i}")

            if ctrl_events > ctrl_n or treat_events > treat_n:
                st.error("Conversions cannot exceed user count.")
                return None

            ctrl_rate  = ctrl_events / ctrl_n
            treat_rate = treat_events / treat_n
            st.caption(
                f"**{ctrl_name}:** {ctrl_rate*100:.3f}% conversion  ·  "
                f"**{treat_name}:** {treat_rate*100:.3f}% conversion  ·  "
                f"Lift: {(treat_rate-ctrl_rate)/ctrl_rate*100:+.2f}%"
            )
            return {
                "name": name, "role": role, "type": mtype, "direction": dir_val,
                "ctrl_n": int(ctrl_n), "treat_n": int(treat_n),
                "ctrl_events": int(ctrl_events), "treat_events": int(treat_events),
            }

        else:  # continuous
            st.caption(f"Enter the output of: `SELECT arm, COUNT(*) AS users, AVG(metric) AS mean, STDDEV(metric) AS std FROM experiment GROUP BY arm`")
            row2 = st.columns(3)
            ctrl_n    = row2[0].number_input(f"{ctrl_name} — Users",    min_value=2, value=10000, step=100,   key=f"res_cn_{i}")
            ctrl_mean = row2[0].number_input(f"{ctrl_name} — Mean",     value=50.0,  format="%.4f",           key=f"res_cm_{i}")
            ctrl_std  = row2[0].number_input(f"{ctrl_name} — Std Dev",  min_value=0.0001, value=20.0, format="%.4f", key=f"res_cs_{i}")
            treat_n    = row2[1].number_input(f"{treat_name} — Users",  min_value=2, value=10200, step=100,   key=f"res_tn_{i}")
            treat_mean = row2[1].number_input(f"{treat_name} — Mean",   value=51.5,  format="%.4f",           key=f"res_tm_{i}")
            treat_std  = row2[1].number_input(f"{treat_name} — Std Dev",min_value=0.0001, value=20.5, format="%.4f", key=f"res_ts_{i}")
            abs_diff = treat_mean - ctrl_mean
            rel_diff = abs_diff / ctrl_mean * 100 if ctrl_mean != 0 else 0
            row2[2].markdown("**Preview**")
            row2[2].caption(f"Δ = {abs_diff:+,.4f}  ({rel_diff:+.2f}%)")
            return {
                "name": name, "role": role, "type": mtype, "direction": dir_val,
                "ctrl_n": int(ctrl_n), "ctrl_mean": float(ctrl_mean), "ctrl_std": float(ctrl_std),
                "treat_n": int(treat_n), "treat_mean": float(treat_mean), "treat_std": float(treat_std),
            }


# ── Main render ────────────────────────────────────────────────────────────────

def render():
    st.header("Experiment Result Analyzer")
    st.caption(
        "Enter the raw numbers from your database query to get a full statistical analysis "
        "across all your experiment metrics. Designed for both technical and non-technical audiences."
    )

    with st.expander("📖 How to use this tool", expanded=False):
        st.markdown("""
        ### Input your query results directly

        For each metric, run a query like:

        **Binary metric (conversion rate):**
        ```sql
        SELECT
            arm,
            COUNT(DISTINCT user_id)          AS users,
            SUM(CASE WHEN converted THEN 1 END) AS conversions
        FROM experiment_assignments
        WHERE experiment_id = 'my_experiment'
        GROUP BY arm;
        ```

        **Continuous metric (revenue, session length, etc.):**
        ```sql
        SELECT
            arm,
            COUNT(DISTINCT user_id) AS users,
            AVG(revenue)             AS mean,
            STDDEV(revenue)          AS std_dev
        FROM experiment_assignments
        WHERE experiment_id = 'my_experiment'
        GROUP BY arm;
        ```

        Then paste the numbers into the fields below. You can analyze up to 6 metrics simultaneously.

        ### Metric roles
        - **North Star ⭐** — your primary success metric. The shipping decision is based on this.
        - **Supporting 📊** — secondary metrics that provide context.
        - **Guardrail 🛡️** — metrics you must not harm (revenue, errors, churn). A significant negative change here blocks shipping.
        """)

    st.divider()

    # ── Experiment setup ──────────────────────────────────────────────────
    st.subheader("Experiment Setup")
    cfg1, cfg2, cfg3, cfg4 = st.columns([3, 2, 2, 1])
    exp_name  = cfg1.text_input("Experiment name", value="My A/B Experiment", key="res_exp_name")
    ctrl_name = cfg2.text_input("Control arm name",   value="Control",   key="res_ctrl_name")
    treat_name= cfg3.text_input("Treatment arm name", value="Treatment", key="res_treat_name")
    alpha     = cfg4.selectbox("Alpha (α)", [0.05, 0.01, 0.10], index=0, key="res_alpha")

    st.divider()

    # ── Metric count ──────────────────────────────────────────────────────
    st.subheader("Metric Data")
    st.caption("Enter the raw numbers from your database for each metric. Add up to 6 metrics.")
    n_metrics = st.slider(
        "Number of metrics",
        min_value=1, max_value=6, value=3,
        key="res_n_metrics",
        help="Set how many metrics you want to analyze simultaneously.",
    )

    configs = []
    for i in range(int(n_metrics)):
        cfg = _render_metric_input(i, ctrl_name, treat_name)
        if cfg is not None:
            configs.append(cfg)

    # ── Run ───────────────────────────────────────────────────────────────
    st.divider()
    run = st.button("▶  Analyze Results", type="primary", key="run_res",
                    width="stretch")

    if run or "res_results" in st.session_state:
        if run:
            if not configs:
                st.error("Fix the input errors above before analyzing.")
                return

            results = []
            for cfg in configs:
                if cfg["type"] == "binary":
                    r = analyze_binary(
                        cfg["ctrl_n"], cfg["ctrl_events"],
                        cfg["treat_n"], cfg["treat_events"],
                        alpha=alpha, direction=cfg["direction"],
                    )
                else:
                    r = analyze_continuous(
                        cfg["ctrl_n"], cfg["ctrl_mean"], cfg["ctrl_std"],
                        cfg["treat_n"], cfg["treat_mean"], cfg["treat_std"],
                        alpha=alpha, direction=cfg["direction"],
                    )
                r.update({"name": cfg["name"], "role": cfg["role"],
                           "ctrl_n": cfg["ctrl_n"], "treat_n": cfg["treat_n"]})
                results.append(r)

            st.session_state["res_results"] = {
                "results": results,
                "ctrl_name": ctrl_name,
                "treat_name": treat_name,
                "alpha": alpha,
                "exp_name": exp_name,
            }

        saved    = st.session_state["res_results"]
        results  = saved["results"]
        ctrl_name_s  = saved["ctrl_name"]
        treat_name_s = saved["treat_name"]
        alpha_s      = saved["alpha"]
        exp_name_s   = saved["exp_name"]

        st.divider()

        # ── Verdict ───────────────────────────────────────────────────────
        st.subheader(f"Results: {exp_name_s}")
        verdict = overall_verdict(results)
        _render_verdict_banner(verdict)

        # ── Metric summary cards ──────────────────────────────────────────
        st.markdown("#### Metric Summary")
        card_cols = st.columns(len(results))
        for col, result in zip(card_cols, results):
            with col:
                _render_metric_card(result)

        # ── Forest plot ───────────────────────────────────────────────────
        st.divider()
        st.markdown("#### Effect Estimates")
        st.caption(
            "Each row shows the range of plausible effects (confidence interval) for one metric. "
            "The dot is the observed effect; the bar is the CI. "
            "Green = statistically positive, red = negative, grey = inconclusive. "
            "Bars that don't cross the zero line are statistically significant."
        )
        forest_data = [
            {
                "name": r["name"], "role": r["role"],
                "relative_change": r["relative_change"],
                "rel_ci_lo": r["rel_ci_lo"], "rel_ci_hi": r["rel_ci_hi"],
                "verdict": r["verdict"], "significant": r["significant"],
            }
            for r in results
        ]
        st.altair_chart(results_forest_plot(forest_data), width="stretch")

        # ── Traffic chart ─────────────────────────────────────────────────
        with st.expander("📊 Traffic distribution per arm", expanded=False):
            st.caption("Confirms the number of users entering each arm is as expected. Large differences here may indicate an SRM — use the 🔁 A/A Simulator tab to investigate.")
            traffic_data = [{"name": r["name"], "ctrl_n": r["ctrl_n"], "treat_n": r["treat_n"]} for r in results]
            st.altair_chart(results_traffic_chart(traffic_data, ctrl_name_s, treat_name_s), width="stretch")

        # ── Per-metric details ────────────────────────────────────────────
        st.divider()
        st.markdown("#### Metric Details")
        st.caption("Click each row to expand the full statistical breakdown, confidence interval, and plain-English interpretation.")
        for i, result in enumerate(results):
            _render_metric_detail(i, result, alpha_s, ctrl_name_s, treat_name_s)

    else:
        st.info(
            "Fill in your experiment data above and click **▶ Analyze Results** to see the full breakdown.",
            icon="▶️",
        )
