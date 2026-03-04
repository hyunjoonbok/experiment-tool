"""
Tool 6: Causal Design Selector
Interactive decision tree that recommends the right causal inference method
based on study characteristics.
"""

from dataclasses import dataclass, field


@dataclass
class CausalDesign:
    method: str
    confidence: str          # "High", "Medium", "Low"
    required_assumptions: list[str]
    sensitivity_checks: list[str]
    model_spec: str          # example model specification
    pros: list[str]
    cons: list[str]
    when_to_use: str


# ── Design library ────────────────────────────────────────
DESIGNS: dict[str, CausalDesign] = {

    "A/B Test": CausalDesign(
        method="A/B Test (Randomized Controlled Trial)",
        confidence="High",
        required_assumptions=[
            "Random assignment of units to treatment/control",
            "SUTVA: no spillover between arms",
            "No differential attrition",
            "Single randomization point",
        ],
        sensitivity_checks=[
            "SRM check (chi-square on observed vs expected allocation)",
            "Pre-experiment covariate balance check (t-tests on age, tenure, etc.)",
            "Novelty effect: plot day-over-day metric trend",
            "Holdout validation on a subset",
        ],
        model_spec=(
            "OLS: Y = α + β·Treatment + ε\n"
            "With covariates (CUPED): Y_adj = Y - θ·X_pre\n"
            "Y_adj = α + β·Treatment + ε\n"
            "where θ = Cov(Y, X_pre) / Var(X_pre)"
        ),
        pros=[
            "Unbiased ATE under valid randomization",
            "No model assumptions needed for identification",
            "Simple to explain to stakeholders",
        ],
        cons=[
            "Requires ability to randomize",
            "Susceptible to SRM and novelty effects",
            "SUTVA violated in networked products",
        ],
        when_to_use="Use when you can randomize users/sessions and features don't have network effects.",
    ),

    "Difference-in-Differences": CausalDesign(
        method="Difference-in-Differences (DiD)",
        confidence="Medium",
        required_assumptions=[
            "Parallel trends: treated and control would follow same trend absent treatment",
            "No anticipation effect before treatment",
            "Stable composition of treatment/control groups",
            "Common support: overlap in covariates",
        ],
        sensitivity_checks=[
            "Pre-trend test: regress outcome on time × treated in pre-period (should be ~0)",
            "Placebo test: apply treatment to an earlier 'fake' period",
            "Sensitivity to control group choice",
            "Heterogeneous treatment timing (Callaway-Sant'Anna estimator)",
        ],
        model_spec=(
            "Two-way FE DiD:\n"
            "Y_it = α_i + γ_t + β·(Treated_i × Post_t) + ε_it\n\n"
            "Staggered (Callaway-Sant'Anna):\n"
            "ATT(g,t) = E[Y_t - Y_{g-1} | G=g] - E[Y_t - Y_{g-1} | C]\n\n"
            "SE: Cluster standard errors at unit level"
        ),
        pros=[
            "Handles time-invariant confounders via FE",
            "Works with observational data",
            "Intuitive before/after + treated/control framing",
        ],
        cons=[
            "Parallel trends is untestable (only falsifiable in pre-period)",
            "Staggered rollout requires Callaway-Sant'Anna (standard DiD biased)",
            "Sensitive to composition changes",
        ],
        when_to_use="Use when you have panel data, a control group, and pre-period observations. Common for geo or team rollouts.",
    ),

    "Synthetic Control": CausalDesign(
        method="Synthetic Control Method",
        confidence="Medium",
        required_assumptions=[
            "Pre-period is long enough to fit a good synthetic control (usually 3x post-period)",
            "Donor pool units not affected by treatment",
            "Convex combination of donors can approximate treated unit",
            "No interference between treated and donor units",
        ],
        sensitivity_checks=[
            "In-space placebo: apply SC to each donor unit, compare RMSPE",
            "In-time placebo: apply SC to pre-period as if treatment happened earlier",
            "Leave-one-out: drop each donor and re-estimate",
            "RMSPE ratio: post/pre RMSPE (p-value analog)",
        ],
        model_spec=(
            "Minimise: ||X_1 - X_0·W||²_V\n"
            "subject to: W ≥ 0, Σw_j = 1\n\n"
            "where X_1 = treated pre-period outcomes\n"
            "      X_0 = donor matrix\n"
            "      W   = synthetic weights\n\n"
            "Treatment effect: α_t = Y_1t - Σ(w_j · Y_jt)"
        ),
        pros=[
            "Transparent weighting — shows which donors matter",
            "Good for single treated unit (N=1 case)",
            "Visualizable synthetic vs actual trajectory",
        ],
        cons=[
            "Requires long, high-quality pre-period",
            "No standard errors (uses permutation inference)",
            "Doesn't generalize when treated unit is outside convex hull of donors",
        ],
        when_to_use="Use when you have 1–5 treated units (markets, countries), a long pre-period, and many potential control units.",
    ),

    "Instrumental Variables": CausalDesign(
        method="Instrumental Variables (IV / 2SLS)",
        confidence="Medium",
        required_assumptions=[
            "Relevance: instrument Z strongly predicts treatment D (F > 10)",
            "Exclusion restriction: Z affects outcome Y only through D",
            "Independence: Z is as good as randomly assigned",
            "Monotonicity: no defiers (for LATE interpretation)",
        ],
        sensitivity_checks=[
            "First-stage F-statistic (must be > 10, ideally > 20)",
            "Overidentification test (Sargan-Hansen) if multiple instruments",
            "Sensitivity to exclusion restriction (Conley et al. local-to-zero)",
            "Compare OLS and IV estimates — large difference suggests endogeneity",
        ],
        model_spec=(
            "First stage:  D = α + π·Z + X·γ + u\n"
            "Second stage: Y = μ + β·D_hat + X·δ + ε\n\n"
            "LATE = E[Y(1)-Y(0) | Compliers]\n"
            "     = Cov(Y,Z) / Cov(D,Z)\n\n"
            "SE: Robust or clustered at the instrument level"
        ),
        pros=[
            "Handles endogeneity / selection into treatment",
            "Can recover LATE even with non-compliance",
        ],
        cons=[
            "Finding a valid instrument is hard",
            "LATE only generalizes to compliers (external validity concern)",
            "Weak instruments amplify bias",
        ],
        when_to_use="Use when treatment is endogenous and you have a valid natural experiment (e.g., lottery assignment, threshold, distance).",
    ),

    "Matching / Weighting": CausalDesign(
        method="Propensity Score Matching / IPW",
        confidence="Medium",
        required_assumptions=[
            "Conditional ignorability: Y(0),Y(1) ⊥ D | X",
            "Common support: 0 < P(D=1|X) < 1 for all units",
            "No unobserved confounders (strong assumption)",
            "Correct propensity model specification",
        ],
        sensitivity_checks=[
            "Covariate balance after matching (standardised mean differences < 0.1)",
            "Rosenbaum bounds sensitivity analysis (Γ-sensitivity)",
            "Overlap check: propensity score distribution plot",
            "Doubly-robust estimator (AIPW) as robustness check",
        ],
        model_spec=(
            "Propensity score: e(X) = P(D=1|X) via logistic regression\n\n"
            "IPW estimator:\n"
            "ATE = (1/N) Σ [D·Y/e(X) - (1-D)·Y/(1-e(X))]\n\n"
            "AIPW (doubly robust):\n"
            "ATE = (1/N) Σ [μ1(X) - μ0(X)\n"
            "           + D(Y-μ1(X))/e(X)\n"
            "           - (1-D)(Y-μ0(X))/(1-e(X))]"
        ),
        pros=[
            "Flexible — many matching algorithms available",
            "Interpretable: balance table shows comparability",
            "AIPW is doubly robust (one model can be misspecified)",
        ],
        cons=[
            "Requires conditional ignorability — untestable",
            "Sensitive to propensity model specification",
            "Cannot handle unobserved confounders",
        ],
        when_to_use="Use when you have rich observational pre-treatment covariates and no natural experiment.",
    ),
}


# ── Decision tree ─────────────────────────────────────────
def select_design(
    can_randomize: bool,
    has_spillover: bool,
    has_staggered_rollout: bool,
    has_panel_data: bool,
    has_strong_pre_period: bool,
    has_instrument: bool,
    n_treated_units: int,
) -> tuple[str, str]:
    """
    Decision tree returning (primary_method, secondary_method).
    """
    if can_randomize:
        if has_spillover:
            return "Difference-in-Differences", "Synthetic Control"
        return "A/B Test", "Difference-in-Differences"

    # Non-randomized
    if has_instrument:
        return "Instrumental Variables", "Matching / Weighting"

    if has_panel_data:
        if n_treated_units <= 5 and has_strong_pre_period:
            return "Synthetic Control", "Difference-in-Differences"
        if has_staggered_rollout:
            return "Difference-in-Differences", "Synthetic Control"
        return "Difference-in-Differences", "Matching / Weighting"

    return "Matching / Weighting", "Difference-in-Differences"


def get_design(name: str) -> CausalDesign:
    return DESIGNS.get(name, DESIGNS["Matching / Weighting"])
