"""
Tool 8: Funnel Transition Simulator
Models multi-stage funnel with treatment uplift at a specific stage,
downstream decay, and spillover. Outputs net MAU impact and revenue delta.
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class FunnelResult:
    stage_names: list[str]
    baseline_volumes: list[float]
    treated_volumes: list[float]
    baseline_cvrs: list[float]
    treated_cvrs: list[float]
    net_mau_delta: float
    net_mau_delta_pct: float
    revenue_delta: float
    revenue_delta_pct: float
    incremental_users_per_stage: list[float]


def simulate_funnel(
    stage_names: list[str],
    baseline_cvrs: list[float],           # conversion rate at each stage
    top_of_funnel_n: float,               # users entering stage 1
    treatment_stage: int,                 # 0-indexed stage where uplift is applied
    treatment_uplift: float,              # relative lift at treatment stage (e.g. 0.10)
    downstream_decay: float,              # pct of uplift retained each subsequent stage (e.g. 0.8 = 80%)
    retention_multiplier: float = 1.0,   # multiplier on final retained users
    spillover_effect: float = 0.0,        # spillover boost to adjacent stages (signed, fraction)
    revenue_per_user: float = 10.0,       # ARPU at bottom of funnel
) -> FunnelResult:
    """
    Simulate a multi-stage funnel with a treatment uplift at one stage.
    Downstream decay models how uplift attenuates at later stages.
    """
    n_stages = len(stage_names)

    # ── Baseline volumes ──────────────────────────────────
    baseline_vols = [top_of_funnel_n]
    for i in range(1, n_stages):
        baseline_vols.append(baseline_vols[-1] * baseline_cvrs[i - 1])
    # Final output (MAU)
    baseline_mau = baseline_vols[-1] * baseline_cvrs[-1]

    # ── Treated CVRs ─────────────────────────────────────
    treated_cvrs = list(baseline_cvrs)

    # Apply uplift at treatment_stage
    treated_cvrs[treatment_stage] = baseline_cvrs[treatment_stage] * (1 + treatment_uplift)

    # Downstream decay: uplift fades at each stage after treatment
    decay_remaining = 1.0
    for i in range(treatment_stage + 1, n_stages):
        decay_remaining *= downstream_decay
        treated_cvrs[i] = baseline_cvrs[i] * (1 + treatment_uplift * decay_remaining)

    # Spillover: boost the stage before treatment (if any)
    if spillover_effect != 0.0 and treatment_stage > 0:
        treated_cvrs[treatment_stage - 1] = baseline_cvrs[treatment_stage - 1] * (1 + spillover_effect)

    # ── Treated volumes ───────────────────────────────────
    treated_vols = [top_of_funnel_n]
    for i in range(1, n_stages):
        treated_vols.append(treated_vols[-1] * treated_cvrs[i - 1])
    treated_mau = treated_vols[-1] * treated_cvrs[-1] * retention_multiplier

    # ── Deltas ────────────────────────────────────────────
    net_mau_delta = treated_mau - baseline_mau
    net_mau_delta_pct = net_mau_delta / baseline_mau * 100 if baseline_mau > 0 else 0.0
    revenue_delta = net_mau_delta * revenue_per_user
    revenue_delta_pct = net_mau_delta_pct

    incremental = [t - b for t, b in zip(treated_vols, baseline_vols)]

    return FunnelResult(
        stage_names=stage_names,
        baseline_volumes=baseline_vols,
        treated_volumes=treated_vols,
        baseline_cvrs=baseline_cvrs,
        treated_cvrs=treated_cvrs,
        net_mau_delta=round(net_mau_delta, 1),
        net_mau_delta_pct=round(net_mau_delta_pct, 3),
        revenue_delta=round(revenue_delta, 1),
        revenue_delta_pct=round(revenue_delta_pct, 3),
        incremental_users_per_stage=[round(x, 1) for x in incremental],
    )


def funnel_chart_data(result: FunnelResult) -> list[dict]:
    """Return rows for funnel bar chart."""
    rows = []
    for i, name in enumerate(result.stage_names):
        rows.append({"stage": name, "volume": result.baseline_volumes[i], "arm": "Baseline"})
        rows.append({"stage": name, "volume": result.treated_volumes[i], "arm": "Treatment"})
    return rows


def cvr_comparison_data(result: FunnelResult) -> list[dict]:
    """Return rows for CVR comparison chart."""
    rows = []
    for i, name in enumerate(result.stage_names):
        rows.append({
            "stage": name,
            "cvr": result.baseline_cvrs[i],
            "arm": "Baseline",
            "pct": f"{result.baseline_cvrs[i]:.1%}",
        })
        rows.append({
            "stage": name,
            "cvr": result.treated_cvrs[i],
            "arm": "Treatment",
            "pct": f"{result.treated_cvrs[i]:.1%}",
        })
    return rows


def sensitivity_sweep(
    stage_names: list[str],
    baseline_cvrs: list[float],
    top_of_funnel_n: float,
    treatment_stage: int,
    treatment_uplifts: list[float],
    downstream_decays: list[float],
    revenue_per_user: float = 10.0,
) -> list[dict]:
    """
    Sweep over (uplift × decay) combinations for a sensitivity table.
    """
    rows = []
    for uplift in treatment_uplifts:
        for decay in downstream_decays:
            result = simulate_funnel(
                stage_names=stage_names,
                baseline_cvrs=baseline_cvrs,
                top_of_funnel_n=top_of_funnel_n,
                treatment_stage=treatment_stage,
                treatment_uplift=uplift,
                downstream_decay=decay,
                revenue_per_user=revenue_per_user,
            )
            rows.append({
                "uplift": f"{uplift:.0%}",
                "decay": f"{decay:.0%}",
                "net_mau_delta": round(result.net_mau_delta, 0),
                "net_mau_delta_pct": round(result.net_mau_delta_pct, 2),
                "revenue_delta": round(result.revenue_delta, 0),
            })
    return rows
