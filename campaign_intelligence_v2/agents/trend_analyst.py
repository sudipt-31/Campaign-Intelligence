"""
agents/trend_analyst.py
=======================
Node 4 — Trend Analyst (runs in parallel with KPI Analyst).

LangChain tool-calling loop for diagnostic metrics, ad recall, and trend direction.
"""
from __future__ import annotations

import json

from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE
from core.state import TrendData
from tools.registry import TREND_TOOLS
from prompts.agent_prompts import TREND_ANALYST_PROMPT

_TOOL_MAP = {t.name: t for t in TREND_TOOLS}
_MAX_ITERS = 8


def _empty() -> TrendData:
    return TrendData(diagnostics=[], ad_recall=[], trend_directions=[],
                     top_creatives=[], anomalies=[], fetch_errors=[])


def run_trend_analyst(question: str) -> TrendData:
    """LangChain tool-calling loop for the Trend Analyst."""
    llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=2048)
    agent = llm.bind_tools(TREND_TOOLS)

    messages = [
        SystemMessage(content=TREND_ANALYST_PROMPT),
        HumanMessage(content=f"User question: {question}\n\nFetch all relevant trend, diagnostic and ad recall data now."),
    ]

    collected: dict[str, list] = {
        "diagnostics": [], "ad_recall": [], "trend_directions": [],
        "top_creatives": [], "anomalies": [], "fetch_errors": [],
    }

    for _ in range(_MAX_ITERS):
        response = agent.invoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            tool_id   = tc["id"]

            try:
                tool_fn = _TOOL_MAP.get(tool_name)
                if tool_fn:
                    result = tool_fn.invoke(tool_args)
                    result_str = json.dumps(result)

                    if tool_name in ("get_diagnostics_for_campaign",):
                        collected["diagnostics"].extend(result if isinstance(result, list) else [])
                    elif tool_name == "get_trend_directions":
                        collected["trend_directions"].extend(result if isinstance(result, list) else [])
                    elif tool_name in ("get_ad_recall_for_campaign",):
                        collected["ad_recall"].extend(result if isinstance(result, list) else [])
                    elif tool_name == "get_top_ad_recall_all":
                        collected["top_creatives"].extend(result if isinstance(result, list) else [])
                    elif tool_name == "get_anomalies":
                        collected["anomalies"].extend(result if isinstance(result, list) else [])
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})
                    collected["fetch_errors"].append(f"Unknown tool: {tool_name}")

            except Exception as exc:
                result_str = json.dumps({"error": str(exc)})
                collected["fetch_errors"].append(f"{tool_name}: {exc}")

            messages.append(ToolMessage(content=result_str, tool_call_id=tool_id))

    return TrendData(**collected)
