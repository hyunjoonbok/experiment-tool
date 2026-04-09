"""
UI Tab 10: A/A Test Simulator
Two sub-tabs:
  1. False Positive Simulator — given traffic, how often does a no-effect experiment
     falsely detect significance? Validates alpha calibration before going live.
  2. Randomization Check — SRM detection via chi-square test on observed traffic counts.
"""

import streamlit as st
import pandas as pd

from tools.aa_simulator import simulate_aa, srm_check, multi_metric_fp_table
from utils.charts import (
    aa_pvalue_histogram,
    aa_zstat_histogram,
    aa_fpr_accumulation,
    aa_srm_chart,
)


# ── Health-check helper ────────────────────────────────────────────────────────

def _calibration_verdict(fpr, alpha, ci_lo, ci_hi, ks_p, z_std):
    """Return (status, icon, detail) based on multiple calibration indicators."""
    fpr_ok = ci_lo <= alpha <= ci_hi
    ks_ok = ks_p > 0.05
    zstd_ok = abs(z_std - 1.0) < 0.10

    n_pass = sum([fpr_ok, ks_ok, zstd_ok])
    if n_pass == 3:
        return "success", "✅", "All three calibration checks pass — randomization looks healthy."
    elif n_pass == 2:
        return "warning", "⚠️", "One calibration check flagged. Review the charts below."
    else:
        return "error", "🔴", "Multiple calibration checks failed — possible randomization bias."


# ── Sub-tab 1: False Positive Simulator ───────────────────────────────────────

