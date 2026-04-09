"""
Reusable Altair chart helpers for the experiment tool.
"""

import altair as alt
import numpy as np
import pandas as pd
from scipy import stats as scipy_stats


CHART_WIDTH = 620
CHART_HEIGHT = 320
COLOR_SCALE = alt.Scale(scheme="blues")


def power_curve_chart(data: dict, target_power: float = 0.8) -> alt.Chart:
    """Line chart of power vs sample size per arm."""
    df = pd.DataFrame(data)
    base = alt.Chart(df).mark_line(color="#2563eb", strokeWidth=2.5).encode(
        x=alt.X("n_per_arm:Q", title="Sample Size per Arm"),
        y=alt.Y("power:Q", title="Statistical Power", scale=alt.Scale(domain=[0, 1])),
        tooltip=["n_per_arm", alt.Tooltip("power:Q", format=".3f")],
    )
    rule = alt.Chart(pd.DataFrame({"power": [target_power]})).mark_rule(
        color="#dc2626", strokeDash=[6, 3], strokeWidth=1.5
    ).encode(y="power:Q")
    label = alt.Chart(pd.DataFrame({"power": [target_power], "label": [f"Target {target_power:.0%}"]})).mark_text(
        align="left", dx=5, dy=-8, color="#dc2626", fontSize=11
    ).encode(y="power:Q", text="label:N", x=alt.value(0))
    return (base + rule + label).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Power Curve"
    ).configure_view(strokeWidth=0)


def sensitivity_heatmap_chart(rows: list[dict]) -> alt.Chart:
    """Heatmap of power across effect sizes × sample sizes."""
    df = pd.DataFrame(rows)
    return alt.Chart(df).mark_rect().encode(
        x=alt.X("n_per_arm:O", title="Sample Size per Arm"),
        y=alt.Y("effect_size:O", title="Effect Size"),
        color=alt.Color(
            "power:Q",
            scale=alt.Scale(scheme="blues", domain=[0, 1]),
            title="Power",
        ),
        tooltip=["effect_size", "n_per_arm", alt.Tooltip("power:Q", format=".3f")],
    ).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Sensitivity Heatmap"
    ).configure_view(strokeWidth=0)


def alpha_spending_chart(rows: list[dict]) -> alt.Chart:
    """Line + point chart of cumulative alpha spent at each look."""
    df = pd.DataFrame(rows)
    line = alt.Chart(df).mark_line(color="#7c3aed", strokeWidth=2).encode(
        x=alt.X("look:O", title="Interim Look"),
        y=alt.Y("cumulative_alpha_spent:Q", title="Cumulative Alpha Spent", scale=alt.Scale(domain=[0, 0.1])),
        tooltip=["look", alt.Tooltip("cumulative_alpha_spent:Q", format=".5f"), alt.Tooltip("z_boundary:Q", format=".3f")],
    )
    points = alt.Chart(df).mark_circle(size=70, color="#7c3aed").encode(
        x="look:O",
        y="cumulative_alpha_spent:Q",
    )
    return (line + points).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Alpha Spending Curve"
    ).configure_view(strokeWidth=0)


def stopping_distribution_chart(looks: list[int], counts: list[int]) -> alt.Chart:
    """Bar chart of stopping look distribution."""
    df = pd.DataFrame({"look": looks, "count": counts})
    df["pct"] = df["count"] / df["count"].sum()
    return alt.Chart(df).mark_bar(color="#059669", opacity=0.8).encode(
        x=alt.X("look:O", title="Stopping Look"),
        y=alt.Y("pct:Q", title="Proportion of Experiments", axis=alt.Axis(format=".0%")),
        tooltip=["look", alt.Tooltip("pct:Q", format=".1%")],
    ).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Early Stopping Distribution (among experiments that rejected H₀)"
    ).configure_view(strokeWidth=0)


def variance_decomposition_bar(rows: list[dict]) -> alt.Chart:
    """Horizontal bar chart of variance components."""
    df = pd.DataFrame(rows)
    df["abs_pct"] = df["pct"].abs()
    color_map = {
        "Numerator Variance": "#2563eb",
        "Denominator Variance": "#f59e0b",
        "Covariance Adjustment": "#10b981",
    }
    return alt.Chart(df).mark_bar(opacity=0.85).encode(
        y=alt.Y("component:N", title=None, sort="-x"),
        x=alt.X("abs_pct:Q", title="% Contribution to Total Variance"),
        color=alt.Color(
            "component:N",
            scale=alt.Scale(
                domain=list(color_map.keys()),
                range=list(color_map.values()),
            ),
            legend=None,
        ),
        tooltip=["component", alt.Tooltip("abs_pct:Q", format=".1f", title="% Contribution")],
    ).properties(
        width=CHART_WIDTH, height=200, title="Variance Decomposition by Component"
    ).configure_view(strokeWidth=0)


