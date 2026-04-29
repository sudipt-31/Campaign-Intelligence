"""
tools.py
────────
LangChain @tool functions for the au_topline.db campaign database.
Every tool returns a JSON string so agents can reason over structured results.

Real campaigns in the DB
────────────────────────
CM49  Travel like Jennie          → Mass Consumers, XB Travelers, Gen Z, Gen ZY, Music Enthusiasts
CM50  ING | Tripadvisor           → XB Travelers, ING Cardholders
CM51  MasterCard Click To Pay     → Online Shoppers
CM52  Commbank - AFC Women's Cup  → Mass Consumers
"""
import json
from langchain_core.tools import tool
from data_loader import (
    get_data_summary,
    get_kpis_for_campaign,
    get_kpis_for_segment,
    get_uplift_per_campaign,
    get_uplift_by_metric_campaign,
    get_preference_comparison,
    get_top_uplift_rows,
    get_negative_uplift_rows,
    get_diagnostics_for_campaign,
    get_recall_trend,
    get_diagnostics_vs_norm,
    get_ad_recall_for_campaign,
    get_ad_recall_vs_norm,
)


def _j(obj) -> str:
    return json.dumps(obj, indent=2, default=str)


# ────────────────────────────────────────────────────────────────────────────
# 1. Dataset overview
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_dataset_overview() -> str:
    """
    Returns everything you need to understand the dataset before answering any question:
    campaign names, campaign codes, target groups per campaign, KPI metric names,
    diagnostic metric names, ad creative names, time period column names, and row counts.

    ALWAYS call this first if you are unsure what campaigns, segments, or metrics exist.
    Available campaigns: Travel like Jennie, ING | Tripadvisor,
                         MasterCard Click To Pay Campaign,
                         Commbank - AFC Women's Asian Cup Australia 2026
    """
    return _j(get_data_summary())


# ────────────────────────────────────────────────────────────────────────────
# 2. Marketing KPIs — per campaign
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_campaign_kpis(campaign_name: str) -> str:
    """
    Returns all marketing KPI rows for one campaign, broken down by target group.
    Columns returned: campaign_name, tg_name, metric, seen, not_seen, uplift, desired_uplift.

    'seen'    = score among people exposed to the ad
    'not_seen' = score among control (non-exposed) group
    'uplift'  = seen − not_seen  (positive = ad drove improvement)
    'desired_uplift' = the target lift set for that KPI

    Metrics available: Preference, Relevance, Brand Trust, Purchase Intent,
                       Brand Connection, International Payments, Exclusive Access, etc.

    Use for: "How did Travel like Jennie perform?", "Show ING KPIs",
             "MasterCard brand metrics", "Commbank uplift"
    Args:
        campaign_name: Partial name is fine. e.g. "Jennie", "ING", "MasterCard", "Commbank"
    """
    rows = get_kpis_for_campaign(campaign_name)
    if not rows:
        return (f"No KPI data found for '{campaign_name}'. "
                "Call get_dataset_overview to see valid campaign names.")
    return _j({"campaign": campaign_name, "total_rows": len(rows), "data": rows})


# ────────────────────────────────────────────────────────────────────────────
# 3. Marketing KPIs — per target segment
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_segment_kpis(segment_name: str) -> str:
    """
    Returns all marketing KPI rows for one target group / audience segment,
    across all campaigns that contain that segment.

    Available segments: Mass Consumers, XB Travelers, Gen Z, Gen ZY,
                        Music Enthusiasts, ING Cardholders, Online Shoppers

    Use for: "How did Gen Z respond?", "XB Travelers performance",
             "What are Mass Consumers metrics?", "ING Cardholders uplift"
    Args:
        segment_name: Partial match. e.g. "Gen Z", "XB", "Mass", "ING Card", "Music"
    """
    rows = get_kpis_for_segment(segment_name)
    if not rows:
        return (f"No data for segment '{segment_name}'. "
                "Call get_dataset_overview to see valid segment names.")
    return _j({"segment": segment_name, "total_rows": len(rows), "data": rows})