def _render_simulation():
    st.subheader("False Positive Simulator")
    st.caption(
        "Simulate experiments where **both arms are identical** — no treatment effect. "
        "Shows how often you'd declare a winner purely by chance, and whether your "
        "randomisation produces correctly-calibrated p-values."
    )

    # ── Inputs ────────────────────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        metric_type = st.selectbox(
            "Metric Type",
            ["binary", "continuous"],
            format_func=lambda x: {
                "binary": "Binary (conversion, click)",
                "continuous": "Continuous (revenue, session length)",
            }[x],
            help=(
                "**Binary**: Bernoulli outcomes (0/1). Uses pooled two-proportion z-test.\n\n"
                "**Continuous**: Numeric per-user outcomes. Uses exact CLT simulation of "
                "two-sample t-statistics — memory-efficient regardless of N per arm."
            ),
            key="aa_metric_type",
        )
        if metric_type == "binary":
            baseline_mean = st.number_input(
                "Baseline Conversion Rate",
                value=0.10, min_value=0.001, max_value=0.999, format="%.4f",
                help="E.g. 0.10 = 10% conversion. Both arms use this same rate in an A/A test.",
                key="aa_baseline_mean_bin",
            )
            baseline_std = float((baseline_mean * (1 - baseline_mean)) ** 0.5)
            st.caption(f"Auto std = √(p·(1−p)) = **{baseline_std:.4f}**")
        else:
            baseline_mean = st.number_input(
                "Baseline Mean",
                value=50.0, min_value=0.001, format="%.2f",
                help="Average metric value per user. Same in both arms for A/A.",
                key="aa_baseline_mean_cont",
            )
            baseline_std = st.number_input(
                "Baseline Std Dev",
                value=20.0, min_value=0.001, format="%.2f",
                help="User-level standard deviation. Larger → more noise → needs more data.",
                key="aa_baseline_std",
            )

    with col2:
        alpha = st.slider(
            "Significance Level (α)",
            0.01, 0.10, 0.05, step=0.01,
            help=(
                "Your false positive threshold. Under correct randomization, the empirical "
                "false positive rate should be **very close to α**. "
                "A large deviation signals a calibration or randomization problem."
            ),
            key="aa_alpha",
        )
        daily_traffic = st.number_input(
            "Daily Traffic per Arm",
            min_value=10, value=1000, step=100,
            help="Unique users per day entering each arm (50/50 split assumed).",
            key="aa_daily_traffic",
        )
        experiment_days = st.slider(
            "Experiment Duration (days)",
            min_value=1, max_value=90, value=14,
            help="How long the experiment runs. Determines total N per arm.",
            key="aa_duration_days",
        )

    n_per_arm = daily_traffic * experiment_days
    st.info(
        f"**{n_per_arm:,} users per arm** over {experiment_days} days "
        f"({daily_traffic:,}/day). Both arms receive identical treatment in A/A.",
        icon="ℹ️",
    )

    with st.expander("Advanced settings", expanded=False):
        n_sim = st.select_slider(
            "Number of Simulated Experiments",
            options=[500, 1000, 2000, 5000, 10000],
            value=2000,
            help=(
                "Each simulated experiment draws two independent arms from the same distribution. "
                "More simulations → tighter confidence interval on the false positive rate. "
                "2000 gives ±1.0 pp CI at α=0.05; 10 000 gives ±0.4 pp."
            ),
            key="aa_n_sim",
        )
        seed = st.number_input(
            "Random Seed",
            min_value=0, max_value=99999, value=42,
            help="Fix the seed for reproducible results. Change to see simulation variance.",
            key="aa_seed",
        )

    # ── Run ───────────────────────────────────────────────────────────────
    st.divider()
    run = st.button("Run A/A Simulation", type="primary", key="run_aa_sim")

    if run or "aa_sim_results" in st.session_state:
        if run:
            with st.spinner(f"Simulating {n_sim:,} A/A experiments…"):
                result = simulate_aa(
                    metric_type=metric_type,
                    n_per_arm=n_per_arm,
                    baseline_mean=baseline_mean,
                    baseline_std=baseline_std,
                    alpha=alpha,
                    n_sim=n_sim,
                    seed=int(seed),
                )
            st.session_state["aa_sim_results"] = result

        res = st.session_state["aa_sim_results"]
        fpr = res["false_positive_rate"]
        ci_lo, ci_hi = res["fpr_ci"]
        n_fp = res["n_false_positives"]
        ks_p = res["ks_p_value"]
        z_std = res["z_std"]
        z_mean = res["z_mean"]
        r_n_sim = res["n_sim"]

        # ── Calibration scorecard ─────────────────────────────────────────
        st.subheader("Calibration Scorecard")
        verdict_status, verdict_icon, verdict_detail = _calibration_verdict(
            fpr, alpha, ci_lo, ci_hi, ks_p, z_std
        )
        getattr(st, verdict_status)(f"{verdict_icon} {verdict_detail}")

        c1, c2, c3 = st.columns(3)

        fpr_delta = round(fpr - alpha, 4)
        fpr_ok = ci_lo <= alpha <= ci_hi
        c1.metric(
            "Empirical FPR",
            f"{fpr:.3f}",
            delta=f"{fpr_delta:+.3f} vs expected {alpha}",
            delta_color="off" if fpr_ok else "inverse",
            help=(
                f"Fraction of {r_n_sim:,} A/A experiments that incorrectly rejected H₀. "
                f"95% CI: [{ci_lo:.3f}, {ci_hi:.3f}]. "
                f"Expected = α = {alpha}. "
                "If α is inside the CI, the test is well-calibrated."
            ),
        )
        ks_ok = ks_p > 0.05
        c2.metric(
            "KS Test p-value",
            f"{ks_p:.3f}",
            delta="✓ Uniform" if ks_ok else "✗ Non-uniform",
            delta_color="off" if ks_ok else "inverse",
            help=(
                "Kolmogorov-Smirnov test of whether p-values follow Uniform[0,1]. "
                "p > 0.05 → cannot reject uniformity → p-values are well-calibrated. "
                "p < 0.05 → p-values cluster near 0 or 1 → possible bias."
            ),
        )
        zstd_ok = abs(z_std - 1.0) < 0.10
        c3.metric(
            "Z-stat Std Dev",
            f"{z_std:.3f}",
            delta=f"mean = {z_mean:+.3f} (expected 0)",
            delta_color="off" if zstd_ok else "inverse",
            help=(
                "Standard deviation of all test statistics. Under H₀ with correct randomization, "
                "z-stats should be N(0,1): std ≈ 1.0, mean ≈ 0. "
                "Std > 1.1 suggests variance is inflated (over-rejection). "
                "Std < 0.9 suggests under-dispersion (conservative test)."
            ),
        )

        # Detailed check table
        check_df = pd.DataFrame([
            {
                "Check": "FPR calibration",
                "Result": f"{fpr:.3f}  (CI: {ci_lo:.3f}–{ci_hi:.3f})",
                "Expected": f"α = {alpha}",
                "Status": "✅ Pass" if fpr_ok else "❌ Fail",
            },
            {
                "Check": "P-value uniformity (KS)",
                "Result": f"p = {ks_p:.3f}  (KS stat = {res['ks_stat']:.4f})",
                "Expected": "p > 0.05",
                "Status": "✅ Pass" if ks_ok else "❌ Fail",
            },
            {
                "Check": "Z-stat dispersion",
                "Result": f"std = {z_std:.3f},  mean = {z_mean:.3f}",
                "Expected": "std ≈ 1.0,  mean ≈ 0",
                "Status": "✅ Pass" if zstd_ok else "❌ Fail",
            },
        ])
        st.dataframe(check_df, width="stretch", hide_index=True)

        # ── P-value distribution ──────────────────────────────────────────
        st.divider()
        st.subheader("P-value Distribution")
        st.caption(
            "Under correct randomization, p-values should be **uniformly distributed** on [0, 1] "
            f"— each of the 20 bins should hold approximately {r_n_sim // 20} simulations. "
            f"The red bins (p < {alpha}) are false positives; there should be roughly "
            f"{r_n_sim * alpha:.0f} of them ({alpha:.0%})."
        )
        st.altair_chart(aa_pvalue_histogram(res["p_values"], alpha), width="stretch")

        with st.expander("📊 How to read this chart", expanded=False):
            st.markdown(f"""
            **What you expect:** A flat histogram — every bin roughly the same height.
            The dashed line marks the exact uniform expectation ({r_n_sim // 20} per bin).

            **What signals a problem:**
            - **Too many small p-values (spike near 0):** Your randomization is biased —
              the two arms are systematically different even before treatment. Check your
              assignment mechanism (hashing function, cookie handling, network effects).
            - **Too few small p-values (spike near 1 or u-shaped):** Your variance is
              inflated — the standard error is too large. Check for variance estimation bugs
              or clustered observations treated as independent.
            - **Perfectly flat but FPR ≠ α:** Simulation noise — run more simulations.

            **Your result:** {n_fp} false positives out of {r_n_sim:,} simulations
            ({fpr:.1%}) vs expected {alpha:.1%}.
            {"✅ Within expected range." if fpr_ok else "⚠️ Outside expected range — inspect the distribution."}
            """)

        # ── Z-stat distribution ───────────────────────────────────────────
        st.divider()
        st.subheader("Test Statistic Distribution")
        st.caption(
            "Each bar is one bin of z-statistics. The black curve is the theoretical N(0,1) density. "
            "Red bars fall in the rejection region (|z| > z_critical). "
            f"There should be exactly {alpha:.0%} of bars in red."
        )
        st.altair_chart(aa_zstat_histogram(res["z_stats"], alpha), width="stretch")

        with st.expander("📊 How to read this chart", expanded=False):
            import scipy.stats as sc
            z_crit = sc.norm.ppf(1 - alpha / 2)
            st.markdown(f"""
            **What you expect:** Bars closely following the black N(0,1) bell curve.
            Critical values at ±{z_crit:.3f} — bars beyond these are false positives.

            **What signals a problem:**
            - **Bars exceed the N(0,1) curve in the tails:** Your test statistic has heavier
              tails than expected → you're rejecting too often. Common causes: correlated
              observations, variance underestimation, or non-normal data at small n.
            - **Bars fall below the N(0,1) curve in the tails:** Conservative test —
              you're not rejecting enough. Can happen with over-clustered standard errors.
            - **Distribution is shifted left or right:** Systematic bias in your randomization.
              The control and treatment arms are not drawn from the same distribution.

            **Your z-stat summary:** mean = {z_mean:+.4f} (expected 0),
            std = {z_std:.4f} (expected 1.0).
            """)

        # ── Running FPR ───────────────────────────────────────────────────
        st.divider()
        st.subheader("False Positive Rate — Convergence")
        st.caption(
            "Shows how the running false positive rate stabilises as more simulations accumulate. "
            "Noisy at the start; should settle near the red α line as n grows."
        )
        st.altair_chart(aa_fpr_accumulation(res["running_fpr"], alpha), width="stretch")

        # ── Multi-metric projection ───────────────────────────────────────
        st.divider()
        st.subheader("Multi-Metric False Positive Projection")
        st.caption(
            "If you test multiple metrics simultaneously **without correction**, "
            "how many false positives should you expect across your simulation runs?"
        )
        fp_table = multi_metric_fp_table(alpha, r_n_sim, max_metrics=10)
        df_fp = pd.DataFrame(fp_table)
        st.dataframe(
            df_fp.style.format({
                "FWER (no correction)": "{:.1%}",
                "Expected false positive runs": "{:.0f}",
                "Avg false positive metrics / experiment": "{:.2f}",
                "Bonferroni threshold per metric": "{:.5f}",
            }).background_gradient(
                subset=["FWER (no correction)"], cmap="RdYlGn_r", vmin=0, vmax=1
            ),
            width="stretch",
            hide_index=True,
        )
        with st.expander("Interpreting the table", expanded=False):
            st.markdown(f"""
            Each row shows what happens when you test **k metrics simultaneously at α={alpha}**
            with no multiple-testing correction:

            - **FWER** (Family-wise Error Rate): probability that **at least one** of the k
              metrics shows a false positive. With k=5: {1-(1-alpha)**5:.1%}.
            - **Expected false positive runs**: out of your {r_n_sim:,} A/A simulations,
              approximately this many experiments would declare at least one winner —
              even though no treatment exists.
            - **Avg false positive metrics / experiment**: on average, k × α metrics will
              look significant by chance per experiment.
            - **Bonferroni threshold**: use this as your per-metric significance threshold to
              control FWER ≤ {alpha:.0%}. See the Multiple Testing tab for more options.
            """)

    else:
        st.info(
            "Configure your experiment parameters above and click **Run A/A Simulation**. "
            "The simulation takes a few seconds for large n_sim settings.",
            icon="▶️",
        )