def traffic_shift_chart(rows: list[dict]) -> alt.Chart:
    """Line chart of std error vs traffic shift %."""
    df = pd.DataFrame(rows)
    return alt.Chart(df).mark_line(color="#f59e0b", strokeWidth=2.5, point=True).encode(
        x=alt.X("traffic_shift_pct:Q", title="Traffic Shift (%)"),
        y=alt.Y("std_error:Q", title="Standard Error of Ratio"),
        tooltip=["traffic_shift_pct", "n", alt.Tooltip("std_error:Q", format=".6f")],
    ).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Standard Error vs Traffic Volume"
    ).configure_view(strokeWidth=0)


def did_trajectory_chart(rows: list[dict]) -> alt.Chart:
    """Line chart of treated vs control trajectories across pre/post periods."""
    df = pd.DataFrame(rows)
    base = alt.Chart(df)
    treated = base.transform_filter(
        alt.datum.violation == df["violation"].iloc[0]
    )
    line_treat = base.mark_line(strokeWidth=2).encode(
        x=alt.X("period:Q", title="Period (0 = treatment start)"),
        y=alt.Y("treated_mean:Q", title="Outcome"),
        color=alt.Color("violation:N", title="Trend Violation"),
        strokeDash=alt.value([1, 0]),
    )
    line_ctrl = base.mark_line(strokeWidth=2, strokeDash=[5, 3], opacity=0.6).encode(
        x="period:Q",
        y=alt.Y("control_mean:Q", title="Outcome"),
        color=alt.Color("violation:N"),
    )
    rule = alt.Chart(pd.DataFrame({"period": [0]})).mark_rule(
        color="#6b7280", strokeDash=[4, 4], strokeWidth=1
    ).encode(x="period:Q")
    return (line_treat + line_ctrl + rule).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Treated (solid) vs Control (dashed) Trajectories"
    ).configure_view(strokeWidth=0)


def bias_violation_chart(rows: list[dict]) -> alt.Chart:
    """Line chart of DiD bias as a function of trend violation."""
    df = pd.DataFrame(rows)
    bias_line = alt.Chart(df).mark_line(color="#dc2626", strokeWidth=2.5, point=True).encode(
        x=alt.X("trend_violation:Q", title="Pre-trend Violation Magnitude"),
        y=alt.Y("bias:Q", title="Estimation Bias"),
        tooltip=["trend_violation", alt.Tooltip("bias:Q", format=".4f"), alt.Tooltip("power:Q", format=".3f")],
    )
    zero = alt.Chart(pd.DataFrame({"bias": [0]})).mark_rule(
        color="#6b7280", strokeDash=[4, 4]
    ).encode(y="bias:Q")
    return (bias_line + zero).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="DiD Bias vs Pre-trend Violation"
    ).configure_view(strokeWidth=0)


def did_power_chart(rows: list[dict]) -> alt.Chart:
    """Line chart of DiD power vs number of units."""
    df = pd.DataFrame(rows)
    return alt.Chart(df).mark_line(color="#2563eb", strokeWidth=2.5, point=True).encode(
        x=alt.X("n_units:Q", title="Number of Units"),
        y=alt.Y("power:Q", title="Power", scale=alt.Scale(domain=[0, 1])),
        tooltip=["n_units", alt.Tooltip("power:Q", format=".3f")],
    ).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="DiD Power vs Sample Size"
    ).configure_view(strokeWidth=0)


def funnel_bar_chart(rows: list[dict]) -> alt.Chart:
    """Grouped bar chart comparing baseline vs treatment volumes per stage."""
    df = pd.DataFrame(rows)
    stage_order = df["stage"].unique().tolist()
    return alt.Chart(df).mark_bar(opacity=0.85).encode(
        x=alt.X("arm:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("volume:Q", title="Users"),
        color=alt.Color(
            "arm:N",
            scale=alt.Scale(domain=["Baseline", "Treatment"], range=["#94a3b8", "#2563eb"]),
            legend=alt.Legend(title="Arm"),
        ),
        column=alt.Column("stage:N", sort=stage_order, title="Funnel Stage",
                          header=alt.Header(labelAngle=-30, labelAlign="right")),
        tooltip=["stage", "arm", alt.Tooltip("volume:Q", format=",.0f")],
    ).properties(
        width=80, height=CHART_HEIGHT, title="Funnel Volumes: Baseline vs Treatment"
    ).configure_view(strokeWidth=0)


def funnel_incremental_chart(stage_names: list[str], incremental: list[float]) -> alt.Chart:
    """Horizontal bar chart of incremental users per funnel stage."""
    df = pd.DataFrame({"stage": stage_names, "incremental": incremental})
    df["color"] = df["incremental"].apply(lambda x: "gain" if x >= 0 else "loss")
    return alt.Chart(df).mark_bar(opacity=0.85).encode(
        y=alt.Y("stage:N", sort=stage_names, title=None),
        x=alt.X("incremental:Q", title="Incremental Users (Treatment − Baseline)"),
        color=alt.Color(
            "color:N",
            scale=alt.Scale(domain=["gain", "loss"], range=["#10b981", "#ef4444"]),
            legend=None,
        ),
        tooltip=["stage", alt.Tooltip("incremental:Q", format=",.1f")],
    ).properties(
        width=CHART_WIDTH, height=200, title="Incremental Users per Stage"
    ).configure_view(strokeWidth=0)


def sensitivity_heatmap_funnel(rows: list[dict]) -> alt.Chart:
    """Heatmap of net MAU delta across uplift × decay combinations."""
    df = pd.DataFrame(rows)
    return alt.Chart(df).mark_rect().encode(
        x=alt.X("decay:O", title="Downstream Decay Rate"),
        y=alt.Y("uplift:O", title="Treatment Uplift"),
        color=alt.Color(
            "net_mau_delta_pct:Q",
            scale=alt.Scale(scheme="blues"),
            title="Net MAU Δ%",
        ),
        tooltip=[
            "uplift", "decay",
            alt.Tooltip("net_mau_delta:Q", format=",.0f", title="Net MAU Δ"),
            alt.Tooltip("net_mau_delta_pct:Q", format=".2f", title="Net MAU Δ%"),
            alt.Tooltip("revenue_delta:Q", format=",.0f", title="Revenue Δ ($)"),
        ],
    ).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Sensitivity: Net MAU Δ% (Uplift × Decay)"
    ).configure_view(strokeWidth=0)


