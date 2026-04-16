"""
UI Tab 1: Experiment Planner
Three practitioner-focused sub-tabs with decision-oriented visuals.
"""

import streamlit as st
import pandas as pd
from tools.power_simulator import (
    mde_for_power,
    sample_size_for_effect,
    feasibility_curve,
    sensitivity_heatmap,
    subgroup_mde_table,
)
from utils.charts import feasibility_zone_chart, power_matrix_chart, subgroup_mde_chart


# ── Helpers ───────────────────────────────────────────────

def _params_key(p: dict) -> str:
    """Deterministic fingerprint of shared params for stale-result detection."""
    return "|".join(str(p[k]) for k in sorted(p))


def _mde_range(mde_rel: float) -> list:
    """5 effect sizes centered on mde_rel (as fractions)."""
    center = max(mde_rel, 0.01)
    candidates = [center * f for f in [0.4, 0.7, 1.0, 1.4, 2.0]]
    return [max(0.01, round(x, 4)) for x in candidates]


def _n_range(n_per_arm: int) -> list:
    """5 sample sizes centered on n_per_arm."""
    factors = [0.25, 0.5, 1.0, 2.0, 4.0]
    return [max(50, int(n_per_arm * f)) for f in factors]


# ── Shared Params ─────────────────────────────────────────

def _shared_params() -> dict:
    """Render shared parameter panel and return collected values."""
    col1, col2 = st.columns(2)

    with col1:
        metric_type = st.selectbox(
            "Metric Type",
            ["binary", "continuous", "ratio"],
            help=(
                "**Binary**: 0/1 per user (conversion, click). Uses two-proportion z-test.\n\n"
                "**Continuous**: numeric per user (revenue, session length). Uses two-sample t-test.\n\n"
                "**Ratio**: numerator/denominator (CTR, CVR). Uses Monte Carlo."
            ),
            key="pwr_metric_type",
        )
        if metric_type == "binary":
            baseline_mean = st.number_input(
                "Baseline Conversion Rate",
                value=0.05, min_value=0.001, max_value=0.999, format="%.4f",
                help="Current conversion rate. E.g. 0.05 = 5% of users convert.",
                key="pwr_baseline_mean_bin",
            )
            baseline_std = float((baseline_mean * (1 - baseline_mean)) ** 0.5)
            st.caption(f"Auto std = sqrt(p·(1-p)) = **{baseline_std:.4f}**")
        else:
            baseline_mean = st.number_input(
                "Baseline Mean",
                value=10.0, min_value=0.001, format="%.3f",
                help="Average metric value per user before treatment.",
                key="pwr_baseline_mean",
            )
            baseline_std = st.number_input(
                "Baseline Std Dev",
                value=5.0, min_value=0.0001, format="%.3f",
                help="Standard deviation across users. Higher → more noise → need more users.",
                key="pwr_baseline_std",
            )

    with col2:
        alpha = st.slider(
            "Significance Level (α)", 0.01, 0.10, 0.05, step=0.01,
            help="False positive rate. Industry standard: 0.05.",
            key="pwr_alpha",
        )
        target_power = st.slider(
            "Target Power", 0.60, 0.99, 0.80, step=0.05,
            help="Probability of detecting a real effect. Standard: 0.80.",
            key="pwr_target_power",
        )
        daily_traffic = st.number_input(
            "Daily Traffic per Arm",
            min_value=0, value=1000, step=500,
            help=(
                "Unique users entering each arm per day (50/50 split). "
                "Used to convert sample sizes to calendar days."
            ),
            key="pwr_daily_traffic",
        )

    with st.expander("Advanced: CUPED & Clustering", expanded=False):
        a1, a2 = st.columns(2)
        with a1:
            n_sim = st.select_slider(
                "MC Simulation Runs (ratio only)",
                options=[500, 1000, 2000, 5000], value=1000,
                key="pwr_n_sim",
            )
            r_squared = st.slider(
                "CUPED R²", 0.0, 0.9, 0.0, step=0.05,
                help="Pre-experiment covariate R². Reduces variance by (1−R²).",
                key="pwr_r_squared",
            )
            st.caption(f"Variance reduced to **{(1 - r_squared)*100:.0f}%** of baseline")
        with a2:
            icc = st.slider(
                "Clustering ICC", 0.0, 0.3, 0.0, step=0.01,
                help="Intra-cluster correlation. 0 = user-level randomization.",
                key="pwr_icc",
            )
            cluster_size = st.number_input(
                "Avg Cluster Size", min_value=1, value=50, step=10,
                key="pwr_cluster_size",
            )

    return dict(
        metric_type=metric_type,
        baseline_mean=baseline_mean,
        baseline_std=baseline_std,
        alpha=alpha,
        target_power=target_power,
        daily_traffic=int(daily_traffic),
        n_sim=n_sim,
        r_squared=r_squared,
        icc=icc,
        cluster_size=float(cluster_size),
    )