# ── Sub-tab 2: Randomization Check (SRM) ──────────────────────────────────────

def _render_srm_check():
    st.subheader("Randomization Check — Sample Ratio Mismatch (SRM)")
    st.caption(
        "Enter your **observed traffic counts** from a live or completed experiment. "
        "The chi-square test detects whether your actual split matches the intended split — "
        "a mismatch indicates a broken randomization pipeline."
    )

    with st.expander("📖 What is an SRM and why does it matter?", expanded=False):
        st.markdown("""
        ### Sample Ratio Mismatch (SRM)

        An SRM occurs when the observed fraction of users in each variant differs significantly
        from the intended split (e.g., you set 50/50 but observe 52/48). This is one of the most
        common and dangerous experiment bugs because:

        1. **It invalidates all your results.** If the split is wrong, users are not randomly
           assigned — some characteristic (likely correlated with your metric) is causing the
           imbalance. Effect estimates will be biased.
        2. **It's often invisible.** The experiment may show a "significant" result, but the
           effect is entirely due to the biased assignment, not the treatment.
        3. **It happens more than you think.** Kohavi et al. (2017) found SRMs in ~6% of
           experiments at Microsoft. Common causes: client-side logging drops, bot filtering
           applied asymmetrically, caching layers, redirect chains, A/B framework bugs.

        ### What causes SRM?

        | Root Cause | Description |
        |------------|-------------|
        | **Triggering / filtering** | Users excluded from one arm but not the other (e.g., browser filter, login check) |
        | **Redirect chains** | One variant has an extra redirect; some users drop before logging |
        | **Caching** | One variant is cached (fast); the other is not — different bot rates |
        | **Client-side logging** | JS fires differently per variant; missed events bias counts |
        | **Experiment overlap** | Another experiment running simultaneously captures users from one arm |
        | **Novelty effects** | Treatment users are more engaged → more sessions → duplicated user IDs |

        ### The SRM threshold

        Industry standard (Kohavi et al. 2020): use **p < 0.01** (not 0.05) to flag SRM.
        This stricter threshold reduces false SRM alerts while still catching real mismatches.
        """)

    # ── Inputs ────────────────────────────────────────────────────────────
    st.divider()
    n_variants = st.slider(
        "Number of Variants (including control)",
        min_value=2, max_value=5, value=2,
        key="aa_srm_n_variants",
        help="Total variants in your experiment including the control group.",
    )

    col_split, col_obs = st.columns(2)

    with col_split:
        st.markdown("**Intended Traffic Split**")
        use_equal = st.checkbox(
            "Equal split (1/k per variant)", value=True, key="aa_srm_equal_split"
        )
        fractions = []
        if use_equal:
            fractions = [1.0 / n_variants] * n_variants
            for i in range(n_variants):
                label = "Control" if i == 0 else f"Treatment {i}"
                st.caption(f"{label}: {fractions[i]:.1%}")
        else:
            raw_fracs = []
            for i in range(n_variants):
                label = "Control" if i == 0 else f"Treatment {i}"
                val = st.number_input(
                    f"% traffic → {label}",
                    min_value=1, max_value=98, value=int(100 / n_variants),
                    key=f"aa_srm_frac_{i}",
                )
                raw_fracs.append(val)
            total_pct = sum(raw_fracs)
            if abs(total_pct - 100) > 1:
                st.warning(f"Percentages sum to {total_pct}% — must equal 100%.")
                fractions = [r / total_pct for r in raw_fracs]
            else:
                fractions = [r / 100 for r in raw_fracs]

    with col_obs:
        st.markdown("**Observed User Counts**")
        observed = []
        names = []
        for i in range(n_variants):
            label = "Control" if i == 0 else f"Treatment {i}"
            names.append(label)
            count = st.number_input(
                f"Observed users — {label}",
                min_value=0, value=5000 if i == 0 else (4850 if i == 1 else 5000),
                step=10,
                key=f"aa_srm_obs_{i}",
                help=f"Number of unique users assigned to {label}.",
            )
            observed.append(int(count))

    # ── Run ───────────────────────────────────────────────────────────────
    st.divider()
    run_srm = st.button("Check for SRM", type="primary", key="run_aa_srm")

    if run_srm or "aa_srm_results" in st.session_state:
        if run_srm:
            if sum(observed) == 0:
                st.error("Enter at least one observed user count.")
                return
            result = srm_check(observed, fractions, names)
            st.session_state["aa_srm_results"] = result

        res = st.session_state["aa_srm_results"]

        if "error" in res:
            st.error(res["error"])
            return

        chi2 = res["chi2"]
        p_val = res["p_value"]
        total = res["total_users"]
        srm = res["srm_detected"]
        warn = res["warning_zone"]

        # ── Verdict ──────────────────────────────────────────────────────
        if srm:
            st.error(
                f"🔴 **SRM Detected** — p = {p_val:.4f} < 0.01  (χ² = {chi2:.2f}, {total:,} total users)\n\n"
                "Your observed traffic split differs significantly from the intended split. "
                "**Do not trust results from this experiment.** Investigate the randomization pipeline before proceeding."
            )
        elif warn:
            st.warning(
                f"⚠️ **Borderline** — p = {p_val:.4f} (between 0.01 and 0.05)  (χ² = {chi2:.2f})\n\n"
                "The split is slightly off. Not severe enough to invalidate results, but worth "
                "investigating if the difference persists across multiple checks."
            )
        else:
            st.success(
                f"✅ **No SRM** — p = {p_val:.4f} ≥ 0.01  (χ² = {chi2:.2f}, {total:,} total users)\n\n"
                "The observed traffic split is consistent with the intended allocation. "
                "Randomization quality check passed."
            )

        # ── Metrics ──────────────────────────────────────────────────────
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Chi-square Statistic", f"{chi2:.4f}",
                   help="Larger = more mismatch. Under correct randomization: ~chi2(k−1).")
        mc2.metric("P-value", f"{p_val:.4f}",
                   help="Probability of observing this mismatch by chance. Flag at < 0.01.")
        mc3.metric("Total Users", f"{total:,}",
                   help="Sum of observed users across all variants.")

        # ── Per-variant table ─────────────────────────────────────────────
        df_v = pd.DataFrame(res["variants"])

        def color_diff(val):
            try:
                v = float(val)
                if abs(v) > 2.0:
                    return "color: #dc2626; font-weight: bold"
                elif abs(v) > 1.0:
                    return "color: #d97706"
                return ""
            except (ValueError, TypeError):
                return ""

        st.dataframe(
            df_v.style
            .format({"Observed": "{:,}", "Expected": "{:,}", "Difference": "{:+,}", "% Difference": "{:+.2f}%"})
            .applymap(color_diff, subset=["% Difference"]),
            width="stretch",
            hide_index=True,
        )

        # ── SRM bar chart ─────────────────────────────────────────────────
        st.altair_chart(aa_srm_chart(res["variants"]), width="stretch")

        # ── Next steps ────────────────────────────────────────────────────
        if srm or warn:
            with st.expander("🔍 Debugging checklist", expanded=srm):
                st.markdown("""
                Work through these in order — most SRMs are caught by the first three:

                1. **Check your logging pipeline.** Are events from both variants reaching your
                   data warehouse at the same rate? Filter to experiment-start events only.
                2. **Check for redirect or page-load differences.** Does one variant have a
                   slower load time, extra redirect, or page error that causes drop-off before
                   the user is logged?
                3. **Check bot / spider filtering.** Is bot filtering applied identically to
                   both variants? Asymmetric filtering is the most common SRM cause.
                4. **Check experiment overlap.** Is another experiment running on the same
                   population? Overlapping experiments can steal users from one arm.
                5. **Check triggering conditions.** Are users eligible to enter your experiment
                   in both arms at identical rates? (Login requirement, feature flag gate, A/B
                   framework version mismatch.)
                6. **Run the SRM check on a pre-experiment period.** If you have data from before
                   the experiment started, check whether the same users would show an SRM in
                   historical data. A mismatch there confirms a pipeline issue.
                7. **Segment the SRM.** Break down observed counts by platform, country, new
                   vs returning users, browser. A variant-specific SRM in one segment identifies
                   the affected code path.
                """)
        else:
            with st.expander("📋 What to check next", expanded=False):
                st.markdown("""
                The traffic split looks healthy. A few additional checks before trusting results:

                - **Run SRM checks daily** during the experiment (not just at the end) —
                  a growing mismatch can appear mid-experiment due to caching warm-up or bot traffic.
                - **Check pre-experiment balance** on key metrics (e.g., historical conversion rate
                  per arm). Both arms should have similar pre-experiment distributions.
                - **Check for novelty effects** in the first 24–48 hours — early traffic often has
                  different characteristics.
                - **Verify your primary metric logs at the same rate** across arms — the SRM check
                  above tests assignment counts, not event counts.
                """)