# ────────────────────────────────────────────────────────────────────────────
# 4. Uplift comparison — all campaigns
# ────────────────────────────────────────────────────────────────────────────
@tool
def compare_campaign_uplift() -> str:
    """
    Compares average brand uplift across all 4 campaigns.
    Aggregates every metric and segment for each campaign into a single avg_uplift score.
    Also returns avg_seen, avg_not_seen, and how many segments / metric rows contributed.

    Use for: "Which campaign had the best uplift?",
             "Rank campaigns by performance",
             "Which campaign is doing best overall?",
             "Compare all campaigns"
    """
    return _j({"comparison": "avg_uplift_per_campaign", "data": get_uplift_per_campaign()})


# ────────────────────────────────────────────────────────────────────────────
# 5. Uplift heatmap — campaign × metric
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_uplift_by_metric_and_campaign() -> str:
    """
    Returns uplift broken down by every campaign × metric combination.
    Great for understanding WHICH metric drove (or hurt) each campaign.

    Use for: "Which metric had the highest uplift?",
             "Where did brand trust improve most?",
             "Break down preference uplift per campaign",
             "Metric-level performance comparison"
    """
    return _j({
        "description": "avg_uplift per campaign × metric",
        "data": get_uplift_by_metric_campaign()
    })


# ────────────────────────────────────────────────────────────────────────────
# 6. Preference metric comparison
# ────────────────────────────────────────────────────────────────────────────
@tool
def compare_preference_scores() -> str:
    """
    Compares the 'Preference' KPI (preference_seen score and uplift)
    across all campaigns and their target groups, ranked best to worst.

    Use for: "Which campaign improved brand preference?",
             "Preference uplift by segment",
             "How does Gen Z preference compare to Mass Consumers?",
             "Best preference performance"
    """
    return _j({"metric": "Preference", "data": get_preference_comparison()})


# ────────────────────────────────────────────────────────────────────────────
# 7. Top uplift performers
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_top_uplift_performers(top_n: int = 10) -> str:
    """
    Returns the top N campaign × segment × metric rows ranked by uplift (highest first).
    Use to highlight wins, best moments, or strongest brand-lift results.

    Use for: "Top performing metrics", "Best uplift moments",
             "What are our biggest wins?", "Highlight top results"
    Args:
        top_n: How many rows to return (default 10, max sensible ~20)
    """
    return _j({"ranked_by": "uplift DESC", "top_n": top_n,
               "data": get_top_uplift_rows(top_n)})


# ────────────────────────────────────────────────────────────────────────────
# 8. Negative uplift — underperformers
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_underperforming_metrics() -> str:
    """
    Returns all campaign × segment × metric rows where uplift is NEGATIVE
    (meaning the ad actually hurt or underperformed versus the control group).
    Sorted worst first.

    Use for: "What is underperforming?", "Where is the brand losing ground?",
             "Why is a campaign struggling?", "Negative impact areas",
             "What should we fix?"
    """
    rows = get_negative_uplift_rows()
    if not rows:
        return "No negative uplift found — all measured metrics are positive across all campaigns."
    return _j({"description": "negative_uplift_rows_sorted_worst_first",
               "count": len(rows), "data": rows})


# ────────────────────────────────────────────────────────────────────────────
# 9. Campaign diagnostics (time-series)
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_campaign_diagnostics(campaign_name: str) -> str:
    """
    Returns diagnostic scores over time for a campaign. Each row has:
    norm (industry benchmark), dec_25, fn1_jan_26, jan_26, to_date.

    Diagnostic metrics include:
    Campaign Recall, Branded Recall, Ad Exposure, Branding score,
    Ease of Understanding, Key Message recall, Call to Action recall,
    Relevancy, Enjoyable/Appealing.

    Use for: "How did recall change over time?",
             "Is ad exposure above norm?",
             "Was the key message understood?",
             "Trend analysis for Travel like Jennie",
             "Diagnostic breakdown for ING"
    Args:
        campaign_name: Partial name. e.g. "Jennie", "ING", "MasterCard", "Commbank"
    """
    rows = get_diagnostics_for_campaign(campaign_name)
    if not rows:
        return f"No diagnostics found for '{campaign_name}'."
    return _j({"campaign": campaign_name, "row_count": len(rows),
               "time_columns": ["norm", "dec_25", "fn1_jan_26", "jan_26", "to_date"],
               "data": rows})


