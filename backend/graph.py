"""
graph.py — LangGraph state machine orchestrating the 4-agent pipeline.

Flow:
  supervisor_node → data_analyst_node → insight_node → report_writer_node → END

Each node reads from and writes to AgentState (TypedDict).
Chat history is threaded through every node for conversational memory.
"""
import json
import re
from typing import TypedDict, Annotated, Optional, Any

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage

from agents import (
    build_supervisor_agent,
    build_data_analyst_agent,
    build_insight_agent,
    build_report_writer_agent,
)


# ──────────────────────────────────────────────────
# Shared State
# ──────────────────────────────────────────────────
class AgentState(TypedDict):
    question:        str
    chat_history:    list[dict]   # [{"role": "user"|"assistant", "content": "..."}]
    routing:         Optional[dict]
    raw_data:        Optional[str]
    insights:        Optional[str]
    final_response:  Optional[dict]
    agent_trace:     list[str]
    error:           Optional[str]


# ──────────────────────────────────────────────────
# Helper: safe JSON extraction
# ──────────────────────────────────────────────────
def _extract_json(text: str) -> Optional[dict]:
    """Extract JSON from LLM response — handles markdown fences."""
    # Strip markdown fences
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(clean)
    except Exception:
        # Try extracting first JSON block
        match = re.search(r"\{.*\}", clean, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
    return None


def _build_history_context(chat_history: list[dict], max_turns: int = 6) -> str:
    """Format recent chat history as a readable context block."""
    if not chat_history:
        return ""
    recent = chat_history[-(max_turns * 2):]  # keep last N full turns
    lines = ["=== CONVERSATION HISTORY (for context) ==="]
    for msg in recent:
        role = msg.get("role", "user").upper()
        content = msg.get("content", "")
        # Truncate very long assistant responses
        if role == "ASSISTANT" and len(content) > 400:
            content = content[:400] + "…"
        lines.append(f"[{role}]: {content}")
    lines.append("=== END HISTORY ===")
    return "\n".join(lines)


# ──────────────────────────────────────────────────
# Node Implementations
# ──────────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """Classifies the question and produces a routing plan."""
    print("\n" + "═"*60)
    print(f" 🤖 [STEP 1: SUPERVISOR] Analyzing: {state['question']}")
    print("═"*60, flush=True)
    
    try:
        history_ctx = _build_history_context(state.get("chat_history", []))
        question_with_ctx = state["question"]
        if history_ctx:
            question_with_ctx = f"{history_ctx}\n\nCurrent question: {state['question']}"

        agent    = build_supervisor_agent()
        response = agent.invoke({"question": question_with_ctx})
        routing  = _extract_json(response.content)

        if not routing:
            routing = {
                "intent": "General campaign analysis",
                "requires_data": True,
                "requires_insight": True,
                "requires_chart": True,
                "requires_recommendations": True,
                "primary_table": "multiple",
                "primary_campaign": None,
                "primary_segment": None,
                "primary_metric": None,
                "routing_notes": "Default routing — call compare_campaign_uplift and get_dataset_overview",
            }

        print(f" ✅ [Supervisor] Routing decided:")
        print(f"    - Intent: {routing.get('intent')}")
        print(f"    - Requires Data: {routing.get('requires_data')}")
        print(f"    - Primary Table: {routing.get('primary_table')}")
        print(f"    - Notes: {routing.get('routing_notes')}")
        
        return {
            **state,
            "routing":     routing,
            "agent_trace": state.get("agent_trace", []) + ["supervisor"],
        }
    except Exception as e:
        print(f" ❌ [Supervisor] Error: {e}")
        return {**state, "error": f"Supervisor failed: {str(e)}"}


def data_analyst_node(state: AgentState) -> AgentState:
    """Calls data tools to fetch relevant campaign metrics."""
    print("\n" + "─"*60)
    print(" 📊 [STEP 2: DATA ANALYST] Fetching numbers...")
    print("─"*60, flush=True)

    if state.get("error"):
        return state

    routing = state.get("routing", {})
    if not routing.get("requires_data", True):
        print(" ⏭️ [DataAnalyst] Skipping data fetch (not required).")
        return {
            **state,
            "raw_data": "No data requested for this query.",
            "agent_trace": state.get("agent_trace", []) + ["data_analyst_skipped"],
        }

    metric   = routing.get("primary_metric")
    segment  = routing.get("primary_segment")
    campaign = routing.get("primary_campaign")
    table    = routing.get("primary_table")
    notes    = routing.get("routing_notes", "")

    # Build a targeted prompt based on routing + history context
    input_parts = [f"User question: {state['question']}"]
    input_parts.append(f"<<ROUTING: {notes}>>")
    if table:
        input_parts.append(f"Primary table: {table}")
    if metric:
        input_parts.append(f"Focus metric: {metric}")
    if segment:
        input_parts.append(f"Focus segment: {segment}")
    if campaign:
        input_parts.append(f"Focus campaign: {campaign}")

    # Inject history summary for follow-up awareness
    history_ctx = _build_history_context(state.get("chat_history", []), max_turns=3)
    if history_ctx:
        input_parts.insert(1, history_ctx)

    try:
        executor = build_data_analyst_agent()
        result   = executor.invoke({"input": "\n".join(input_parts)})
        raw_data = result.get("output", "No data returned")
        
        # Truncate raw data for terminal visibility
        data_preview = (raw_data[:300] + "...") if len(raw_data) > 300 else raw_data
        print(f" ✅ [DataAnalyst] Data retrieved (preview):\n{data_preview}\n", flush=True)
        
        return {
            **state,
            "raw_data":    raw_data,
            "agent_trace": state.get("agent_trace", []) + ["data_analyst"],
        }
    except Exception as e:
        print(f" ❌ [DataAnalyst] Error: {e}")
        return {**state, "error": f"Data Analyst failed: {str(e)}"}


def insight_node(state: AgentState) -> AgentState:
    """Analyses raw data and generates structured insights."""
    print("\n" + "─"*60)
    print(" 💡 [STEP 3: INSIGHT AGENT] Processing trends and anomalies...")
    print("─"*60, flush=True)

    if state.get("error"):
        return state

    routing = state.get("routing", {})
    if not routing.get("requires_insight", True):
        print(" ⏭️ [InsightAgent] Skipping insights (not required).")
        return {
            **state,
            "insights": "No specific insights required for this conversational query.",
            "agent_trace": state.get("agent_trace", []) + ["insight_agent_skipped"],
        }

    data = state.get("raw_data", "No data available")

    # Build history context for follow-up coherence
    history_ctx = _build_history_context(state.get("chat_history", []), max_turns=3)
    question_with_ctx = state["question"]
    if history_ctx:
        question_with_ctx = f"{history_ctx}\n\nCurrent question: {state['question']}"

    try:
        agent    = build_insight_agent()
        response = agent.invoke({
            "question": question_with_ctx,
            "data":     data,
        })
        insights = response.content
        
        # Try to parse and show key findings
        parsed_insights = _extract_json(insights)
        if parsed_insights:
            findings = parsed_insights.get("key_findings", [])
            print(f" ✅ [InsightAgent] Top Findings:")
            for f in findings[:3]:
                print(f"    - {f}")
        else:
            print(f" ✅ [InsightAgent] Insights generated (raw).")
            
        return {
            **state,
            "insights":    insights,
            "agent_trace": state.get("agent_trace", []) + ["insight_agent"],
        }
    except Exception as e:
        print(f" ❌ [InsightAgent] Error: {e}")
        return {**state, "error": f"Insight Agent failed: {str(e)}"}


def report_writer_node(state: AgentState) -> AgentState:
    """Produces the final user-facing JSON response."""
    print("\n" + "─"*60)
    print(" ✍️ [STEP 4: REPORT WRITER] Crafting final response...")
    print("─"*60, flush=True)

    if state.get("error"):
        return state

    insights = state.get("insights", "No insights available")

    # Pass history so report writer can reference prior answers
    history_ctx = _build_history_context(state.get("chat_history", []), max_turns=3)
    question_with_ctx = state["question"]
    if history_ctx:
        question_with_ctx = f"{history_ctx}\n\nCurrent question: {state['question']}"

    try:
        agent    = build_report_writer_agent()
        response = agent.invoke({
            "question": question_with_ctx,
            "insights": insights,
        })
        parsed = _extract_json(response.content)

        if not parsed:
            # Graceful fallback
            parsed = {
                "summary": "Analysis complete. Please see the data for details.",
                "rich_text": "## Analysis Complete\n\nThe pipeline ran successfully but could not parse the structured output. Please try rephrasing your question.",
                "chart": [{"name": "N/A", "value": 0}],
                "chart_type": "bar",
                "chart_title": "Campaign Analysis",
                "table_data": None,
                "recommendations": ["Review the raw data for more details."],
            }

        print(f" ✅ [ReportWriter] Response complete.")
        print(f"    - Summary: {parsed.get('summary')[:100]}...")
        print(f"    - Recommendations: {len(parsed.get('recommendations', []))} generated")
        print("═"*60 + "\n", flush=True)
        
        return {
            **state,
            "final_response": parsed,
            "agent_trace":    state.get("agent_trace", []) + ["report_writer"],
        }
    except Exception as e:
        print(f" ❌ [ReportWriter] Error: {e}")
        return {**state, "error": f"Report Writer failed: {str(e)}"}


# ──────────────────────────────────────────────────
# Conditional: skip data/insight if supervisor says no
# ──────────────────────────────────────────────────
def should_run_data_analyst(state: AgentState) -> str:
    if state.get("error"):
        return "error"
    routing = state.get("routing", {})
    return "data_analyst" if routing.get("requires_data", True) else "insight"


# ──────────────────────────────────────────────────
# Build Graph
# ──────────────────────────────────────────────────
def build_campaign_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("supervisor",    supervisor_node)
    graph.add_node("data_analyst",  data_analyst_node)
    graph.add_node("insight",       insight_node)
    graph.add_node("report_writer", report_writer_node)

    # Entry point
    graph.set_entry_point("supervisor")

    # Edges
    graph.add_conditional_edges(
        "supervisor",
        should_run_data_analyst,
        {
            "data_analyst": "data_analyst",
            "insight":      "insight",
            "error":        END,
        }
    )
    graph.add_edge("data_analyst",  "insight")
    graph.add_edge("insight",       "report_writer")
    graph.add_edge("report_writer", END)

    return graph.compile()


# Singleton — compiled once, reused
_graph_instance = None


def get_graph():
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = build_campaign_graph()
    return _graph_instance