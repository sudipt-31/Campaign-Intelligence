"""
core/graph/nodes.py -- v2
==========================
All LangGraph node functions for the REDESIGNED control-loop pipeline.

NEW nodes vs v1:
  - node_data_quality_gate : early data validation right after fan-in
  - node_critic            : challenges the Strategist (intelligence layer)

CHANGED nodes vs v1:
  - node_synthesizer   : now emits reasoning_trace entry
  - node_strategist    : accepts critic feedback + confidence_note
  - node_report_writer : uses critic-approved recs, emits reasoning_trace

ARCHITECTURE:
  Planner -> [ContextResolver?] -> KPI+Trend (parallel)
  -> FanIn -> DataQualityGate -(FAIL+retry<1)-> [KPI+Trend]
                              -(PASS/WARN/exhaust)-> Synthesizer
  -> Strategist -> Critic -(not approved, attempt<1)-> Strategist
                          -(approved or exhausted)-> ReportWriter
"""
from __future__ import annotations

import json
import re
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import (
    LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS,
    CONFIDENCE_THRESHOLD, MAX_DATA_RETRIES, MAX_CRITIC_ATTEMPTS,
)
from core.state import (
    AgentState, ExecutionPlan, KPIData, TrendData,
    DataQualityResult,
)
from prompts.agent_prompts import CONTEXT_RESOLVER_PROMPT, VALIDATION_PROMPT

from agents.planner       import run_planner
from agents.kpi_analyst   import run_kpi_analyst
from agents.trend_analyst import run_trend_analyst
from agents.synthesizer   import run_synthesizer
from agents.strategist    import run_strategist
from agents.report_writer import run_report_writer
from agents.critic        import run_critic

# Live update list for SSE streaming
LIVE_UPDATES: list[str] = []


def _emit(node: str, msg: str) -> None:
    line = f"[{node.upper()}] {msg}"
    print(line, flush=True)
    LIVE_UPDATES.append(line)


def _reason(node: str, thought: str) -> list[str]:
    """Return a reasoning_trace entry."""
    return [f"[{node}] {thought}"]


# Node 1: Planner

def node_planner(state: AgentState) -> dict:
    _emit("PLANNER", "Classifying question and building execution plan...")
    question = state["resolved_question"] or state["raw_question"]
    try:
        plan = run_planner(question)
        reasoning = (
            f"Query classified as '{plan['query_type']}'. "
            f"Campaigns in scope: {plan['campaigns_in_scope']}. "
            f"Routing reason: {plan['routing_reason']}. "
            f"Context resolution needed: {plan['requires_context_resolution']}."
        )
        _emit("PLANNER", f"Query type: {plan['query_type']} | Campaigns: {plan['campaigns_in_scope']}")
        return {
            "execution_plan": plan,
            "node_execution_order": ["PLANNER"],
            "reasoning_trace": _reason("PLANNER", reasoning),
        }
    except Exception as exc:
        _emit("PLANNER", f"Error: {exc} -- using default plan")
        return {
            "execution_plan": ExecutionPlan(
                query_type="general_insight",
                campaigns_in_scope=["CA01","CA02","CA03","CA04","CA05","CA06"],
                segments_in_scope=[],
                requires_context_resolution=False,
                routing_reason=f"Fallback: {exc}",
            ),
            "node_execution_order": ["PLANNER"],
            "reasoning_trace": _reason("PLANNER", f"Planning failed ({exc}), using general_insight fallback."),
            "error_log": [f"Planner error: {exc}"],
        }


# Node 2: Context Resolver

def node_context_resolver(state: AgentState) -> dict:
    _emit("CONTEXT_RESOLVER", "Resolving follow-up context...")
    chat_history = state.get("chat_history", [])  # type: ignore
    question = state["raw_question"]
    try:
        history_str = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in (chat_history or [])[-6:]
        )
        llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=256)
        resp = llm.invoke([
            SystemMessage(content=CONTEXT_RESOLVER_PROMPT),
            HumanMessage(content=f"Conversation history:\n{history_str}\n\nCurrent question: {question}"),
        ])
        resolved = resp.content.strip()
        rewritten = resolved != question
        reasoning = (
            f"Rewrite applied: {rewritten}. "
            f"Original: '{question[:80]}'. "
            + (f"Resolved to: '{resolved[:80]}'." if rewritten else "No change needed.")
        )
        _emit("CONTEXT_RESOLVER", f"Rewrite applied: {rewritten}")
        return {
            "resolved_question": resolved,
            "rewrite_applied": rewritten,
            "node_execution_order": ["CONTEXT_RESOLVER"],
            "reasoning_trace": _reason("CONTEXT_RESOLVER", reasoning),
        }
    except Exception as exc:
        return {
            "resolved_question": question,
            "rewrite_applied": False,
            "node_execution_order": ["CONTEXT_RESOLVER"],
            "reasoning_trace": _reason("CONTEXT_RESOLVER", f"Error: {exc}. Kept original question."),
            "error_log": [f"Context resolver error: {exc}"],
        }


