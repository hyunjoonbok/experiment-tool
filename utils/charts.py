"""
Reusable Altair chart helpers for the experiment tool.
"""

import altair as alt
import pandas as pd


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
        width=CHART_WIDTH, height=CHART_HEIGHT, title="Stopping Look Distribution"
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