def feasibility_zone_chart(rows: list, target_mde_pct=None) -> alt.Chart:
    """
    Feasibility & Duration chart: hyperbolic curve of (MDE%, weeks) over colored zone bands.
    Optionally highlights a specific MDE target with an orange annotated point.
    """
    df = pd.DataFrame(rows)
    max_mde = df["mde_pct"].max() if not df.empty else 50

    # Zone background bands
    zone_df = pd.DataFrame([
        {"y1": 0,  "y2": 2,  "x_min": 0, "x_max": max_mde, "zone": "VIABLE",     "color": "#d1fae5", "label_y": 1},
        {"y1": 2,  "y2": 4,  "x_min": 0, "x_max": max_mde, "zone": "PATIENCE",   "color": "#fef3c7", "label_y": 3},
        {"y1": 4,  "y2": 8,  "x_min": 0, "x_max": max_mde, "zone": "MARGINAL",   "color": "#ffedd5", "label_y": 6},
        {"y1": 8,  "y2": 20, "x_min": 0, "x_max": max_mde, "zone": "NOT VIABLE", "color": "#fee2e2", "label_y": 13},
    ])
    zone_color_scale = alt.Scale(
        domain=["VIABLE", "PATIENCE", "MARGINAL", "NOT VIABLE"],
        range=["#d1fae5", "#fef3c7", "#ffedd5", "#fee2e2"],
    )
    bands = alt.Chart(zone_df).mark_rect(opacity=0.5).encode(
        x=alt.X("x_min:Q", scale=alt.Scale(domain=[0, max_mde])),
        x2="x_max:Q",
        y=alt.Y("y1:Q", scale=alt.Scale(domain=[0, 20])),
        y2="y2:Q",
        color=alt.Color("zone:N", scale=zone_color_scale, legend=None),
        tooltip=alt.value(None),
    )

    # Zone labels on right side
    label_df = zone_df.copy()
    label_df["x_label"] = max_mde * 0.97
    zone_text_color = alt.Scale(
        domain=["VIABLE", "PATIENCE", "MARGINAL", "NOT VIABLE"],
        range=["#065f46", "#92400e", "#c2410c", "#b91c1c"],
    )
    zone_labels = alt.Chart(label_df).mark_text(
        align="right", fontWeight="bold", fontSize=10
    ).encode(
        x=alt.X("x_label:Q"),
        y=alt.Y("label_y:Q"),
        text="zone:N",
        color=alt.Color("zone:N", scale=zone_text_color, legend=None),
        tooltip=alt.value(None),
    )

    # Feasibility curve — line
    point_color_scale = alt.Scale(
        domain=["VIABLE", "PATIENCE", "MARGINAL", "NOT VIABLE"],
        range=["#10b981", "#f59e0b", "#f97316", "#ef4444"],
    )
    curve_line = alt.Chart(df).mark_line(color="#1e293b", strokeWidth=2.5).encode(
        x=alt.X("mde_pct:Q", title="MDE (% relative lift)"),
        y=alt.Y("weeks:Q", title="Weeks to reach significance", scale=alt.Scale(domain=[0, 20])),
        tooltip=[
            alt.Tooltip("mde_pct:Q", title="MDE (%)"),
            alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
            alt.Tooltip("n_per_arm:Q", title="N per Arm", format=","),
            alt.Tooltip("zone:N", title="Zone"),
        ],
    )
    curve_points = alt.Chart(df).mark_circle(size=70).encode(
        x="mde_pct:Q",
        y="weeks:Q",
        color=alt.Color("zone:N", scale=point_color_scale, legend=None),
        tooltip=[
            alt.Tooltip("mde_pct:Q", title="MDE (%)"),
            alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
            alt.Tooltip("n_per_arm:Q", title="N per Arm", format=","),
            alt.Tooltip("zone:N", title="Zone"),
        ],
    )

    layers = [bands, zone_labels, curve_line, curve_points]

    # Highlight target point if provided
    if target_mde_pct is not None and not df.empty:
        target_row = df.iloc[(df["mde_pct"] - target_mde_pct).abs().argsort()[:1]]
        if not target_row.empty:
            highlight = alt.Chart(target_row).mark_point(
                size=200, color="#f97316", filled=True, strokeWidth=2, stroke="white"
            ).encode(
                x="mde_pct:Q",
                y="weeks:Q",
                tooltip=[
                    alt.Tooltip("mde_pct:Q", title="Your target MDE (%)"),
                    alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
                    alt.Tooltip("n_per_arm:Q", title="N per Arm", format=","),
                    alt.Tooltip("zone:N", title="Zone"),
                ],
            )
            annotation = alt.Chart(target_row).mark_text(
                align="left", dx=10, dy=-8, fontSize=10, fontWeight="bold", color="#f97316"
            ).encode(
                x="mde_pct:Q",
                y="weeks:Q",
                text=alt.Text("n_per_arm:Q", format=","),
            )
            layers += [highlight, annotation]

    return alt.layer(*layers).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Feasibility & Duration"
    ).configure_view(strokeWidth=0)