# Node 3: KPI Analyst (parallel)

def node_kpi_analyst(state: AgentState) -> dict:
    _emit("KPI_ANALYST", "Fetching KPI, budget and segment data via LangChain tools...")
    question = state.get("resolved_question") or state["raw_question"]
    try:
        kpi_data = run_kpi_analyst(question)
        n_uplift = len(kpi_data.get("brand_uplift", []))
        n_budget = len(kpi_data.get("budget_summary", []))
        n_errors = len(kpi_data.get("fetch_errors", []))
        reasoning = (
            f"Fetched {n_uplift} uplift rows, {n_budget} budget rows. "
            f"Fetch errors: {n_errors}. "
            f"kpi_comparison rows: {len(kpi_data.get('kpi_comparison', []))}."
        )
        _emit("KPI_ANALYST", reasoning)
        return {
            "kpi_data_chunks": [kpi_data],
            "node_execution_order": ["KPI_ANALYST"],
            "reasoning_trace": _reason("KPI_ANALYST", reasoning),
        }
    except Exception as exc:
        _emit("KPI_ANALYST", f"Error: {exc}")
        empty = KPIData(brand_uplift=[], target_vs_actual=[], budget_summary=[], kpi_comparison=[], fetch_errors=[str(exc)])
        return {
            "kpi_data_chunks": [empty],
            "node_execution_order": ["KPI_ANALYST"],
            "reasoning_trace": _reason("KPI_ANALYST", f"Failed: {exc}. Returning empty data."),
            "error_log": [f"KPI Analyst error: {exc}"],
        }


# Node 4: Trend Analyst (parallel)

def node_trend_analyst(state: AgentState) -> dict:
    _emit("TREND_ANALYST", "Fetching trend, diagnostic and ad recall data via LangChain tools...")
    question = state.get("resolved_question") or state["raw_question"]
    try:
        trend_data = run_trend_analyst(question)
        n_diag = len(trend_data.get("diagnostics", []))
        n_dirs = len(trend_data.get("trend_directions", []))
        n_errors = len(trend_data.get("fetch_errors", []))
        reasoning = (
            f"Fetched {n_diag} diagnostic rows, {n_dirs} trend directions. "
            f"Top creatives: {len(trend_data.get('top_creatives', []))}. "
            f"Anomalies: {len(trend_data.get('anomalies', []))}. "
            f"Fetch errors: {n_errors}."
        )
        _emit("TREND_ANALYST", reasoning)
        return {
            "trend_data_chunks": [trend_data],
            "node_execution_order": ["TREND_ANALYST"],
            "reasoning_trace": _reason("TREND_ANALYST", reasoning),
        }
    except Exception as exc:
        _emit("TREND_ANALYST", f"Error: {exc}")
        empty = TrendData(diagnostics=[], ad_recall=[], trend_directions=[], top_creatives=[], anomalies=[], fetch_errors=[str(exc)])
        return {
            "trend_data_chunks": [empty],
            "node_execution_order": ["TREND_ANALYST"],
            "reasoning_trace": _reason("TREND_ANALYST", f"Failed: {exc}. Returning empty data."),
            "error_log": [f"Trend Analyst error: {exc}"],
        }


# Node 5: Fan-in Merge (zero LLM)

