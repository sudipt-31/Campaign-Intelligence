"""
service.py -- v2
Thin bridge between FastAPI and LangGraph pipeline.
New: exposes reasoning_trace, data_quality, critic_approved in response.
"""
from __future__ import annotations

import uuid
import traceback

from models import QueryResponse, TableData
from core.state import initial_state
from core.graph.builder import get_graph
from db.loader import get_all_campaigns, get_all_segments


def run_query(question: str, chat_history: list[dict] | None = None) -> QueryResponse:
    thread_id    = str(uuid.uuid4())
    chat_history = chat_history or []

    try:
        from core.graph import nodes as _nodes
        _nodes.LIVE_UPDATES.clear()
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"[Service] Question : {question[:120]}")
    print(f"[Service] Thread   : {thread_id}")
    print(f"[Service] History  : {len(chat_history)} turns")
    print(f"{'='*60}\n", flush=True)

    state = initial_state(question=question, thread_id=thread_id)
    state["chat_history"] = chat_history  # type: ignore[typeddict-unknown-key]

    try:
        graph  = get_graph()
        config = {"configurable": {"thread_id": thread_id}}
        result = graph.invoke(state, config=config)
        return _translate(result)
    except Exception as exc:
        traceback.print_exc()
        return QueryResponse(
            summary=f"Pipeline error: {exc}",
            error=str(exc),
            confidence_score=0,
            agent_trace=["ERROR"],
        )


def _translate(result: dict) -> QueryResponse:
    fr      = result.get("final_response") or {}
    critic  = result.get("critic_output") or {}
    dq      = result.get("data_quality_result") or {}

    table_data = None
    raw_table  = fr.get("table_data")
    if raw_table and raw_table.get("columns") and raw_table.get("rows"):
        table_data = TableData(
            columns=raw_table["columns"],
            rows=raw_table["rows"],
        )

    return QueryResponse(
        summary=fr.get("answer", "Analysis complete."),
        rich_text=fr.get("rich_text"),
        chart=fr.get("chart_data"),
        chart_type=fr.get("chart_type", "bar"),
        chart_title=fr.get("chart_title"),
        table_data=table_data,
        recommendations=fr.get("recommendations"),
        agent_trace=result.get("node_execution_order", []),
        reasoning_trace=fr.get("reasoning_trace", []),
        confidence_score=fr.get("confidence_score"),
        data_quality={
            "severity":     dq.get("severity", "PASS"),
            "issues":       dq.get("issues", []),
            "reasoning":    dq.get("reasoning", ""),
            "retry_count":  result.get("data_retry_count", 0),
        } if dq else None,
        critic_approved=critic.get("approved"),
        error=fr.get("error"),
    )


def get_health_info() -> dict:
    try:
        campaigns = get_all_campaigns()
        segments  = get_all_segments()
        return {
            "status":             "ok",
            "data_loaded":        True,
            "campaigns_count":    len(campaigns),
            "segments_available": [s["segment_name"] for s in segments],
        }
    except Exception as exc:
        return {
            "status":             "error",
            "data_loaded":        False,
            "campaigns_count":    0,
            "segments_available": [],
            "error":              str(exc),
        }