def power_matrix_chart(rows: list, target_power: float = 0.80) -> alt.Chart:
    """
    Power Sensitivity Matrix: heatmap with power % text in each cell
    and an amber boundary curve at the target power threshold.
    """
    df = pd.DataFrame(rows)
    df["power_pct"] = (df["power"] * 100).round(0).astype(int).astype(str) + "%"

    # Determine ordinal sort orders
    n_order = sorted(df["n_per_arm"].unique().tolist())
    es_order = df["effect_size"].unique().tolist()

    # Boundary: for each effect_size, minimum n_per_arm where power >= target_power
    boundary_rows = []
    for es, grp in df.groupby("effect_size"):
        above = grp[grp["power"] >= target_power].sort_values("n_per_arm")
        if not above.empty:
            min_n = above["n_per_arm"].iloc[0]
            boundary_rows.append({"effect_size": es, "n_per_arm": min_n})
    boundary_df = pd.DataFrame(boundary_rows) if boundary_rows else pd.DataFrame(columns=["effect_size", "n_per_arm"])

    base = alt.Chart(df)

    heatmap = base.mark_rect().encode(
        x=alt.X("n_per_arm:O", title="Sample Size per Arm", sort=n_order),
        y=alt.Y("effect_size:O", title="Effect Size", sort=es_order),
        color=alt.Color(
            "power:Q",
            scale=alt.Scale(scheme="greens", domain=[0, 1]),
            title="Power",
        ),
        tooltip=[
            "effect_size",
            alt.Tooltip("n_per_arm:Q", format=",", title="N per Arm"),
            alt.Tooltip("power:Q", format=".1%", title="Power"),
        ],
    )

    text_layer = base.mark_text(fontSize=11, fontWeight="bold").encode(
        x=alt.X("n_per_arm:O", sort=n_order),
        y=alt.Y("effect_size:O", sort=es_order),
        text="power_pct:N",
        color=alt.condition(
            alt.datum.power >= 0.65,
            alt.value("white"),
            alt.value("#374151"),
        ),
    )

    layers = [heatmap, text_layer]

    if not boundary_df.empty:
        boundary_points = alt.Chart(boundary_df).mark_point(
            size=300, filled=False, strokeWidth=3, color="#f97316"
        ).encode(
            x=alt.X("n_per_arm:O", sort=n_order),
            y=alt.Y("effect_size:O", sort=es_order),
            tooltip=[
                alt.Tooltip("effect_size:N", title="Effect Size"),
                alt.Tooltip("n_per_arm:Q", format=",", title="Min N for boundary"),
            ],
        )
        # Label the first boundary cell
        first_boundary = boundary_df.sort_values("n_per_arm").head(1)
        boundary_label = alt.Chart(
            first_boundary.assign(label=f"{target_power:.0%} power boundary →")
        ).mark_text(
            align="right", dx=-8, dy=-14, fontSize=9, fontWeight="bold", color="#f97316"
        ).encode(
            x=alt.X("n_per_arm:O", sort=n_order),
            y=alt.Y("effect_size:O", sort=es_order),
            text="label:N",
        )
        layers += [boundary_points, boundary_label]

    return alt.layer(*layers).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Power Sensitivity Matrix"
    ).configure_view(strokeWidth=0)