# ── Main render ────────────────────────────────────────────────────────────────

def render():
    st.header("A/A Test Simulator")
    st.caption(
        "Run A/A tests before your real experiment to validate randomization quality "
        "and confirm your testing infrastructure is correctly calibrated."
    )

    with st.expander("📖 What is an A/A test and when should I run one?", expanded=False):
        st.markdown("""
        ### A/A testing: your experiment pipeline health check

        An **A/A test** assigns users to two groups (control and "treatment") but applies **no
        treatment** — both groups see identical experiences. Because there is no real effect,
        any statistically significant result is a false positive by definition.

        **Why run an A/A test?**

        | Goal | What it checks |
        |------|----------------|
        | Validate alpha calibration | Your p-values should be ~Uniform[0,1]. If not, your test statistic is miscalibrated → your α=0.05 isn't really 5%. |
        | Check randomization quality | The false positive rate across many A/A simulations should be ≈ α. |
        | Detect SRM before launch | Traffic split should exactly match your intended allocation. |
        | Verify metric logging | Pre-experiment metric distributions should be identical between arms. |

        **When to run A/A tests:**
        - When setting up a new A/B testing platform for the first time
        - After major infrastructure changes (new hashing function, new logging pipeline)
        - When a previous experiment showed a surprisingly large effect with no intuitive explanation
        - When onboarding a new metric into your experiment framework

        **Tab 1 (False Positive Simulator):** Simulates many A/A experiments and diagnoses
        whether your testing setup would produce correctly calibrated p-values.

        **Tab 2 (Randomization Check):** Enter your actual observed traffic counts to test
        whether the split matches your intended allocation (SRM detection).
        """)

    sim_tab, srm_tab = st.tabs(["📊 False Positive Simulator", "🎲 Randomization Check"])

    with sim_tab:
        _render_simulation()

    with srm_tab:
        _render_srm_check()
