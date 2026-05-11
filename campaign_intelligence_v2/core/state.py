"""
core/state.py  -- v2
====================
AgentState for the REDESIGNED control-loop pipeline.

New fields vs v1:
  - data_quality_result   : gate RIGHT after fan-in (early validation)
  - data_retry_count      : how many times we re-fetched data
  - reasoning_trace       : running chain-of-thought from every agent
  - critic_output         : Critic agent challenges the Strategist
  - strategist_revised    : flag that strategy was revised after critique
  - confidence_gate_passed: True only when strategist score >= CONFIDENCE_THRESHOLD

Architecture:
  Planner -> [ContextResolver?] -> KPI+Trend (parallel)
  -> FanIn -> DataQualityGate -(fail/retry)-> [KPI+Trend again] (max 1)
                              -(pass)-------> Synthesizer
  -> Strategist -> Critic -> (low confidence?) -> Strategist again
  -> ReportWriter
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, Optional
from typing_extensions import TypedDict


# Sub-schemas

class ExecutionPlan(TypedDict):
    query_type: Literal[
        "budget_reallocation", "kpi_deep_dive", "trend_analysis",
        "cross_campaign_comparison", "segment_analysis", "ad_creative_analysis",
        "general_insight",
    ]
    campaigns_in_scope: list[str]
    segments_in_scope: list[str]
    requires_context_resolution: bool
    routing_reason: str


class KPIData(TypedDict):
    brand_uplift: list[dict]
    target_vs_actual: list[dict]
    budget_summary: list[dict]
    kpi_comparison: list[dict]
    fetch_errors: list[str]


class TrendData(TypedDict):
    diagnostics: list[dict]
    ad_recall: list[dict]
    trend_directions: list[dict]
    top_creatives: list[dict]
    anomalies: list[dict]
    fetch_errors: list[str]


class DataQualityResult(TypedDict):
    """Produced by the DataQualityGate node right after FanIn."""
    passed: bool
    issues: list[str]
    severity: Literal["PASS", "WARN", "FAIL"]
    should_retry: bool
    reasoning: str


class SynthesisOutput(TypedDict):
    narrative: str
    key_findings: list[str]
    top_campaign: str
    underperforming: list[str]
    anomalies_noted: list[str]
    reasoning: str              # synthesizer chain-of-thought


class StrategistOutput(TypedDict):
    ranked_campaigns: list[dict]
    recommendations: list[str]
    confidence_score: int       # 0-100
    reasoning: str


class CriticOutput(TypedDict):
    """Critic agent challenges the Strategist output."""
    approved: bool
    challenges: list[str]
    revised_recommendations: list[str]
    critique_reasoning: str


class FinalResponse(TypedDict):
    answer: str
    rich_text: str
    chart_data: list[dict]
    chart_type: str
    chart_title: str
    table_data: Optional[dict]
    recommendations: list[str]
    confidence_score: int
    agent_trace: list[str]
    reasoning_trace: list[str]
    error: Optional[str]


# AgentState

class AgentState(TypedDict):
    # Input
    raw_question: str
    thread_id: str

    # Context Resolver
    resolved_question: str
    rewrite_applied: bool

    # Planner
    execution_plan: Optional[ExecutionPlan]

    # Parallel analysts (fan-in via reducer)
    kpi_data_chunks:   Annotated[list[KPIData],   operator.add]
    trend_data_chunks: Annotated[list[TrendData],  operator.add]

    # Collapsed after fan-in
    kpi_data:   Optional[KPIData]
    trend_data: Optional[TrendData]

    # Data Quality Gate (right after fan-in)
    data_quality_result: Optional[DataQualityResult]
    data_retry_count:    int

    # Downstream agents
    synthesis:   Optional[SynthesisOutput]
    strategy:    Optional[StrategistOutput]

    # Critic loop
    critic_output:       Optional[CriticOutput]
    strategist_revised:  bool
    critic_attempt:      int

    # Confidence gate
    confidence_gate_passed: bool

    # Report Writer
    final_response: Optional[FinalResponse]

    # Observability
    reasoning_trace:      Annotated[list[str], operator.add]
    error_log:            Annotated[list[str], operator.add]
    node_execution_order: Annotated[list[str], operator.add]


def initial_state(question: str, thread_id: str) -> AgentState:
    return AgentState(
        raw_question=question,
        thread_id=thread_id,
        resolved_question=question,
        rewrite_applied=False,
        execution_plan=None,
        kpi_data_chunks=[],
        trend_data_chunks=[],
        kpi_data=None,
        trend_data=None,
        data_quality_result=None,
        data_retry_count=0,
        synthesis=None,
        strategy=None,
        critic_output=None,
        strategist_revised=False,
        critic_attempt=0,
        confidence_gate_passed=False,
        final_response=None,
        reasoning_trace=[],
        error_log=[],
        node_execution_order=[],
    )
