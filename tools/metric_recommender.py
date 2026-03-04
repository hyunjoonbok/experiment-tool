"""
Tool 4: Feature → Metric Recommender Engine
Rule-based lookup mapping (feature_type, funnel_stage) → metric bundle.
"""

from dataclasses import dataclass, field


@dataclass
class MetricBundle:
    primary_metric: str
    primary_definition: str
    secondary_metrics: list[str]
    guardrail_metrics: list[str]
    leading_indicators: list[str]
    lagging_indicators: list[str]
    suggested_duration_days: int
    risk_metrics: list[str]
    notes: str = ""


# ─────────────────────────────────────────────────
# Rule-based lookup table
# Keys: (feature_type, funnel_stage)
# ─────────────────────────────────────────────────
METRIC_RULES: dict[tuple[str, str], MetricBundle] = {

    # ── ENGAGEMENT ──────────────────────────────────
    ("engagement", "activation"): MetricBundle(
        primary_metric="D7 Activated Users %",
        primary_definition="% of new users who perform the core action within 7 days",
        secondary_metrics=["Session length", "Feature click-through rate", "Onboarding completion rate"],
        guardrail_metrics=["Crash rate", "Load time p95", "Unsubscribe rate"],
        leading_indicators=["Tutorial completion", "First action time"],
        lagging_indicators=["30-day retention", "Lifetime value"],
        suggested_duration_days=14,
        risk_metrics=["Novelty effect inflation", "Selection bias in early adopters"],
    ),
    ("engagement", "retention"): MetricBundle(
        primary_metric="D30 Retention Rate",
        primary_definition="% of users active on day 30 after first use",
        secondary_metrics=["Weekly active rate", "Feature return rate", "Session frequency"],
        guardrail_metrics=["Support ticket rate", "Uninstall rate", "Notification opt-out"],
        leading_indicators=["D7 retention", "DAU/MAU ratio"],
        lagging_indicators=["6-month retention", "Churn rate"],
        suggested_duration_days=30,
        risk_metrics=["Novelty effect", "Cannibalization of adjacent features"],
    ),
    ("engagement", "awareness"): MetricBundle(
        primary_metric="Feature Discovery Rate",
        primary_definition="% of eligible users who see and interact with the feature at least once",
        secondary_metrics=["Impression-to-click rate", "Share / invite rate"],
        guardrail_metrics=["Bounce rate", "Scroll depth"],
        leading_indicators=["Feature exposure rate"],
        lagging_indicators=["Repeat usage rate"],
        suggested_duration_days=7,
        risk_metrics=["SRM from surface targeting", "Novelty effect"],
    ),

    # ── MONETIZATION ────────────────────────────────
    ("monetization", "revenue"): MetricBundle(
        primary_metric="Revenue per User (RPU)",
        primary_definition="Total revenue / number of active users in the period",
        secondary_metrics=["Conversion rate to paid", "Average order value", "Purchase frequency"],
        guardrail_metrics=["Refund rate", "Subscription churn", "Customer support escalations"],
        leading_indicators=["Add-to-cart rate", "Trial start rate"],
        lagging_indicators=["LTV", "Payback period"],
        suggested_duration_days=21,
        risk_metrics=["Heavy-tailed revenue distribution (use Mann-Whitney)", "Cannibalization of existing SKUs"],
    ),
    ("monetization", "acquisition"): MetricBundle(
        primary_metric="Paid Conversion Rate",
        primary_definition="% of free users who upgrade to a paid plan during experiment window",
        secondary_metrics=["Trial-to-paid rate", "Time-to-convert", "Promo redemption rate"],
        guardrail_metrics=["CAC", "Refund rate", "Free tier engagement"],
        leading_indicators=["Paywall impression rate", "Trial start rate"],
        lagging_indicators=["12-month LTV", "Resubscription rate"],
        suggested_duration_days=14,
        risk_metrics=["Novelty discount effect", "Simpson's paradox across plan types"],
    ),
    ("monetization", "retention"): MetricBundle(
        primary_metric="Subscription Renewal Rate",
        primary_definition="% of users whose subscription renews at the next billing cycle",
        secondary_metrics=["Days to cancellation", "Plan upgrade rate", "Winback rate"],
        guardrail_metrics=["Forced upgrade complaints", "Support ticket volume"],
        leading_indicators=["Feature usage frequency", "NPS trend"],
        lagging_indicators=["12-month retention", "Net revenue retention"],
        suggested_duration_days=30,
        risk_metrics=["Billing cycle misalignment", "Long novelty decay"],
    ),

    # ── AI USAGE ────────────────────────────────────
    ("ai_usage", "activation"): MetricBundle(
        primary_metric="AI Feature First-Use Rate",
        primary_definition="% of eligible users who invoke the AI feature at least once",
        secondary_metrics=["Prompts per session", "AI output acceptance rate", "Time-to-first-AI-use"],
        guardrail_metrics=["Hallucination complaint rate", "Session abandonment on AI error", "Latency p95"],
        leading_indicators=["Tooltip / onboarding click-through"],
        lagging_indicators=["Weekly AI usage rate", "AI-attributed retention"],
        suggested_duration_days=14,
        risk_metrics=["Novelty effect (AI features spike early)", "Metric gaming via prompt stuffing"],
    ),
    ("ai_usage", "retention"): MetricBundle(
        primary_metric="Weekly AI Engagement Rate",
        primary_definition="% of active users who use AI feature at least once per week",
        secondary_metrics=["AI interactions per session", "AI-to-manual task ratio", "Return rate after AI use"],
        guardrail_metrics=["Error rate", "Negative feedback rate", "Latency degradation"],
        leading_indicators=["D7 AI repeat rate"],
        lagging_indicators=["AI feature D60 retention", "AI-attributed revenue"],
        suggested_duration_days=28,
        risk_metrics=["Novelty decay plateau", "Engagement cannibalization from organic features"],
    ),
    ("ai_usage", "revenue"): MetricBundle(
        primary_metric="AI-Attributed Revenue per User",
        primary_definition="Incremental revenue attributable to AI feature usage (via holdout)",
        secondary_metrics=["Upgrade rate among AI users", "AI premium plan adoption"],
        guardrail_metrics=["AI cost per query", "Infrastructure cost per user"],
        leading_indicators=["AI task completion rate"],
        lagging_indicators=["AI-attributed LTV"],
        suggested_duration_days=21,
        risk_metrics=["Attribution complexity", "Cost guardrail breach"],
    ),

    # ── RETENTION ───────────────────────────────────
    ("retention", "retention"): MetricBundle(
        primary_metric="D30 Retention Rate",
        primary_definition="% of users returning on day 30",
        secondary_metrics=["D7 / D14 retention", "Reactivation rate", "Churn rate"],
        guardrail_metrics=["Notification opt-out rate", "App uninstall rate"],
        leading_indicators=["D3 retention", "L28 DAU/MAU"],
        lagging_indicators=["6-month retention", "LTV"],
        suggested_duration_days=30,
        risk_metrics=["Long novelty effect", "Cannibalization of notification channel"],
    ),
    ("retention", "activation"): MetricBundle(
        primary_metric="Onboarding Completion Rate",
        primary_definition="% of new users completing all onboarding steps",
        secondary_metrics=["Time-to-activate", "Step drop-off rate", "Day-1 return rate"],
        guardrail_metrics=["Onboarding abandonment", "Support request on step X"],
        leading_indicators=["Onboarding start rate"],
        lagging_indicators=["D30 retention", "Feature adoption depth"],
        suggested_duration_days=14,
        risk_metrics=["Selection bias (only new users)", "Novelty effect on completion"],
    ),

    # ── MIGRATION ───────────────────────────────────
    ("migration", "activation"): MetricBundle(
        primary_metric="Migration Completion Rate",
        primary_definition="% of eligible users who fully migrate to the new experience",
        secondary_metrics=["Time-to-migrate", "Rollback rate", "Error rate during migration"],
        guardrail_metrics=["Data integrity errors", "Support escalation rate", "Latency post-migration"],
        leading_indicators=["Migration start rate"],
        lagging_indicators=["Post-migration retention", "Post-migration engagement"],
        suggested_duration_days=14,
        risk_metrics=["SRM from eligibility filtering", "Novelty regression after migration"],
    ),
    ("migration", "retention"): MetricBundle(
        primary_metric="Post-Migration D30 Retention",
        primary_definition="% of migrated users still active 30 days after migration",
        secondary_metrics=["Rollback rate", "Feature parity satisfaction", "Session depth post-migration"],
        guardrail_metrics=["Bug report rate", "Data loss incidents"],
        leading_indicators=["Post-migration D7 retention"],
        lagging_indicators=["Post-migration LTV"],
        suggested_duration_days=30,
        risk_metrics=["Survivorship bias from successful migrators", "Long novelty effect"],
    ),

    # ── MARKETPLACE ─────────────────────────────────
    ("marketplace", "acquisition"): MetricBundle(
        primary_metric="Listing-to-Transaction Rate",
        primary_definition="% of item listings that result in at least one transaction",
        secondary_metrics=["New seller / buyer conversion", "GMV per new user", "Search-to-purchase rate"],
        guardrail_metrics=["Fraud rate", "Dispute rate", "Supply-demand balance"],
        leading_indicators=["Search click-through rate", "Listing view rate"],
        lagging_indicators=["Repeat purchase rate", "Seller LTV"],
        suggested_duration_days=14,
        risk_metrics=["Network effects bias", "Interference between buyer/seller arms"],
    ),
    ("marketplace", "revenue"): MetricBundle(
        primary_metric="Gross Merchandise Value (GMV) per User",
        primary_definition="Total transaction value / active users in the period",
        secondary_metrics=["Take rate", "Average order value", "Transactions per user"],
        guardrail_metrics=["Refund / dispute rate", "Seller defect rate"],
        leading_indicators=["Add-to-cart rate", "Bid rate"],
        lagging_indicators=["Annual GMV", "Seller retention rate"],
        suggested_duration_days=21,
        risk_metrics=["SUTVA violations (network interference)", "Heavy-tailed GMV distribution"],
    ),
    ("marketplace", "retention"): MetricBundle(
        primary_metric="Repeat Transaction Rate",
        primary_definition="% of buyers who transact more than once within 90 days",
        secondary_metrics=["Days between purchases", "Category expansion rate"],
        guardrail_metrics=["Fraud rate increase", "Seller churn"],
        leading_indicators=["Wishlist add rate", "Notification click rate"],
        lagging_indicators=["12-month buyer LTV", "Seller supply health"],
        suggested_duration_days=30,
        risk_metrics=["Interference via shared inventory", "Network spillover"],
    ),
}