# ── Sub-tab 1: How long? ──────────────────────────────────

def _render_duration_sub(p: dict) -> None:
    left, right = st.columns([1, 1])

    with left:
        st.markdown("**How long must the experiment run to detect your target lift?**")
        mde_pct = st.slider(
            "Target MDE (%)", 1, 50, 10,
            help="Minimum relative lift you need to be able to detect.",
            key="pwr_dur_mde",
        )
        run = st.button("Calculate Runtime", type="primary", key="run_dur")

    if run:
        effect_size = mde_pct / 100.0
        with st.spinner("Calculating..."):
            n_per_arm = sample_size_for_effect(
                metric_type=p["metric_type"],
                baseline_mean=p["baseline_mean"],
                baseline_std=p["baseline_std"],
                effect_size=effect_size,
                alpha=p["alpha"],
                target_power=p["target_power"],
                n_sim=p["n_sim"],
                r_squared=p["r_squared"],
                icc=p["icc"],
                cluster_size=p["cluster_size"],
            )
        days = n_per_arm / p["daily_traffic"] if p["daily_traffic"] > 0 else None
        st.session_state["pwr_dur_results"] = dict(
            n_per_arm=n_per_arm, days=days, mde_pct=mde_pct,
            baseline_mean=p["baseline_mean"], metric_type=p["metric_type"],
            _params_key=_params_key(p),
        )

    if "pwr_dur_results" in st.session_state:
        res = st.session_state["pwr_dur_results"]
        n_per_arm = res["n_per_arm"]
        days = res["days"]
        mde_pct_shown = res["mde_pct"]
        bm = res["baseline_mean"]
        mt = res["metric_type"]

        if res.get("_params_key") != _params_key(p):
            st.warning(
                "⚠️ Shared settings changed since last run — results below may not match "
                "the current parameters. Click **Calculate Runtime** to update."
            )

        with right:
            if days is not None:
                st.metric("Required Runtime", f"{days:.0f} days / {days/7:.1f} weeks")
            else:
                st.metric("Required Runtime", "Set daily traffic")

            c1, c2 = st.columns(2)
            c1.metric("N per Arm", f"{n_per_arm:,}")
            c2.metric("Total N", f"{n_per_arm * 2:,}")

            if mt == "binary":
                abs_mde = (mde_pct_shown / 100) * bm
                st.caption(f"= {abs_mde * 100:.2f} pp absolute change on {bm*100:.2f}% baseline")
            else:
                abs_mde = (mde_pct_shown / 100) * bm
                st.caption(f"= {abs_mde:.3g} absolute change on {bm:.3g} baseline")

            if days is not None:
                st.info(
                    f"To detect a **{mde_pct_shown}% relative lift** with "
                    f"{p['target_power']:.0%} power at α={p['alpha']}, you need "
                    f"**{n_per_arm:,} users per arm** — approximately "
                    f"**{days:.0f} days** ({days/7:.1f} weeks) at "
                    f"{p['daily_traffic']:,} users/day/arm."
                )

            if n_per_arm >= 10_000_000:
                abs_mde_shown = (mde_pct_shown / 100) * bm
                st.error(
                    f"**Requires {n_per_arm:,} users per arm** — this is Google/Meta scale. "
                    f"Your absolute MDE is only **{abs_mde_shown * 100:.4f} pp** on a {bm*100:.2f}% baseline. "
                    f"At this precision, consider: (1) widen MDE to a business-meaningful absolute threshold, "
                    f"(2) switch to a higher-signal proxy metric closer to the intervention, "
                    f"or (3) apply CUPED to reduce variance."
                )
            elif days is not None and days < 7:
                st.warning("Runtime < 7 days. Always run at least one full week to avoid day-of-week bias.")
            elif days is not None and days > 56:
                st.warning("Runtime > 8 weeks. Consider novelty effects and seasonality risk over this window.")

            st.markdown("""
**Important considerations**
- Run for at least 7 days to cover a full weekly cycle
- Don't stop early even if results look significant
- Add ramp-up buffer for gradual rollouts
- Novelty effects can inflate early results (first 1–3 days)
""")

        # Feasibility zone chart (full width, below 2-col section)
        if p["daily_traffic"] > 0:
            st.divider()
            st.subheader("Feasibility & Duration")
            st.caption("How long will the experiment take at different sensitivity levels?")
            if days is not None:
                st.markdown(
                    f"**A {mde_pct_shown}% relative lift is detectable in "
                    f"{days/7:.1f} weeks with current traffic.**"
                )
            with st.spinner("Computing feasibility curve..."):
                fc_rows = feasibility_curve(
                    metric_type=p["metric_type"],
                    baseline_mean=p["baseline_mean"],
                    baseline_std=p["baseline_std"],
                    alpha=p["alpha"],
                    target_power=p["target_power"],
                    daily_traffic=p["daily_traffic"],
                    n_sim=p["n_sim"],
                    r_squared=p["r_squared"],
                    icc=p["icc"],
                    cluster_size=p["cluster_size"],
                )
            if fc_rows:
                st.altair_chart(
                    feasibility_zone_chart(fc_rows, target_mde_pct=mde_pct_shown),
                    width="stretch",
                )
                with st.expander("📊 How to read this chart", expanded=False):
                    st.markdown("""
**Statistically:** The curve shows required experiment duration (weeks) to achieve your target
power at each possible MDE. It's a hyperbola — small effects require exponentially more data.
The zones reflect what's realistic to commit to:

- **VIABLE** (≤ 2 weeks): Fast, low risk of external confounds
- **PATIENCE** (2–4 weeks): Standard; common for most product experiments
- **MARGINAL** (4–8 weeks): Long; novelty effects and seasonality become concerns
- **NOT VIABLE** (> 8 weeks): Too long for a single experiment — consider proxy metrics, phased approach, or CUPED

**Business terms:** Each point on the curve answers: *"If we only care about detecting a lift of X%,
how long must we commit to running this experiment?"* The orange dot is your current target.
If it's in the orange or red zone, you have three levers: accept a wider MDE, increase daily traffic
allocation, or apply CUPED to reduce variance (Advanced settings above).
""")