def tradeoff_curve_chart(rows: list) -> alt.Chart:
    """Line + point chart of MDE% vs experiment duration in days."""
    df = pd.DataFrame(rows)
    line = alt.Chart(df).mark_line(color="#2563eb", strokeWidth=2.5).encode(
        x=alt.X("days:Q", title="Duration (days)"),
        y=alt.Y("mde_relative_pct:Q", title="MDE (%)", scale=alt.Scale(zero=False)),
        tooltip=[
            alt.Tooltip("days:Q", title="Days"),
            alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
            alt.Tooltip("n_per_arm:Q", title="N per Arm", format=","),
            alt.Tooltip("mde_relative_pct:Q", title="MDE (%)", format=".2f"),
        ],
    )
    points = alt.Chart(df).mark_circle(size=80, color="#2563eb").encode(
        x="days:Q",
        y="mde_relative_pct:Q",
        tooltip=[
            alt.Tooltip("days:Q", title="Days"),
            alt.Tooltip("weeks:Q", title="Weeks", format=".1f"),
            alt.Tooltip("n_per_arm:Q", title="N per Arm", format=","),
            alt.Tooltip("mde_relative_pct:Q", title="MDE (%)", format=".2f"),
        ],
    )
    return (line + points).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT, title="MDE % vs Experiment Duration"
    ).configure_view(strokeWidth=0)


def correction_threshold_chart(rows: list, n_tests: int) -> alt.Chart:
    """
    Line chart: per-test alpha threshold vs number of metrics tested.
    Shows how Bonferroni, Šidák, and No Correction thresholds shrink as k grows.
    A vertical dashed line marks the current n_tests.
    """
    df = pd.DataFrame(rows)
    method_colors = alt.Scale(
        domain=["No Correction", "Bonferroni", "Šidák"],
        range=["#94a3b8", "#2563eb", "#7c3aed"],
    )
    line = alt.Chart(df).mark_line(strokeWidth=2.5).encode(
        x=alt.X("n_tests:Q", title="Number of Metrics Tested", axis=alt.Axis(values=list(range(1, 21)))),
        y=alt.Y("threshold:Q", title="Per-Test Alpha Threshold"),
        color=alt.Color("method:N", scale=method_colors, legend=alt.Legend(title="Method")),
        tooltip=[
            alt.Tooltip("method:N", title="Method"),
            alt.Tooltip("n_tests:Q", title="# Tests"),
            alt.Tooltip("threshold:Q", format=".5f", title="Per-test α"),
        ],
    )
    current = alt.Chart(df[df["n_tests"] == n_tests]).mark_circle(size=120, opacity=1).encode(
        x="n_tests:Q",
        y="threshold:Q",
        color=alt.Color("method:N", scale=method_colors, legend=None),
    )
    vline = alt.Chart(pd.DataFrame({"x": [n_tests]})).mark_rule(
        color="#374151", strokeDash=[5, 3], strokeWidth=1.5
    ).encode(x="x:Q")
    label = alt.Chart(pd.DataFrame({"x": [n_tests], "text": [f"k={n_tests}"]})).mark_text(
        align="left", dx=6, dy=-10, fontSize=10, color="#374151"
    ).encode(x="x:Q", text="text:N", y=alt.value(20))
    return (line + current + vline + label).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT,
        title="How Correction Thresholds Shrink with More Metrics",
    ).configure_view(strokeWidth=0)


def rejection_heatmap_chart(all_results: dict, metric_labels: list) -> alt.Chart:
    """
    Heatmap: correction method (Y) × metric (X), colored by rejected/not rejected.
    all_results: {method_name: list[{metric_index, rejected, original_p, adjusted_threshold}]}
    metric_labels: list of metric name strings (same length as p_values).
    """
    records = []
    method_order = ["No Correction", "Bonferroni", "Šidák", "Holm-Bonferroni", "Benjamini-Hochberg (FDR)"]
    for method in method_order:
        if method not in all_results:
            continue
        for r in all_results[method]:
            idx = r["metric_index"] - 1
            records.append({
                "method": method,
                "metric": metric_labels[idx] if idx < len(metric_labels) else f"M{r['metric_index']}",
                "rejected": r["rejected"],
                "status": "Rejected ✓" if r["rejected"] else "Not Rejected",
                "original_p": r["original_p"],
                "adjusted_threshold": r["adjusted_threshold"],
            })
    df = pd.DataFrame(records)
    metric_order = metric_labels if metric_labels else sorted(df["metric"].unique().tolist())

    heatmap = alt.Chart(df).mark_rect(stroke="white", strokeWidth=2).encode(
        x=alt.X("metric:O", title="Metric", sort=metric_order),
        y=alt.Y("method:O", title=None, sort=method_order),
        color=alt.Color(
            "status:N",
            scale=alt.Scale(
                domain=["Rejected ✓", "Not Rejected"],
                range=["#059669", "#fca5a5"],
            ),
            legend=alt.Legend(title="Decision"),
        ),
        tooltip=[
            alt.Tooltip("method:N", title="Method"),
            alt.Tooltip("metric:N", title="Metric"),
            alt.Tooltip("original_p:Q", format=".4f", title="p-value"),
            alt.Tooltip("adjusted_threshold:Q", format=".5f", title="Threshold"),
            alt.Tooltip("status:N", title="Decision"),
        ],
    )
    text = alt.Chart(df).mark_text(fontSize=11, fontWeight="bold").encode(
        x=alt.X("metric:O", sort=metric_order),
        y=alt.Y("method:O", sort=method_order),
        text=alt.Text("original_p:Q", format=".3f"),
        color=alt.condition(
            alt.datum.rejected,
            alt.value("white"),
            alt.value("#374151"),
        ),
    )
    return (heatmap + text).properties(
        width=CHART_WIDTH, height=220,
        title="Rejection Decisions by Method and Metric (p-values shown in cells)",
    ).configure_view(strokeWidth=0)


