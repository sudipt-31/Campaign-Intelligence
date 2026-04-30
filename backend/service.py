"""
service.py — thin layer between FastAPI and the LangGraph pipeline.
Supports conversational memory via chat_history.
"""
import traceback
from models import QueryResponse, TableData
from graph import get_graph
from data_loader import get_data_summary


def run_query(question: str, chat_history: list[dict] | None = None) -> QueryResponse:
    from langchain_core.callbacks import StdOutCallbackHandler
    import sys
    
    print("\n" + "🚀"*30)
    print(f" [PIPELINE START] User Question: {question}")
    print("🚀"*30 + "\n", flush=True)
    
    graph = get_graph()
    initial_state = {
        "question":       question,
        "chat_history":   chat_history or [],
        "routing":        None,
        "raw_data":       None,
        "insights":       None,
        "final_response": None,
        "agent_trace":    [],
        "error":          None,
    }
    try:
        # Pass the StdOutCallbackHandler to force verbose output to the terminal
        state = graph.invoke(
            initial_state,
            config={"callbacks": [StdOutCallbackHandler()]}
        )
        print(f"\n{'='*60}\n[Service] Pipeline Complete\n{'='*60}", flush=True)

        if state.get("error"):
            return QueryResponse(
                summary=f"Pipeline error: {state['error']}",
                agent_trace=state.get("agent_trace", []),
                error=state["error"],
            )

        r = state.get("final_response", {})

        # Parse table_data if present
        table_data = None
        raw_td = r.get("table_data")
        if raw_td and isinstance(raw_td, dict):
            try:
                table_data = TableData(
                    columns=raw_td.get("columns", []),
                    rows=raw_td.get("rows", []),
                )
            except Exception:
                table_data = None

        return QueryResponse(
            summary         = r.get("summary", "Analysis complete."),
            rich_text       = r.get("rich_text"),
            chart           = r.get("chart"),
            chart_type      = r.get("chart_type", "bar"),
            chart_title     = r.get("chart_title"),
            table_data      = table_data,
            recommendations = r.get("recommendations"),
            agent_trace     = state.get("agent_trace", []),
        )
    except Exception as exc:
        traceback.print_exc()
        return QueryResponse(
            summary="Unexpected error — please try again.",
            error=str(exc),
        )


def get_health_info() -> dict:
    try:
        s = get_data_summary()
        return {
            "status":             "ok",
            "data_loaded":        True,
            "campaigns_count":    s["total_campaigns"],
            "segments_available": s["segments"],
        }
    except Exception as exc:
        return {
            "status":             "error",
            "data_loaded":        False,
            "campaigns_count":    0,
            "segments_available": [],
            "error":              str(exc),
        }