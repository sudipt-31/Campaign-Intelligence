"""
agents/kpi_analyst.py
=====================
Node 3 — KPI Analyst (runs in parallel with Trend Analyst).

Uses LangChain tool-calling (bind_tools + agentic loop) to:
1. Select the right KPI/budget tools based on the question.
2. Execute tool calls against the database.
3. Return structured KPIData.

LangChain pattern: ChatOpenAI.bind_tools() → tool call loop → collect results.
This is the correct LangChain tool-use pattern — NOT AgentExecutor.
"""
from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE
from core.state import KPIData
from tools.registry import KPI_TOOLS
from prompts.agent_prompts import KPI_ANALYST_PROMPT

_TOOL_MAP = {t.name: t for t in KPI_TOOLS}
_MAX_ITERS = 8


def _empty() -> KPIData:
    return KPIData(brand_uplift=[], target_vs_actual=[], budget_summary=[], kpi_comparison=[], fetch_errors=[])


def run_kpi_analyst(question: str) -> KPIData:
    """
    LangChain tool-calling loop for the KPI Analyst.
    Returns a fully-populated KPIData dict.
    """
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=2048)
    agent = llm.bind_tools(KPI_TOOLS)

    messages = [
        SystemMessage(content=KPI_ANALYST_PROMPT),
        HumanMessage(content=f"User question: {question}\n\nFetch all relevant KPI and budget data now."),
    ]

    collected: dict[str, list] = {
        "brand_uplift": [], "target_vs_actual": [],
        "budget_summary": [], "kpi_comparison": [], "fetch_errors": [],
    }

    for _ in range(_MAX_ITERS):
        response = agent.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            # Agent is done — try to parse JSON from final text
            break

        # Execute each tool call
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            tool_id   = tc["id"]

            try:
                tool_fn = _TOOL_MAP.get(tool_name)
                if tool_fn:
                    result = tool_fn.invoke(tool_args)
                    result_str = json.dumps(result)

                    # Accumulate into known buckets
                    if tool_name == "get_brand_uplift_all":
                        collected["brand_uplift"].extend(result if isinstance(result, list) else [])
                    elif tool_name in ("get_target_vs_actual",):
                        collected["target_vs_actual"].extend(result if isinstance(result, list) else [])
                    elif tool_name in ("get_budget_summary", "get_budget_for_campaign", "get_top_roi_channels"):
                        collected["budget_summary"].extend(result if isinstance(result, list) else [])
                    elif tool_name == "get_kpi_comparison_table":
                        collected["kpi_comparison"].extend(result if isinstance(result, list) else [])
                    # kpis_for_campaign goes into brand_uplift too for display
                    elif tool_name in ("get_kpis_for_campaign", "get_kpis_for_campaign_segment"):
                        collected["brand_uplift"].extend(result if isinstance(result, list) else [])
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    collected["fetch_errors"].append(f"Unknown tool: {tool_name}")

            except Exception as exc:
                result_str = json.dumps({"error": str(exc)})
                collected["fetch_errors"].append(f"{tool_name}: {exc}")

            messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))

    return KPIData(**collected)