def node_fan_in(state: AgentState) -> dict:
    """Pure Python — no LLM. Collapses parallel analyst chunks into single objects."""
    _emit("FAN_IN", "Merging parallel analyst outputs...")

    kpi_chunks = state.get("kpi_data_chunks", [])
    merged_kpi = KPIData(brand_uplift=[], target_vs_actual=[], budget_summary=[], kpi_comparison=[], fetch_errors=[])
    for chunk in kpi_chunks:
        for key in ("brand_uplift", "target_vs_actual", "budget_summary", "kpi_comparison", "fetch_errors"):
            merged_kpi[key].extend(chunk.get(key, []))  # type: ignore

    trend_chunks = state.get("trend_data_chunks", [])
    merged_trend = TrendData(diagnostics=[], ad_recall=[], trend_directions=[], top_creatives=[], anomalies=[], fetch_errors=[])
    for chunk in trend_chunks:
        for key in ("diagnostics", "ad_recall", "trend_directions", "top_creatives", "anomalies", "fetch_errors"):
            merged_trend[key].extend(chunk.get(key, []))  # type: ignore

    n_kpi  = len(merged_kpi["brand_uplift"])
    n_tdir = len(merged_trend["trend_directions"])
    reasoning = (
        f"Merged {len(kpi_chunks)} KPI chunk(s) and {len(trend_chunks)} trend chunk(s). "
        f"Total KPI uplift rows: {n_kpi}. Total trend directions: {n_tdir}."
    )
    _emit("FAN_IN", f"KPI rows: {n_kpi} | Trend directions: {n_tdir}")
    return {
        "kpi_data": merged_kpi,
        "trend_data": merged_trend,
        "node_execution_order": ["FAN_IN"],
        "reasoning_trace": _reason("FAN_IN", reasoning),
    }


# Node 6: Data Quality Gate (NEW -- right after fan-in)
# This is the EARLY VALIDATION that was missing in v1.

def node_data_quality_gate(state: AgentState) -> dict:
    """
    Pure Python check (no LLM) on merged data.
    If data is too sparse and we haven't retried yet -> signal retry.
    This is the control loop that v1 was missing.
    """
    _emit("DATA_QUALITY_GATE", "Checking data quality before analysis begins...")

    kpi   = state.get("kpi_data") or {}
    trend = state.get("trend_data") or {}
    retry = state.get("data_retry_count", 0)

    # Determine what type of query this is to calibrate expectations
    plan = state.get("execution_plan") or {}
    query_type = plan.get("query_type", "general_insight")
    trend_queries = {"trend_analysis", "ad_creative_analysis"}
    kpi_queries   = {"budget_reallocation", "kpi_deep_dive", "cross_campaign_comparison",
                     "segment_analysis", "general_insight"}
    kpi_required  = query_type in kpi_queries

    issues = []

    # Check KPI data — only critical for KPI-type queries
    kpi_empty = len(kpi.get("brand_uplift", [])) == 0 and len(kpi.get("kpi_comparison", [])) == 0
    if kpi_empty and kpi_required:
        issues.append("KPI data is completely empty (no uplift or comparison rows)")
    if len(kpi.get("fetch_errors", [])) > 2:
        issues.append(f"KPI analyst had {len(kpi['fetch_errors'])} fetch errors")

    # Check Trend data — always required (at minimum trend_directions)
    if len(trend.get("trend_directions", [])) == 0:
        issues.append("Trend directions are empty (no campaign trend data)")
    if len(trend.get("fetch_errors", [])) > 2:
        issues.append(f"Trend analyst had {len(trend['fetch_errors'])} fetch errors")

    # Only retry for issues that are truly critical AND kpi-type queries need them
    critical_issues = [i for i in issues if "completely empty" in i]
    has_critical = len(critical_issues) > 0

    if not issues:
        severity = "PASS"
        passed = True
        should_retry = False
        reasoning = (
            f"Data quality check PASSED. "
            f"KPI rows: {len(kpi.get('brand_uplift', []))}, "
            f"budget rows: {len(kpi.get('budget_summary', []))}, "
            f"trend directions: {len(trend.get('trend_directions', []))}. "
            f"Proceeding to Synthesizer."
        )
    elif has_critical and retry < MAX_DATA_RETRIES:
        severity = "FAIL"
        passed = False
        should_retry = True
        reasoning = (
            f"CRITICAL data gap detected (retry {retry+1}/{MAX_DATA_RETRIES}): {'; '.join(critical_issues)}. "
            f"Will re-dispatch KPI and Trend analysts with same question."
        )
    else:
        # Non-critical issues or retry exhausted — continue with warning
        severity = "WARN" if issues else "PASS"
        passed = True
        should_retry = False
        reasoning = (
            f"Data quality: {severity}. Issues noted: {'; '.join(issues) if issues else 'none'}. "
            f"{'Retry limit reached — proceeding with partial data.' if retry >= MAX_DATA_RETRIES else 'Non-critical — proceeding.'}"
        )

    result = DataQualityResult(
        passed=passed,
        issues=issues,
        severity=severity,
        should_retry=should_retry,
        reasoning=reasoning,
    )

    _emit("DATA_QUALITY_GATE", f"{severity} | Issues: {len(issues)} | Retry: {should_retry}")
    return {
        "data_quality_result": result,
        "data_retry_count": retry + (1 if should_retry else 0),
        "node_execution_order": ["DATA_QUALITY_GATE"],
        "reasoning_trace": _reason("DATA_QUALITY_GATE", reasoning),
        # Reset chunks AND previously merged data so fan-in starts clean on retry.
        # Without this, Annotated[list, operator.add] doubles the old data.
        **({"kpi_data_chunks": [], "trend_data_chunks": [], "kpi_data": None, "trend_data": None} if should_retry else {}),
    }