def risk_gauge_chart(flags: list) -> alt.Chart:
    """Horizontal lollipop chart for risk scores."""
    color_map = {"green": "#10b981", "yellow": "#f59e0b", "red": "#ef4444"}
    df = pd.DataFrame([
        {"risk": f.name, "score": f.score, "level": f.level, "color": color_map[f.level]}
        for f in flags
    ])
    base = alt.Chart(df)
    bars = base.mark_bar(height=8, opacity=0.7).encode(
        y=alt.Y("risk:N", title=None, sort="-x"),
        x=alt.X("score:Q", title="Risk Score (0–100)", scale=alt.Scale(domain=[0, 100])),
        color=alt.Color("level:N", scale=alt.Scale(
            domain=["green", "yellow", "red"],
            range=["#10b981", "#f59e0b", "#ef4444"]
        ), legend=alt.Legend(title="Risk Level")),
        tooltip=["risk", alt.Tooltip("score:Q", format=".0f"), "level"],
    )
    points = base.mark_circle(size=100).encode(
        y=alt.Y("risk:N", sort="-x"),
        x="score:Q",
        color=alt.Color("level:N", scale=alt.Scale(
            domain=["green", "yellow", "red"],
            range=["#10b981", "#f59e0b", "#ef4444"]
        ), legend=None),
    )
    return (bars + points).properties(
        width=CHART_WIDTH, height=300, title="Experiment Risk Dashboard"
    ).configure_view(strokeWidth=0)


# ── A/A Simulator charts ───────────────────────────────────────────────────────

def aa_pvalue_histogram(p_values: list, alpha: float) -> alt.Chart:
    """
    P-value distribution from A/A simulation. Should be approximately uniform.
    Red bins = rejection zone (p < α). Dashed line = expected count under uniform H₀.
    """
    p = np.array(p_values)
    n_sim = len(p)
    n_bins = 20
    bin_edges = np.linspace(0, 1, n_bins + 1)
    counts, _ = np.histogram(p, bins=bin_edges)
    expected_count = n_sim / n_bins

    df = pd.DataFrame({
        "bin_start": bin_edges[:-1],
        "bin_end": bin_edges[1:],
        "count": counts,
        "zone": [
            "Rejection zone (p < α)" if s < alpha else "Acceptance zone"
            for s in bin_edges[:-1]
        ],
    })

    bars = alt.Chart(df).mark_bar(stroke="white", strokeWidth=0.8).encode(
        x=alt.X("bin_start:Q", title="p-value", scale=alt.Scale(domain=[0, 1])),
        x2="bin_end:Q",
        y=alt.Y("count:Q", title="Simulation Count"),
        color=alt.Color(
            "zone:N",
            scale=alt.Scale(
                domain=["Rejection zone (p < α)", "Acceptance zone"],
                range=["#ef4444", "#93c5fd"],
            ),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("bin_start:Q", format=".2f", title="p ≥"),
            alt.Tooltip("bin_end:Q", format=".2f", title="p <"),
            alt.Tooltip("count:Q", title="Count"),
        ],
    )
    rule = alt.Chart(pd.DataFrame({"y": [expected_count]})).mark_rule(
        color="#374151", strokeDash=[5, 3], strokeWidth=2
    ).encode(y=alt.Y("y:Q", title="Simulation Count"))

    annotation = alt.Chart(
        pd.DataFrame({"y": [expected_count * 1.04], "x": [0.5], "t": [f"Uniform expected = {expected_count:.0f}"]})
    ).mark_text(fontSize=10, color="#374151", fontStyle="italic").encode(
        x=alt.X("x:Q", scale=alt.Scale(domain=[0, 1])),
        y="y:Q",
        text="t:N",
    )

    return (bars + rule + annotation).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT,
        title="P-value Distribution — should be flat/uniform under correct randomization",
    ).configure_view(strokeWidth=0)


