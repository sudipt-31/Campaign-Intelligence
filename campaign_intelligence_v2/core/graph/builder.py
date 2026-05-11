"""
core/graph/builder.py -- v2
============================
LangGraph StateGraph -- the REDESIGNED campaign intelligence pipeline.

ARCHITECTURE:
------------------------------------------------------------------------
                     +-------------+
                     |   PLANNER   |  <- Entry point
                     +------+------+
                            | conditional
                +-----------+-----------+
                v                       v
       +----------------+    +---------------------------+
       |CONTEXT_RESOLVER|    | (skip -> direct fan-out)  |
       +--------+-------+    +----------+----------------+
                +-------------------------+
                      | Send() PARALLEL FAN-OUT
                 +----+----+
                 v         v
         +----------+ +-----------+
         |KPI_ANALYST| |TREND_ANALY|  <- Parallel via Send()
         +-----+----+ +-----+-----+
               +----------+
                    v  Annotated reducer merges state
           +-----------------+
           |     FAN_IN      |  <- Zero-LLM merge
           +-----------------+
                    v
           +-----------------+
           | DATA_QUALITY_   |  <- NEW: Early gate (pure Python)
           |     GATE        |
           +-----------------+
               |           |
        (FAIL+retry<1)   (PASS/WARN)
               |           v
     [KPI+TREND again]  +-------------+
                        | SYNTHESIZER |
                        +------+------+
                               v
                        +-------------+
                        |  STRATEGIST |  <- chain-of-thought reasoning
                        +------+------+
                               v
                        +-------------+
                        |   CRITIC    |  <- NEW: intelligence layer
                        +------+------+
                 (not approved + attempt<1)  |  (approved)
                               |              v
                    [STRATEGIST again]  +---------------+
                                        | REPORT_WRITER |
                                        +---------------+
------------------------------------------------------------------------

LangGraph features demonstrated:
  1. StateGraph(AgentState) -- typed state machine
  2. Send() -- parallel fan-out to KPI + Trend analysts
  3. Annotated[list, operator.add] -- fan-in reducer
  4. Conditional edges -- 3 branch points
  5. Back-edge retry loop -- DataQualityGate -> analysts (data retry)
  6. Back-edge critique loop -- Critic -> Strategist
  7. MemorySaver -- multi-turn conversation memory
  8. Zero-LLM nodes -- FAN_IN, DATA_QUALITY_GATE
"""
from __future__ import annotations

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import Send

from core.state import AgentState
from core.config import MAX_DATA_RETRIES, MAX_CRITIC_ATTEMPTS, CONFIDENCE_THRESHOLD
from core.graph.nodes import (
    node_planner,
    node_context_resolver,
    node_kpi_analyst,
    node_trend_analyst,
    node_fan_in,
    node_data_quality_gate,
    node_synthesizer,
    node_strategist,
    node_critic,
    node_report_writer,
)

# Node name constants
NODE_PLANNER            = "planner"
NODE_CONTEXT_RESOLVER   = "context_resolver"
NODE_KPI_ANALYST        = "kpi_analyst"
NODE_TREND_ANALYST      = "trend_analyst"
NODE_FAN_IN             = "fan_in"
NODE_DATA_QUALITY_GATE  = "data_quality_gate"
NODE_SYNTHESIZER        = "synthesizer"
NODE_STRATEGIST         = "strategist"
NODE_CRITIC             = "critic"
NODE_REPORT_WRITER      = "report_writer"

_graph = None


# Conditional edge functions

def _route_after_planner(state: AgentState):
    """
    Planner -> Context Resolver (follow-up questions)
            OR parallel [KPI_ANALYST + TREND_ANALYST] (direct fan-out).
    Uses LangGraph Send() to launch both analysts concurrently.
    """
    plan = state.get("execution_plan") or {}
    if plan.get("requires_context_resolution", False):
        return NODE_CONTEXT_RESOLVER
    clean = {k: v for k, v in state.items()
             if k not in ("kpi_data_chunks", "trend_data_chunks")}
    clean["kpi_data_chunks"]  = []
    clean["trend_data_chunks"] = []
    return [
        Send(NODE_KPI_ANALYST,   clean),
        Send(NODE_TREND_ANALYST, clean),
    ]


def _route_after_context_resolver(state: AgentState):
    """After context resolution, always fan out to both analysts."""
    clean = {k: v for k, v in state.items()
             if k not in ("kpi_data_chunks", "trend_data_chunks")}
    clean["kpi_data_chunks"]  = []
    clean["trend_data_chunks"] = []
    return [
        Send(NODE_KPI_ANALYST,   clean),
        Send(NODE_TREND_ANALYST, clean),
    ]