# Node 7: Synthesizer

def node_synthesizer(state: AgentState) -> dict:
    _emit("SYNTHESIZER", "Synthesising findings from KPI + Trend data...")
    question   = state.get("resolved_question") or state["raw_question"]
    kpi_data   = state.get("kpi_data") or KPIData(brand_uplift=[], target_vs_actual=[], budget_summary=[], kpi_comparison=[], fetch_errors=[])
    trend_data = state.get("trend_data") or TrendData(diagnostics=[], ad_recall=[], trend_directions=[], top_creatives=[], anomalies=[], fetch_errors=[])
    try:
        synthesis = run_synthesizer(question, kpi_data, trend_data)
        reasoning = synthesis.get("reasoning", "No reasoning provided by synthesizer.")
        _emit("SYNTHESIZER", f"Top campaign: {synthesis.get('top_campaign', 'N/A')} | Findings: {len(synthesis.get('key_findings', []))}")
        return {
            "synthesis": synthesis,
            "node_execution_order": ["SYNTHESIZER"],
            "reasoning_trace": _reason("SYNTHESIZER", reasoning),
        }
    except Exception as exc:
        _emit("SYNTHESIZER", f"Error: {exc}")
        return {
            "synthesis": None,
            "node_execution_order": ["SYNTHESIZER"],
            "reasoning_trace": _reason("SYNTHESIZER", f"Synthesis failed: {exc}."),
            "error_log": [f"Synthesizer error: {exc}"],
        }


# Node 8: Strategist

def node_strategist(state: AgentState) -> dict:
    critic    = state.get("critic_output")
    revised   = state.get("strategist_revised", False)
    attempt_n = state.get("critic_attempt", 0)

    label = "STRATEGIST"
    if revised:
        _emit(label, f"Revising strategy based on Critic feedback (attempt {attempt_n+1})...")
    else:
        _emit(label, "Building strategic recommendations with chain-of-thought reasoning...")

    question   = state.get("resolved_question") or state["raw_question"]
    synthesis  = state.get("synthesis")
    kpi_data   = state.get("kpi_data") or KPIData(brand_uplift=[], target_vs_actual=[], budget_summary=[], kpi_comparison=[], fetch_errors=[])
    trend_data = state.get("trend_data") or TrendData(diagnostics=[], ad_recall=[], trend_directions=[], top_creatives=[], anomalies=[], fetch_errors=[])

    # Build critique block from Critic output
    critique_block = ""
    if critic and not critic.get("approved", True) and critic.get("challenges"):
        challenges_str = "\n".join(f"  - {c}" for c in critic["challenges"])
        critique_block = (
            f"\nCRITIC CHALLENGES (you MUST address each one in your reasoning):\n"
            f"{challenges_str}\n"
        )

    # Confidence note if previous attempt scored too low
    prev_strategy = state.get("strategy")
    confidence_note = ""
    if prev_strategy:
        prev_score = prev_strategy.get("confidence_score", 100)
        if prev_score < CONFIDENCE_THRESHOLD:
            confidence_note = (
                f"\nNOTE: Your previous confidence_score was {prev_score}, "
                f"below the required threshold of {CONFIDENCE_THRESHOLD}. "
                f"Be more specific and data-driven to improve it — or honestly explain why it should remain low."
            )

    try:
        strategy = run_strategist(question, synthesis or {}, kpi_data, trend_data,
                                   critique_block if critique_block else None,
                                   confidence_note if confidence_note else None)
        reasoning = strategy.get("reasoning", "No reasoning provided.")
        _emit(label, f"Confidence: {strategy['confidence_score']} | Ranked: {len(strategy['ranked_campaigns'])}")
        return {
            "strategy": strategy,
            "node_execution_order": [label],
            "reasoning_trace": _reason(label, reasoning),
        }
    except Exception as exc:
        _emit(label, f"Error: {exc}")
        return {
            "strategy": None,
            "node_execution_order": [label],
            "reasoning_trace": _reason(label, f"Strategist failed: {exc}."),
            "error_log": [f"Strategist error: {exc}"],
        }


