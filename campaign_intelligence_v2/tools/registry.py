"""
tools/registry.py
=================
LangChain @tool definitions wrapping db/loader.py.
Each tool is a thin, typed wrapper — zero business logic here.

KPI_TOOLS   → bound to KPI Analyst agent
TREND_TOOLS → bound to Trend Analyst agent
ALL_TOOLS   → union, used by Synthesizer for follow-up queries
"""
from __future__ import annotations

from typing import Optional
from langchain_core.tools import tool

from db import loader


# ── KPI Tools ─────────────────────────────────────────────────────────────────

@tool
def get_brand_uplift_all() -> list[dict]:
    """Return brand KPI uplift (current minus baseline) for every campaign and KPI metric.
    Use this to compare which campaigns drove the most improvement."""
    return loader.get_brand_uplift_all_campaigns()


@tool
def get_kpis_for_campaign(campaign_code: str) -> list[dict]:
    """Return all KPI metrics (Brand Awareness, Purchase Intent, Brand Trust, Preference, NPS Score)
    for a single campaign across all time periods: Baseline, Week 4, Week 8, Week 12, Current.
    campaign_code must be one of: CA01, CA02, CA03, CA04, CA05, CA06."""
    return loader.get_kpis_for_campaign(campaign_code)


@tool
def get_kpi_comparison_table() -> list[dict]:
    """Return a pivot table with one row per campaign showing current KPI values side-by-side.
    Best for cross-campaign comparison questions."""
    return loader.get_kpi_comparison_all()


@tool
def get_target_vs_actual(campaign_code: Optional[str] = None) -> list[dict]:
    """Return whether each campaign hit its KPI targets (achieved=1) or missed (achieved=0).
    Pass campaign_code to filter to one campaign, or omit for all campaigns."""
    return loader.get_target_vs_actual(campaign_code)


@tool
def get_budget_summary() -> list[dict]:
    """Return budget allocation, spend, burn rate, and average ROI for all campaigns.
    Use for budget reallocation and ROI comparison questions."""
    return loader.get_budget_summary_all()


@tool
def get_budget_for_campaign(campaign_code: str) -> list[dict]:
    """Return channel-level budget breakdown (allocated, spent, burn %, ROI) for one campaign.
    campaign_code must be one of: CA01, CA02, CA03, CA04, CA05, CA06."""
    return loader.get_budget_for_campaign(campaign_code)


@tool
def get_top_roi_channels() -> list[dict]:
    """Return all channels ranked by average ROI score across all campaigns.
    Use to answer which channel performs best."""
    return loader.get_top_roi_channels()


@tool
def get_segment_performance(segment_name: str) -> list[dict]:
    """Return KPI performance for all campaigns targeting a specific audience segment.
    Segments: Gen Z, Millennials, Gen X Parents, Baby Boomers, Urban Professionals,
    Budget Conscious, Eco-Conscious, Sports & Fitness, Empty Nesters, Students."""
    return loader.get_segment_performance(segment_name)


# ── Trend Tools ───────────────────────────────────────────────────────────────

@tool
def get_diagnostics_for_campaign(campaign_code: str) -> list[dict]:
    """Return diagnostic metrics (Campaign Recall, Ad Exposure, Message Clarity, CTA Recall,
    Relevance, Enjoyment, Branded Recall) across all time periods for one campaign.
    campaign_code must be one of: CA01, CA02, CA03, CA04, CA05, CA06."""
    return loader.get_diagnostics_for_campaign(campaign_code)


@tool
def get_trend_directions() -> list[dict]:
    """Return whether each campaign is trending UP, DOWN, or FLAT based on recent diagnostic change.
    Use for week-over-week trend questions."""
    return loader.get_trend_direction_all()


@tool
def get_ad_recall_for_campaign(campaign_code: str) -> list[dict]:
    """Return ad creative recall scores across time periods for one campaign.
    campaign_code must be one of: CA01, CA02, CA03, CA04, CA05, CA06."""
    return loader.get_ad_recall_for_campaign(campaign_code)


@tool
def get_top_ad_recall_all() -> list[dict]:
    """Return the top-performing ad creatives ranked by current recall score, across all campaigns.
    Use to answer which ad creative had the best recall."""
    return loader.get_top_ad_recall_all()


@tool
def get_anomalies() -> list[dict]:
    """Return campaigns with high brand awareness but low purchase intent — a classic anomaly.
    Use to surface diagnostic red flags."""
    return loader.get_anomalies()


@tool
def get_campaign_info(campaign_code: str) -> dict:
    """Return campaign metadata: name, objective, product line, budget, dates.
    campaign_code must be one of: CA01, CA02, CA03, CA04, CA05, CA06."""
    result = loader.get_campaign_by_code(campaign_code)
    if not result:
        return {"error": f"Campaign {campaign_code} not found"}
    segments = loader.get_segments_for_campaign(campaign_code)
    result["target_segments"] = segments
    return result


# ── Tool sets bound to each agent ─────────────────────────────────────────────

KPI_TOOLS: list = [
    get_brand_uplift_all,
    get_kpis_for_campaign,
    get_kpi_comparison_table,
    get_target_vs_actual,
    get_budget_summary,
    get_budget_for_campaign,
    get_top_roi_channels,
    get_segment_performance,
    get_campaign_info,
]

TREND_TOOLS: list = [
    get_diagnostics_for_campaign,
    get_trend_directions,
    get_ad_recall_for_campaign,
    get_top_ad_recall_all,
    get_anomalies,
    get_campaign_info,
]

ALL_TOOLS: list = list({t.name: t for t in KPI_TOOLS + TREND_TOOLS}.values())