def _route_after_data_quality_gate(state: AgentState) -> str:
    """
    NEW control loop: early data quality check.

    FAIL + retry budget remaining  -> re-dispatch KPI+Trend analysts
    PASS / WARN / retry exhausted  -> proceed to Synthesizer
    """
    dq = state.get("data_quality_result") or {}
    should_retry = dq.get("should_retry", False)
    retry_count  = state.get("data_retry_count", 0)

    if should_retry and retry_count <= MAX_DATA_RETRIES:
        # Return list of Send() for parallel retry
        return "retry_analysts"
    return NODE_SYNTHESIZER


def _route_after_critic(state: AgentState) -> str:
    """
    NEW control loop: Critic challenges the Strategist.

    Critic not approved + attempts remaining -> Strategist retry
    Critic approved OR attempts exhausted   -> ReportWriter
    """
    critic  = state.get("critic_output") or {}
    approved = critic.get("approved", True)
    attempt  = state.get("critic_attempt", 0)

    if not approved and attempt < MAX_CRITIC_ATTEMPTS:
        return NODE_STRATEGIST   # inject critique + retry
    return NODE_REPORT_WRITER


# Graph construction

def _build_graph():
    builder = StateGraph(AgentState)

    # Register all nodes
    builder.add_node(NODE_PLANNER,           node_planner)
    builder.add_node(NODE_CONTEXT_RESOLVER,  node_context_resolver)
    builder.add_node(NODE_KPI_ANALYST,       node_kpi_analyst)
    builder.add_node(NODE_TREND_ANALYST,     node_trend_analyst)
    builder.add_node(NODE_FAN_IN,            node_fan_in)
    builder.add_node(NODE_DATA_QUALITY_GATE, node_data_quality_gate)
    builder.add_node(NODE_SYNTHESIZER,       node_synthesizer)
    builder.add_node(NODE_STRATEGIST,        node_strategist)
    builder.add_node(NODE_CRITIC,            node_critic)
    builder.add_node(NODE_REPORT_WRITER,     node_report_writer)

    # Entry point
    builder.set_entry_point(NODE_PLANNER)

    # Planner -> (context_resolver | [kpi + trend])
    builder.add_conditional_edges(NODE_PLANNER, _route_after_planner)

    # Context resolver -> [kpi + trend] (parallel)
    builder.add_conditional_edges(NODE_CONTEXT_RESOLVER, _route_after_context_resolver)

    # Both analysts -> fan_in
    builder.add_edge(NODE_KPI_ANALYST,   NODE_FAN_IN)
    builder.add_edge(NODE_TREND_ANALYST, NODE_FAN_IN)

    # fan_in -> data_quality_gate (NEW)
    builder.add_edge(NODE_FAN_IN, NODE_DATA_QUALITY_GATE)

    # data_quality_gate conditional:
    #   "retry_analysts" -> Send() parallel retry
    #   NODE_SYNTHESIZER -> continue
    def _dqg_route(state: AgentState):
        dq = state.get("data_quality_result") or {}
        if dq.get("should_retry", False):
            # Pass a clean copy: strip old chunks and merged data so the
            # Annotated[list, operator.add] reducer doesn't double-accumulate.
            clean = {k: v for k, v in state.items()
                     if k not in ("kpi_data_chunks", "trend_data_chunks",
                                  "kpi_data", "trend_data", "data_quality_result")}
            clean["kpi_data_chunks"]  = []
            clean["trend_data_chunks"] = []
            return [
                Send(NODE_KPI_ANALYST,   clean),
                Send(NODE_TREND_ANALYST, clean),
            ]
        return NODE_SYNTHESIZER

    builder.add_conditional_edges(NODE_DATA_QUALITY_GATE, _dqg_route)

    # Linear: synthesizer -> strategist -> critic
    builder.add_edge(NODE_SYNTHESIZER, NODE_STRATEGIST)
    builder.add_edge(NODE_STRATEGIST,  NODE_CRITIC)

    # Critic conditional (NEW control loop):
    #   not approved + attempts remaining -> strategist retry
    #   approved or exhausted            -> report_writer
    builder.add_conditional_edges(
        NODE_CRITIC,
        _route_after_critic,
        {
            NODE_STRATEGIST:    NODE_STRATEGIST,
            NODE_REPORT_WRITER: NODE_REPORT_WRITER,
        },
    )

    # Terminal
    builder.add_edge(NODE_REPORT_WRITER, END)

    return builder.compile(checkpointer=MemorySaver())


def get_graph():
    """Return the compiled LangGraph (singleton)."""
    global _graph
    if _graph is None:
        _graph = _build_graph()
    return _graph