# Node 9: Critic (NEW)

def node_critic(state: AgentState) -> dict:
    """
    Challenges the Strategist output.
    This is the intelligence layer missing from v1 — strategy is no longer accepted blindly.
    """
    _emit("CRITIC", "Challenging strategy output — checking specificity, reasoning, confidence...")
    question  = state.get("resolved_question") or state["raw_question"]
    synthesis = state.get("synthesis")
    strategy  = state.get("strategy")
    attempt   = state.get("critic_attempt", 0)

    if not strategy:
        # Nothing to critique
        from core.state import CriticOutput
        result = CriticOutput(
            approved=True,
            challenges=[],
            revised_recommendations=[],
            critique_reasoning="No strategy to critique — auto-approved.",
        )
        return {
            "critic_output": result,
            "critic_attempt": attempt + 1,
            "node_execution_order": ["CRITIC"],
            "reasoning_trace": _reason("CRITIC", "No strategy available — auto-approved."),
        }

    try:
        critic_out = run_critic(question, synthesis or {}, strategy)
        approved   = critic_out.get("approved", True)
        challenges = critic_out.get("challenges", [])
        reasoning  = critic_out.get("critique_reasoning", "")

        _emit("CRITIC", f"Approved: {approved} | Challenges: {len(challenges)}")
        return {
            "critic_output": critic_out,
            "critic_attempt": attempt + 1,
            "strategist_revised": not approved,  # if not approved, strategist will re-run
            "node_execution_order": ["CRITIC"],
            "reasoning_trace": _reason("CRITIC", reasoning),
        }
    except Exception as exc:
        _emit("CRITIC", f"Error: {exc} -- auto-approving")
        from core.state import CriticOutput
        result = CriticOutput(
            approved=True,
            challenges=[],
            revised_recommendations=[],
            critique_reasoning=f"Critic error: {exc} — auto-approved.",
        )
        return {
            "critic_output": result,
            "critic_attempt": attempt + 1,
            "node_execution_order": ["CRITIC"],
            "reasoning_trace": _reason("CRITIC", f"Critic failed ({exc}) — auto-approved."),
            "error_log": [f"Critic error: {exc}"],
        }


# Node 10: Report Writer

def node_report_writer(state: AgentState) -> dict:
    _emit("REPORT_WRITER", "Writing final polished response...")
    question   = state.get("resolved_question") or state["raw_question"]
    synthesis  = state.get("synthesis")
    strategy   = state.get("strategy")
    critic     = state.get("critic_output")
    kpi_data   = state.get("kpi_data")
    trend_data = state.get("trend_data")
    trace      = state.get("node_execution_order", [])
    errors     = state.get("error_log", [])
    reasoning  = state.get("reasoning_trace", [])

    # Merge critic-approved recs into strategy before writing
    if critic and critic.get("approved") is False and critic.get("revised_recommendations"):
        if strategy:
            strategy = dict(strategy)
            strategy["recommendations"] = critic["revised_recommendations"]

    final = run_report_writer(question, synthesis, strategy, kpi_data, trend_data, trace, errors)
    # Attach full reasoning trace to the final response
    final["reasoning_trace"] = reasoning + _reason("REPORT_WRITER", "Report assembled from all agent outputs.")

    _emit("REPORT_WRITER", f"Done. Confidence: {final['confidence_score']}")
    return {
        "final_response": final,
        "node_execution_order": ["REPORT_WRITER"],
    }


# Node 11: Validation (kept for compatibility, not in main loop)

def node_validation(state: AgentState) -> dict:
    """Legacy node — kept for graph compat. No-op in v2 main loop."""
    return {"node_execution_order": ["VALIDATION"]}