def aa_zstat_histogram(z_stats: list, alpha: float) -> alt.Chart:
    """
    Test statistic distribution from A/A simulation vs N(0,1) theoretical curve.
    Shaded tails = rejection regions. Curve = expected N(0,1) density scaled to counts.
    """
    z = np.array(z_stats)
    n_sim = len(z)
    z_crit = float(scipy_stats.norm.ppf(1 - alpha / 2))

    z_abs_max = max(float(np.percentile(np.abs(z), 99.5)), z_crit + 1.5)
    n_bins = 40
    bin_edges = np.linspace(-z_abs_max, z_abs_max, n_bins + 1)
    counts, _ = np.histogram(z, bins=bin_edges)
    bin_w = bin_edges[1] - bin_edges[0]
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    df_hist = pd.DataFrame({
        "bin_start": bin_edges[:-1],
        "bin_end": bin_edges[1:],
        "bin_center": bin_centers,
        "count": counts,
        "zone": [
            "Rejection region" if abs(c) > z_crit else "Acceptance region"
            for c in bin_centers
        ],
    })

    # N(0,1) PDF scaled to histogram count units
    z_fine = np.linspace(-z_abs_max, z_abs_max, 300)
    pdf_scaled = scipy_stats.norm.pdf(z_fine) * n_sim * bin_w
    df_pdf = pd.DataFrame({"z": z_fine, "density": pdf_scaled})

    bars = alt.Chart(df_hist).mark_bar(stroke="white", strokeWidth=0.4, opacity=0.8).encode(
        x=alt.X("bin_start:Q", title="Test Statistic (z)", scale=alt.Scale(domain=[-z_abs_max, z_abs_max])),
        x2="bin_end:Q",
        y=alt.Y("count:Q", title="Count"),
        color=alt.Color(
            "zone:N",
            scale=alt.Scale(
                domain=["Rejection region", "Acceptance region"],
                range=["#f87171", "#93c5fd"],
            ),
            legend=alt.Legend(title=None),
        ),
        tooltip=[
            alt.Tooltip("bin_center:Q", format=".2f", title="z"),
            alt.Tooltip("count:Q", title="Count"),
            alt.Tooltip("zone:N", title="Zone"),
        ],
    )
    pdf_line = alt.Chart(df_pdf).mark_line(
        color="#1e293b", strokeWidth=2.5, strokeDash=[],
    ).encode(
        x=alt.X("z:Q", scale=alt.Scale(domain=[-z_abs_max, z_abs_max])),
        y="density:Q",
        tooltip=alt.value(None),
    )
    # Critical value rules
    crit_df = pd.DataFrame({"x": [-z_crit, z_crit]})
    crit_rules = alt.Chart(crit_df).mark_rule(
        color="#dc2626", strokeDash=[5, 3], strokeWidth=1.5
    ).encode(x="x:Q")

    return (bars + pdf_line + crit_rules).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT,
        title=f"Test Statistic Distribution vs N(0,1) — critical values at ±{z_crit:.2f}",
    ).configure_view(strokeWidth=0)


def aa_fpr_accumulation(running_fpr: list, alpha: float) -> alt.Chart:
    """
    Running cumulative false positive rate across simulations.
    Starts noisy; should converge to α as n_sim grows.
    """
    df = pd.DataFrame(running_fpr)   # [{sim, fpr}, ...]

    line = alt.Chart(df).mark_line(color="#2563eb", strokeWidth=2).encode(
        x=alt.X("sim:Q", title="Simulation Run"),
        y=alt.Y("fpr:Q", title="Cumulative False Positive Rate",
                scale=alt.Scale(domain=[0, min(1.0, alpha * 4)])),
        tooltip=[
            alt.Tooltip("sim:Q", title="Simulation #"),
            alt.Tooltip("fpr:Q", format=".3f", title="Cumulative FPR"),
        ],
    )
    target = alt.Chart(pd.DataFrame({"y": [alpha]})).mark_rule(
        color="#dc2626", strokeDash=[6, 3], strokeWidth=1.5
    ).encode(y=alt.Y("y:Q"))

    label_df = pd.DataFrame({"y": [alpha], "x": [df["sim"].max() * 0.02], "t": [f"α = {alpha}"]})
    target_label = alt.Chart(label_df).mark_text(
        align="left", dx=4, dy=-8, fontSize=10, color="#dc2626", fontWeight="bold"
    ).encode(x="x:Q", y="y:Q", text="t:N")

    return (line + target + target_label).properties(
        width=CHART_WIDTH, height=CHART_HEIGHT,
        title="Running False Positive Rate — converges to α as simulations accumulate",
    ).configure_view(strokeWidth=0)