# ─────────────────────────────────────────────────
# Fallback bundle for unmapped combinations
# ─────────────────────────────────────────────────
_DEFAULT_BUNDLE = MetricBundle(
    primary_metric="Feature Adoption Rate",
    primary_definition="% of eligible users who use the feature at least once",
    secondary_metrics=["Session engagement depth", "Return usage rate"],
    guardrail_metrics=["Error rate", "Latency p95", "Uninstall / opt-out rate"],
    leading_indicators=["Feature exposure rate"],
    lagging_indicators=["30-day retention"],
    suggested_duration_days=14,
    risk_metrics=["Novelty effect", "SRM from targeting"],
    notes="No exact rule match — using generic engagement defaults.",
)


def get_metric_bundle(feature_type: str, funnel_stage: str) -> MetricBundle:
    """
    Look up the metric bundle for a given (feature_type, funnel_stage) pair.
    Falls back to a generic bundle if no rule matches.
    """
    key = (feature_type.lower(), funnel_stage.lower())
    return METRIC_RULES.get(key, _DEFAULT_BUNDLE)


def list_feature_types() -> list[str]:
    return ["engagement", "monetization", "ai_usage", "retention", "migration", "marketplace"]


def list_funnel_stages() -> list[str]:
    return ["awareness", "acquisition", "activation", "retention", "revenue", "referral"]


def bundle_to_dict(bundle: MetricBundle) -> dict:
    """Convert MetricBundle to a plain dict for display."""
    return {
        "Primary Metric": bundle.primary_metric,
        "Definition": bundle.primary_definition,
        "Secondary Metrics": bundle.secondary_metrics,
        "Guardrail Metrics": bundle.guardrail_metrics,
        "Leading Indicators": bundle.leading_indicators,
        "Lagging Indicators": bundle.lagging_indicators,
        "Suggested Duration (days)": bundle.suggested_duration_days,
        "Risk Metrics": bundle.risk_metrics,
        "Notes": bundle.notes,
    }