# ── Sub-tab 2: What can I detect? ────────────────────────

def _render_sensitivity_sub(p: dict) -> None:
    left, right = st.columns([1, 1])

    with left:
        st.markdown("**What effect size can your experiment reliably detect?**")
        mode = st.radio(
            "Input mode",
            ["Sample size per arm", "Days + daily traffic"],
            key="pwr_sens_mode",
            horizontal=True,
        )
        if mode == "Sample size per arm":
            n_per_arm = st.number_input(
                "Sample Size per Arm", min_value=50, value=5000, step=500,
                key="pwr_sens_n",
            )
        else:
            days_input = st.number_input(
                "Experiment Duration (days)", min_value=1, value=14, step=1,
                key="pwr_sens_days",
            )
            n_per_arm = max(int(days_input * p["daily_traffic"]), 50)
            st.caption(f"= {n_per_arm:,} users per arm at {p['daily_traffic']:,}/day")

        run = st.button("Calculate MDE", type="primary", key="run_sens")

    if run:
        with st.spinner("Calculating MDE..."):
            mde_rel = mde_for_power(
                metric_type=p["metric_type"],
                baseline_mean=p["baseline_mean"],
                baseline_std=p["baseline_std"],
                target_power=p["target_power"],
                alpha=p["alpha"],
                n_per_arm=n_per_arm,
                r_squared=p["r_squared"],
                icc=p["icc"],
                cluster_size=p["cluster_size"],
            )
        mde_abs = mde_rel * p["baseline_mean"]
        st.session_state["pwr_sens_results"] = dict(
            n_per_arm=n_per_arm, mde_rel=mde_rel, mde_abs=mde_abs,
            baseline_mean=p["baseline_mean"], metric_type=p["metric_type"],
            _params_key=_params_key(p),
        )

    if "pwr_sens_results" in st.session_state:
        res = st.session_state["pwr_sens_results"]
        mde_rel = res["mde_rel"]
        mde_abs = res["mde_abs"]
        n = res["n_per_arm"]
        bm = res["baseline_mean"]
        mt = res["metric_type"]

        if res.get("_params_key") != _params_key(p):
            st.warning(
                "⚠️ Shared settings changed since last run — results below may not match "
                "the current parameters. Click **Calculate MDE** to update."
            )

        with right:
            st.metric("Minimum Detectable Effect", f"{mde_rel:.1%}")
            c1, c2 = st.columns(2)
            c1.metric("N per Arm", f"{n:,}")
            if mt == "binary":
                c2.metric("Absolute MDE", f"{mde_abs * 100:.2f} pp")
            else:
                c2.metric("Absolute MDE", f"{mde_abs:.3g}")

            st.info(
                f"With **{n:,} users per arm**, you can detect a lift of at least "
                f"**{mde_rel:.1%}** with {p['target_power']:.0%} power at α={p['alpha']}."
            )
            st.success(f"If the true lift is ≥ {mde_rel:.1%}: **likely detectable.**")
            st.error(f"If the true lift is < {mde_rel:.1%}: **probably missed.**")

            # ── What the MDE means in practice ────────────
            st.divider()
            st.markdown("**What this MDE looks like in your metric**")

            treat_mean = bm * (1 + mde_rel)
            if mt == "binary":
                ctrl_label  = f"{bm * 100:.3f}%"
                treat_label = f"{treat_mean * 100:.3f}%"
                delta_label = f"+{mde_abs * 100:.3f} pp"
                unit_note   = "conversion rate"
            elif mt == "continuous":
                ctrl_label  = f"{bm:.4g}"
                treat_label = f"{treat_mean:.4g}"
                delta_label = f"+{mde_abs:.4g}"
                unit_note   = "mean value"
            else:  # ratio
                ctrl_label  = f"{bm:.4g}"
                treat_label = f"{treat_mean:.4g}"
                delta_label = f"+{mde_abs:.4g}"
                unit_note   = "ratio mean"

            card_ctrl, card_arrow, card_treat = st.columns([2, 1, 2])
            with card_ctrl:
                st.markdown(
                    f"""<div style="background:#f1f5f9;border-radius:8px;padding:14px 16px;text-align:center;">
                    <div style="font-size:11px;color:#64748b;font-weight:600;letter-spacing:.05em;">CONTROL</div>
                    <div style="font-size:26px;font-weight:700;color:#1e293b;margin:6px 0;">{ctrl_label}</div>
                    <div style="font-size:11px;color:#94a3b8;">{unit_note}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with card_arrow:
                st.markdown(
                    f"""<div style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;padding-top:10px;">
                    <div style="font-size:22px;color:#f97316;">→</div>
                    <div style="font-size:11px;font-weight:700;color:#f97316;margin-top:2px;">{delta_label}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with card_treat:
                st.markdown(
                    f"""<div style="background:#f0fdf4;border:1.5px solid #86efac;border-radius:8px;padding:14px 16px;text-align:center;">
                    <div style="font-size:11px;color:#16a34a;font-weight:600;letter-spacing:.05em;">TREATMENT</div>
                    <div style="font-size:26px;font-weight:700;color:#15803d;margin:6px 0;">{treat_label}</div>
                    <div style="font-size:11px;color:#86efac;">{unit_note}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            st.caption(
                f"The smallest change your experiment can reliably detect: "
                f"a {mde_rel:.1%} relative lift corresponds to moving the {unit_note} "
                f"from **{ctrl_label}** to **{treat_label}** ({delta_label})."
            )

            st.markdown("""
**Ways to increase sensitivity (lower MDE)**
- Run longer to collect more users
- Apply CUPED — can reduce variance 20–50%
- Narrow target audience to reduce metric variance
- Use a metric closer to the intervention point
""")

        # Power Sensitivity Matrix (full width)
        st.divider()
        st.subheader("Power Sensitivity Matrix")
        st.caption("Statistical power across every effect size × sample size combination.")
        st.markdown("**The amber boundary shows where your experiment becomes reliable.**")

        with st.spinner("Computing power matrix..."):
            heatmap_rows = sensitivity_heatmap(
                metric_type=p["metric_type"],
                baseline_mean=p["baseline_mean"],
                baseline_std=p["baseline_std"],
                effect_sizes=_mde_range(mde_rel),
                sample_sizes=_n_range(n),
                alpha=p["alpha"],
                n_sim=p["n_sim"],
                r_squared=p["r_squared"],
                icc=p["icc"],
                cluster_size=p["cluster_size"],
            )

        if heatmap_rows:
            st.altair_chart(
                power_matrix_chart(heatmap_rows, target_power=p["target_power"]),
                width="stretch",
            )
            with st.expander("📊 How to read this chart", expanded=False):
                st.markdown(f"""
**Statistically:** Each cell shows the probability of correctly detecting an effect of that size
at that sample size (statistical power). Cells **above the amber boundary** have ≥ {p['target_power']:.0%} power
and are statistically reliable. Cells below are underpowered: even if the true effect exists,
you're more likely to miss it than detect it.

**Business terms:** This matrix answers *"under exactly what conditions can we trust a result?"*

- A cell showing **84%** means: if the true effect is that size, your experiment will detect
  it 84% of the time — solid ground for a shipping decision.
- A cell showing **33%** means: you're more likely to get a false negative and ship nothing
  than to actually catch the effect. Don't use these cells to conclude "no effect."
- The **amber dots** mark the minimum sample size needed for each effect size to cross the
  {p['target_power']:.0%} power threshold. Only operate to the right of this boundary.
""")

        # Feasibility zone chart as secondary
        if p["daily_traffic"] > 0:
            st.divider()
            st.subheader("Feasibility & Duration")
            st.caption("How does the detectable effect change with experiment length?")
            target_mde_for_chart = round(mde_rel * 100, 1)
            with st.spinner("Computing feasibility curve..."):
                fc_rows = feasibility_curve(
                    metric_type=p["metric_type"],
                    baseline_mean=p["baseline_mean"],
                    baseline_std=p["baseline_std"],
                    alpha=p["alpha"],
                    target_power=p["target_power"],
                    daily_traffic=p["daily_traffic"],
                    n_sim=p["n_sim"],
                    r_squared=p["r_squared"],
                    icc=p["icc"],
                    cluster_size=p["cluster_size"],
                )
            if fc_rows:
                st.altair_chart(
                    feasibility_zone_chart(fc_rows, target_mde_pct=target_mde_for_chart),
                    width="stretch",
                )


# ── Sub-tab 3: How many users? ────────────────────────────

def _render_samplesize_sub(p: dict) -> None:
    left, right = st.columns([1, 1])

    with left:
        st.markdown("**How many users must enter the experiment per variant?**")
        mde_pct = st.slider(
            "Target MDE (%)", 1, 50, 10,
            help="Minimum relative lift you want to be able to detect.",
            key="pwr_ss_mde",
        )
        run = st.button("Calculate Sample Size", type="primary", key="run_ss")

    if run:
        effect_size = mde_pct / 100.0
        with st.spinner("Calculating..."):
            n_per_arm = sample_size_for_effect(
                metric_type=p["metric_type"],
                baseline_mean=p["baseline_mean"],
                baseline_std=p["baseline_std"],
                effect_size=effect_size,
                alpha=p["alpha"],
                target_power=p["target_power"],
                n_sim=p["n_sim"],
                r_squared=p["r_squared"],
                icc=p["icc"],
                cluster_size=p["cluster_size"],
            )
        days = n_per_arm / p["daily_traffic"] if p["daily_traffic"] > 0 else None
        st.session_state["pwr_ss_results"] = dict(
            n_per_arm=n_per_arm, days=days, mde_pct=mde_pct,
            baseline_mean=p["baseline_mean"], metric_type=p["metric_type"],
            _params_key=_params_key(p),
        )

    if "pwr_ss_results" in st.session_state:
        res = st.session_state["pwr_ss_results"]
        n_per_arm = res["n_per_arm"]
        days = res["days"]
        mde_pct_shown = res["mde_pct"]

        if res.get("_params_key") != _params_key(p):
            st.warning(
                "⚠️ Shared settings changed since last run — results below may not match "
                "the current parameters. Click **Calculate Sample Size** to update."
            )

        with right:
            st.metric("Required N per Variant", f"{n_per_arm:,}")
            c1, c2 = st.columns(2)
            c1.metric("Total N (both arms)", f"{n_per_arm * 2:,}")
            if days is not None:
                c2.metric("Est. Runtime", f"{days:.0f} days")
            else:
                c2.metric("Est. Runtime", "Set daily traffic")

            st.info(
                f"To detect a **{mde_pct_shown}% relative lift** with "
                f"{p['target_power']:.0%} power at α={p['alpha']}, you need "
                f"**{n_per_arm:,} users per variant** (**{n_per_arm * 2:,} total**)."
                + (f" At {p['daily_traffic']:,} users/day/arm that's **{days:.0f} days**." if days else "")
            )

            if n_per_arm >= 10_000_000:
                bm = res["baseline_mean"]
                abs_mde = (mde_pct_shown / 100) * bm
                st.error(
                    f"**{n_per_arm:,} users per arm** — this is a Google/Meta-scale requirement. "
                    f"Your absolute MDE ({abs_mde * 100:.4f} pp on a {bm*100:.2f}% baseline) is extremely small. "
                    f"At this precision, consider: (1) reframe MDE as a minimum business-meaningful absolute change, "
                    f"(2) use a proxy metric with higher signal-to-noise, "
                    f"or (3) apply CUPED (can reduce required N by 20–50%)."
                )

            st.markdown("""
**Key assumptions**
- Two-sided test (detecting lift or drop)
- Equal 50/50 traffic split between arms
- Independent observations (user-level randomization)
- Effect size = minimum business-meaningful lift
- Adjust with CUPED R² if your pipeline supports it
""")

        # Feasibility zone chart (full width)
        if p["daily_traffic"] > 0:
            st.divider()
            st.subheader("Feasibility & Duration")
            st.caption("How your sample size requirement changes with the target lift you choose to detect.")
            st.markdown(
                f"**At {mde_pct_shown}% MDE you need {n_per_arm:,} users per arm"
                + (f" — {days:.0f} days at your current traffic rate.**" if days else ".**")
            )
            with st.spinner("Computing feasibility curve..."):
                fc_rows = feasibility_curve(
                    metric_type=p["metric_type"],
                    baseline_mean=p["baseline_mean"],
                    baseline_std=p["baseline_std"],
                    alpha=p["alpha"],
                    target_power=p["target_power"],
                    daily_traffic=p["daily_traffic"],
                    n_sim=p["n_sim"],
                    r_squared=p["r_squared"],
                    icc=p["icc"],
                    cluster_size=p["cluster_size"],
                )
            if fc_rows:
                st.altair_chart(
                    feasibility_zone_chart(fc_rows, target_mde_pct=mde_pct_shown),
                    width="stretch",
                )
                with st.expander("📊 How to read this chart", expanded=False):
                    st.markdown("""
**Statistically:** The curve is the sample-size vs effect-size tradeoff. Required N grows as a
power law as you target smaller effects — halving the MDE roughly quadruples the required sample
size for binary and continuous metrics. The zones reflect what teams can realistically commit to.

**Business terms:** The orange dot is your experiment. Tracing left along the curve shows how
many more weeks each smaller MDE target costs. Use this chart to anchor scope conversations:

> *"To detect a 5% lift we need 8 weeks, but a 10% lift only needs 2 weeks.
> What's the minimum business-meaningful effect — and is it worth the extra time?"*

If the dot is in the orange or red zone, show this chart to stakeholders and ask whether
accepting a wider MDE (right on the curve) would still answer the product question.
""")


# ── Sub-tab 4: Subgroup Power ─────────────────────────────

_DEFAULT_SEG_NAMES = ["iOS users", "Android users", "New users",
                      "Returning users", "Mobile web", "Desktop"]
# Defaults sum to 100% for 3 segments (35+45+20); user adjusts for other counts.
_DEFAULT_SEG_FRACS = [35, 45, 20, 15, 10, 5]


def _render_subgroup_sub(p: dict) -> None:
    st.info(
        "**This tool is for Pre-Specified Subgroup Analysis only.** "
        "Segments and their traffic shares must be defined *before* the experiment runs. "
        "Post-hoc subgroup slicing (\"let's see how iOS users did after unblinding\") inflates "
        "false positive rates and is not covered here — use **🔬 Multiple Testing** instead "
        "to correct for looking at many slices after the fact.",
        icon="📋",
    )
    st.caption(
        "Each pre-specified subgroup contains only a fraction of total traffic → fewer users per arm "
        "→ larger implied MDE. Quantify this cost before launch so you know which segments "
        "support confirmatory conclusions and which are directional only."
    )

    # ── Pull overall N + MDE from whichever prior sub-tab ran ─────────────
    default_n   = 5_000
    default_mde = 10.0   # %

    if "pwr_sens_results" in st.session_state:
        r = st.session_state["pwr_sens_results"]
        default_n   = r["n_per_arm"]
        default_mde = round(r["mde_rel"] * 100, 2)
    elif "pwr_dur_results" in st.session_state:
        r = st.session_state["pwr_dur_results"]
        default_n   = r["n_per_arm"]
        default_mde = float(r["mde_pct"])
    elif "pwr_ss_results" in st.session_state:
        r = st.session_state["pwr_ss_results"]
        default_n   = r["n_per_arm"]
        default_mde = float(r["mde_pct"])

    col1, col2 = st.columns(2)
    with col1:
        overall_n = st.number_input(
            "Overall N per arm",
            min_value=50, value=int(default_n), step=500,
            help=(
                "Total users per arm in the full experiment. "
                "Pre-populated from any prior calculation in this tab; edit manually if needed."
            ),
            key="pwr_sub_n",
        )
    with col2:
        overall_mde = st.number_input(
            "Overall MDE (%)",
            min_value=0.1, max_value=100.0, value=float(default_mde),
            step=0.5, format="%.1f",
            help="The minimum detectable effect for the overall experiment (% relative lift).",
            key="pwr_sub_mde",
        )

    st.divider()
    st.subheader("Define Segments")
    n_segments = st.slider(
        "Number of segments", 2, 6, 3,
        key="pwr_sub_n_segs",
        help="How many subgroups do you plan to analyse separately?",
    )

    segments = []
    seg_cols = st.columns(2)
    for i in range(n_segments):
        with seg_cols[i % 2]:
            inner = st.columns([3, 2])
            name = inner[0].text_input(
                f"Segment {i+1} name",
                value=_DEFAULT_SEG_NAMES[i] if i < len(_DEFAULT_SEG_NAMES) else f"Segment {i+1}",
                key=f"pwr_sub_name_{i}",
            )
            frac_pct = inner[1].number_input(
                "Traffic %",
                min_value=1, max_value=100,
                value=_DEFAULT_SEG_FRACS[i] if i < len(_DEFAULT_SEG_FRACS) else 50,
                step=5,
                key=f"pwr_sub_frac_{i}",
            )
            segments.append({"name": name or f"Segment {i+1}", "fraction": frac_pct / 100.0})

    # ── Live traffic total + 100% validation ──────────────────────────────
    total_pct = sum(s["fraction"] * 100 for s in segments)
    total_ok = abs(total_pct - 100.0) <= 0.5   # allow ±0.5 pp rounding

    if total_ok:
        st.success(f"Traffic total: **{total_pct:.0f}%** ✓ — segments are mutually exclusive and exhaustive.")
    else:
        st.error(
            f"Traffic shares must sum to **100%**. Currently: **{total_pct:.0f}%**. "
            f"{'Add' if total_pct < 100 else 'Remove'} "
            f"{abs(100 - total_pct):.0f} pp to proceed."
        )

    run = st.button("Compute Subgroup MDEs", type="primary", key="run_sub",
                    disabled=not total_ok)

    if run:
        overall_mde_rel = overall_mde / 100.0
        with st.spinner("Computing implied MDEs..."):
            rows = subgroup_mde_table(
                metric_type=p["metric_type"],
                baseline_mean=p["baseline_mean"],
                baseline_std=p["baseline_std"],
                overall_n_per_arm=int(overall_n),
                overall_mde_rel=overall_mde_rel,
                segments=segments,
                alpha=p["alpha"],
                target_power=p["target_power"],
                n_sim=p["n_sim"],
                r_squared=p["r_squared"],
                icc=p["icc"],
                cluster_size=p["cluster_size"],
            )
        st.session_state["pwr_sub_results"] = {
            "rows": rows,
            "overall_n": int(overall_n),
            "overall_mde": overall_mde,
            "_params_key": _params_key(p),
        }

    if "pwr_sub_results" in st.session_state:
        res = st.session_state["pwr_sub_results"]

        if res.get("_params_key") != _params_key(p):
            st.warning(
                "⚠️ Shared settings changed since last run — "
                "click **Compute Subgroup MDEs** to refresh."
            )

        rows = res["rows"]
        overall_mde_val = res["overall_mde"]

        # ── Scorecard ──────────────────────────────────────────────────────
        st.divider()
        n_powered = sum(1 for r in rows if r["adequately_powered"])
        sc1, sc2, sc3 = st.columns(3)
        sc1.metric("Segments defined", len(rows))
        sc2.metric(
            "Adequately powered ✓", n_powered,
            delta=None if n_powered == len(rows) else f"{len(rows) - n_powered} underpowered",
            delta_color="off" if n_powered == len(rows) else "inverse",
        )
        sc3.metric("Overall MDE", f"{overall_mde_val:.1f}%")

        # ── Bar chart ──────────────────────────────────────────────────────
        st.altair_chart(
            subgroup_mde_chart(rows, overall_mde_pct=overall_mde_val,
                               target_power=p["target_power"]),
            width="stretch",
        )

        # ── Detail table ───────────────────────────────────────────────────
        def _power_color(val):
            if val >= p["target_power"]:
                return "background-color: #d1fae5; color: #065f46"
            elif val >= p["target_power"] * 0.75:
                return "background-color: #fef3c7; color: #92400e"
            return "background-color: #fee2e2; color: #991b1b"

        power_col = f"Power at {overall_mde_val:.1f}% MDE"
        df_sub = pd.DataFrame([{
            "Segment":       r["segment"],
            "Traffic share": f"{r['fraction']:.0%}",
            "N per arm":     r["n_per_arm"],
            "Implied MDE":   f"{r['implied_mde_pct']:.2f}%",
            "vs. Overall":   (f"+{r['mde_delta_pp']:.2f} pp" if r["mde_delta_pp"] >= 0
                              else f"{r['mde_delta_pp']:.2f} pp"),
            power_col:       r["power_at_overall_mde"],
        } for r in rows])

        st.dataframe(
            df_sub.style
            .map(_power_color, subset=[power_col])
            .format({power_col: "{:.0%}"}),
            width="stretch",
            hide_index=True,
        )

        # ── Interpretation ─────────────────────────────────────────────────
        with st.expander("📊 How to interpret this table", expanded=False):
            st.markdown(f"""
**Implied MDE** — The smallest effect detectable *within that segment alone* at
**{p['target_power']:.0%} power**. Smaller segments → fewer users → larger implied MDE → worse sensitivity.
This is expected and not a flaw in your design.

**vs. Overall** — How many percentage points larger the segment's MDE is compared to the
full-experiment threshold. A "+8 pp" means that segment needs an effect 8 pp larger than
your overall target to be detectable at the same power level.

**{power_col}** — If the true effect is exactly the overall MDE ({overall_mde_val:.1f}%),
this is the probability of detecting it *within that segment*.
- **Green (≥ {p['target_power']:.0%})**: Safe to draw segment-level conclusions at the overall threshold.
- **Yellow (≥ {p['target_power']*0.75:.0%})**: Marginal — treat as directional only.
- **Red (< {p['target_power']*0.75:.0%})**: Effectively blind to an effect at the overall MDE size.

**What to do with red/yellow segments:**
- Report them as *directional* (consistent with the overall result) rather than independently significant.
- If a segment conclusion is critical to the shipping decision, re-power the experiment targeting that
  segment's implied MDE — not the overall MDE.
- If all segments are red: your subgroup ambitions exceed the traffic budget. Narrow to fewer segments,
  increase overall runtime, or pre-register only the primary metric for segment analysis.
""")


# ── Main Entry Point ──────────────────────────────────────

def render():
    st.header("Experiment Planner")
    st.caption(
        "Answer the three questions every experiment team needs to answer before launching."
    )

    with st.expander("📖 About this tool — click to learn how to use it", expanded=False):
        st.markdown("""
        ### What is this tool for?
        Before launching any experiment, every team needs to answer three fundamental questions:

        1. **How long do I need to run?** — Given a target lift, how many days until you have enough data?
        2. **What can I detect?** — Given a fixed runtime or traffic budget, what's the smallest effect you can reliably catch?
        3. **How many users do I need?** — Given a target lift, what's the exact sample size per variant?

        This planner answers all three, and pairs each answer with a **decision-oriented visual** so
        you can immediately see whether your experiment is feasible, and what the tradeoffs look like
        at neighboring options.

        ---
        ### Key concepts

        **Statistical Power** is the probability your experiment correctly detects a real effect when one exists.
        - Power = 0.80: if the treatment truly works, you'll catch it 80% of the time.
        - The remaining 20% are missed detections (**Type II errors / false negatives**).
        - Standard: **80%** for most decisions. Use **90%** for high-stakes launches.

        **Minimum Detectable Effect (MDE)** is the smallest relative lift your experiment can reliably detect.
        - If your MDE is 15% but the product team expects a 5% lift — you are **underpowered**.
        - MDE and sample size trade off directly: more users → smaller MDE → subtler effects detectable.

        **Significance Level (α)** is the false positive rate.
        - α = 0.05: 5% chance of a spurious positive if the null hypothesis is true.
        - **Set α before running, never after seeing results.** Adjusting post-hoc is p-hacking.

        ---
        ### Recommended workflow
        1. Set your **metric type** and **baseline** from 30–90 days of historical data.
        2. Set your **daily traffic per arm** (total daily users ÷ 2 for a 50/50 split).
        3. Pick a sub-tab based on your constraint:
           - *Know your target lift?* → **How long to run?** or **How many users?**
           - *Know your runtime or traffic budget?* → **What can I detect?**
        4. Check the **Feasibility & Duration chart** to see which zone your experiment falls in.
        5. In sub-tab 2, check the **Power Sensitivity Matrix** to see the full option space.

        ---
        ### Feasibility zones
        | Zone | Duration | What it means |
        |------|----------|---------------|
        | VIABLE | ≤ 2 weeks | Fast, low risk of external confounds |
        | PATIENCE | 2–4 weeks | Standard; most product experiments land here |
        | MARGINAL | 4–8 weeks | Long; novelty effects and seasonality become real concerns |
        | NOT VIABLE | > 8 weeks | Too long; reconsider metric, MDE target, or traffic allocation |

        ---
        ### Advanced adjustments (CUPED & Clustering)
        - **CUPED R²**: If your analysis pipeline uses pre-experiment covariates (ANCOVA), variance is reduced by `(1 − R²)`. R²=0.3 is common for engagement metrics.
        - **Clustering ICC**: Use when randomization is at a higher level than measurement (e.g. geo/market). Higher ICC + larger cluster size → need more total users.
        """)

    p = _shared_params()

    st.divider()

    sub1, sub2, sub3, sub4 = st.tabs([
        "⏱ How long to run?",
        "🎯 What can I detect?",
        "👥 How many users?",
        "🔍 Subgroup Power",
    ])

    with sub1:
        _render_duration_sub(p)

    with sub2:
        _render_sensitivity_sub(p)

    with sub3:
        _render_samplesize_sub(p)

    with sub4:
        _render_subgroup_sub(p)