# ────────────────────────────────────────────────────────────────────────────
# 10. Campaign recall trend — all campaigns
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_recall_trend_all_campaigns() -> str:
    """
    Returns Campaign Recall scores across all time periods
    (norm, dec_25, fn1_jan_26, jan_26, to_date) for every campaign × segment.
    Best tool for time-series trend questions.

    Use for: "How has recall changed over time?",
             "Is recall improving or declining?",
             "Compare recall trend across campaigns",
             "Month-on-month recall performance"
    """
    return _j({
        "metric": "Campaign Recall",
        "time_columns": ["norm", "dec_25", "fn1_jan_26", "jan_26", "to_date"],
        "data": get_recall_trend()
    })


# ────────────────────────────────────────────────────────────────────────────
# 11. Diagnostics vs benchmark norm
# ────────────────────────────────────────────────────────────────────────────
@tool
def compare_diagnostics_vs_norm() -> str:
    """
    Compares to_date performance vs the norm (industry benchmark) for every
    diagnostic metric × campaign × segment.
    vs_norm = to_date − norm  (positive = above benchmark, negative = below)
    Sorted best to worst.

    Use for: "Are we beating benchmarks?",
             "Which campaigns are above norm?",
             "Norm comparison analysis",
             "Above / below industry average"
    """
    return _j({
        "description": "to_date vs norm benchmark — sorted best to worst",
        "data": get_diagnostics_vs_norm()
    })


# ────────────────────────────────────────────────────────────────────────────
# 12. Ad creative recall — per campaign
# ────────────────────────────────────────────────────────────────────────────
@tool
def get_ad_creative_recall(campaign_name: str) -> str:
    """
    Returns per-ad-creative recall rates over time for a specific campaign.
    Each row: ad_creative name, norm, dec_25, fn1_jan_26, jan_26, to_date.

    Ad creatives in the DB:
      Travel like Jennie → Ad 1 (30s), Ad 2 (6s)
      ING | Tripadvisor  → Ad 1/2/3 (Static)
      MasterCard         → Carousel1, Carousel2, Static, OOH
      Commbank           → Meta Ads, Womens Asia Cup 15s, Insta

    Use for: "Which ad was recalled most?",
             "Compare 30s vs 6s creative for Jennie",
             "MasterCard ad recall",
             "Which creative resonated best?"
    Args:
        campaign_name: Partial name. e.g. "Jennie", "ING", "MasterCard", "Commbank"
    """
    rows = get_ad_recall_for_campaign(campaign_name)
    if not rows:
        return f"No ad recall data for '{campaign_name}'."
    return _j({"campaign": campaign_name, "ad_count": len(rows), "data": rows})


# ────────────────────────────────────────────────────────────────────────────
# 13. Ad recall vs norm — all campaigns
# ────────────────────────────────────────────────────────────────────────────
@tool
def compare_all_ad_recall_vs_norm() -> str:
    """
    Compares ad recall (to_date) vs norm for EVERY ad creative across ALL campaigns.
    vs_norm = to_date − norm. Sorted best to worst.

    Use for: "Which ads beat the norm?",
             "Best performing creatives overall",
             "Ad recall benchmark comparison across all campaigns"
    """
    return _j({
        "description": "ad recall to_date vs norm — all campaigns, sorted best to worst",
        "data": get_ad_recall_vs_norm()
    })


# ── Tool registry ────────────────────────────────────────────────────────────
ALL_TOOLS = [
    get_dataset_overview,
    get_campaign_kpis,
    get_segment_kpis,
    compare_campaign_uplift,
    get_uplift_by_metric_and_campaign,
    compare_preference_scores,
    get_top_uplift_performers,
    get_underperforming_metrics,
    get_campaign_diagnostics,
    get_recall_trend_all_campaigns,
    compare_diagnostics_vs_norm,
    get_ad_creative_recall,
    compare_all_ad_recall_vs_norm,
]