def aa_srm_chart(variants: list) -> alt.Chart:
    """
    Grouped bar chart: observed vs expected user counts per variant.
    variants: list of dicts with keys Variant, Observed, Expected.
    """
    records = []
    for v in variants:
        records.append({"Variant": v["Variant"], "Type": "Observed",
                         "Count": v["Observed"], "pct_diff": v["% Difference"]})
        records.append({"Variant": v["Variant"], "Type": "Expected",
                         "Count": v["Expected"], "pct_diff": 0.0})
    df = pd.DataFrame(records)

    bars = alt.Chart(df).mark_bar(opacity=0.85).encode(
        x=alt.X("Type:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Count:Q", title="User Count"),
        color=alt.Color(
            "Type:N",
            scale=alt.Scale(
                domain=["Observed", "Expected"],
                range=["#2563eb", "#94a3b8"],
            ),
            legend=alt.Legend(title=None),
        ),
        column=alt.Column(
            "Variant:N", title="Variant",
            header=alt.Header(labelAngle=0, labelAlign="center"),
        ),
        tooltip=[
            alt.Tooltip("Variant:N"),
            alt.Tooltip("Type:N"),
            alt.Tooltip("Count:Q", format=","),
            alt.Tooltip("pct_diff:Q", format="+.2f", title="% diff from expected"),
        ],
    )
    return bars.properties(
        width=max(80, CHART_WIDTH // max(len(variants), 1)),
        height=CHART_HEIGHT,
        title="Observed vs Expected User Counts per Variant",
    ).configure_view(strokeWidth=0)


def results_forest_plot(metric_data: list) -> alt.Chart:
    """
    Forest plot: one horizontal CI bar per metric on a common relative-change (%) x-axis.
    metric_data: list of dicts with keys: name, role, relative_change, rel_ci_lo, rel_ci_hi, verdict, significant.
    """
    df = pd.DataFrame(metric_data)
    df["rc_pct"]    = (df["relative_change"] * 100).round(2)
    df["ci_lo_pct"] = (df["rel_ci_lo"] * 100).round(2)
    df["ci_hi_pct"] = (df["rel_ci_hi"] * 100).round(2)

    x_max = max(
        df[["ci_lo_pct", "ci_hi_pct"]].abs().max().max() * 1.25,
        5.0,
    )

    role_order = ["North Star ⭐", "Supporting 📊", "Guardrail 🛡️"]
    metric_order = sorted(
        df["name"].tolist(),
        key=lambda n: next((i for i, r in enumerate(role_order) if df.loc[df["name"] == n, "role"].iloc[0] == r), 99),
    )

    verdict_colors = alt.Scale(
        domain=["win", "loss", "neutral"],
        range=["#059669", "#dc2626", "#94a3b8"],
    )

    ci_bars = alt.Chart(df).mark_bar(height=14, opacity=0.35).encode(
        y=alt.Y("name:O", sort=metric_order, title=None),
        x=alt.X("ci_lo_pct:Q", title="Relative Change (%)", scale=alt.Scale(domain=[-x_max, x_max])),
        x2="ci_hi_pct:Q",
        color=alt.Color("verdict:N", scale=verdict_colors, legend=None),
        tooltip=[
            alt.Tooltip("name:N", title="Metric"),
            alt.Tooltip("role:N", title="Role"),
            alt.Tooltip("rc_pct:Q", format="+.2f", title="Relative Δ (%)"),
            alt.Tooltip("ci_lo_pct:Q", format="+.2f", title="CI Lower (%)"),
            alt.Tooltip("ci_hi_pct:Q", format="+.2f", title="CI Upper (%)"),
        ],
    )
    points = alt.Chart(df).mark_circle(size=90, opacity=1).encode(
        y=alt.Y("name:O", sort=metric_order),
        x="rc_pct:Q",
        color=alt.Color("verdict:N", scale=verdict_colors, legend=alt.Legend(title="Outcome")),
        tooltip=[
            alt.Tooltip("name:N", title="Metric"),
            alt.Tooltip("role:N", title="Role"),
            alt.Tooltip("rc_pct:Q", format="+.2f", title="Relative Δ (%)"),
            alt.Tooltip("ci_lo_pct:Q", format="+.2f", title="CI Lower (%)"),
            alt.Tooltip("ci_hi_pct:Q", format="+.2f", title="CI Upper (%)"),
        ],
    )
    zero = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(
        color="#1e293b", strokeWidth=2
    ).encode(x="x:Q")

    row_h = max(80, len(df) * 64)
    return (ci_bars + points + zero).properties(
        width=CHART_WIDTH, height=row_h,
        title="Effect Estimates — 95% Confidence Intervals (relative change %)",
    ).configure_view(strokeWidth=0)


def results_traffic_chart(metric_data: list, ctrl_name: str, treat_name: str) -> alt.Chart:
    """
    Grouped bar chart comparing user counts per metric per arm.
    metric_data: list of dicts with keys: name, ctrl_n, treat_n.
    """
    records = []
    for m in metric_data:
        records.append({"Metric": m["name"], "Arm": ctrl_name,  "Users": m["ctrl_n"]})
        records.append({"Metric": m["name"], "Arm": treat_name, "Users": m["treat_n"]})
    df = pd.DataFrame(records)
    metric_names = [m["name"] for m in metric_data]

    return alt.Chart(df).mark_bar(opacity=0.85).encode(
        x=alt.X("Arm:N", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("Users:Q", title="Users"),
        color=alt.Color(
            "Arm:N",
            scale=alt.Scale(
                domain=[ctrl_name, treat_name],
                range=["#94a3b8", "#2563eb"],
            ),
            legend=alt.Legend(title="Arm"),
        ),
        column=alt.Column(
            "Metric:N", sort=metric_names, title="Metric",
            header=alt.Header(labelAngle=-20, labelAlign="right"),
        ),
        tooltip=["Metric", "Arm", alt.Tooltip("Users:Q", format=",")],
    ).properties(
        width=max(60, CHART_WIDTH // max(len(metric_data), 1)),
        height=240,
        title="Traffic Distribution per Arm",
    ).configure_view(strokeWidth=0)
