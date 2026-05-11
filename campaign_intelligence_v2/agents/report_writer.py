"""
agents/report_writer.py -- v2
==============================
Report Writer. Now uses critic-approved recs and attaches reasoning_trace.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from core.state import FinalResponse, KPIData, TrendData, SynthesisOutput, StrategistOutput
from prompts.agent_prompts import REPORT_WRITER_PROMPT


def run_report_writer(
    question: str,
    synthesis: Optional[SynthesisOutput],
    strategy: Optional[StrategistOutput],
    kpi_data: Optional[KPIData],
    trend_data: Optional[TrendData],
    agent_trace: list[str],
    error_log: list[str],
) -> FinalResponse:
    context = {
        "question":  question,
        "synthesis": synthesis or {},
        "strategy":  strategy or {},
        "kpi_snapshot": {
            "kpi_comparison": (kpi_data or {}).get("kpi_comparison", [])[:6],
            "brand_uplift":   (kpi_data or {}).get("brand_uplift", [])[:10],
            "budget_summary": (kpi_data or {}).get("budget_summary", [])[:6],
        },
        "trend_snapshot": {
            "trend_directions": (trend_data or {}).get("trend_directions", []),
            "top_creatives":    (trend_data or {}).get("top_creatives", [])[:5],
            "anomalies":        (trend_data or {}).get("anomalies", []),
        },
    }
    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS)
        resp = llm.invoke([
            SystemMessage(content=REPORT_WRITER_PROMPT),
            HumanMessage(content=json.dumps(context, indent=2)),
        ])
        text = resp.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)

        raw_table = parsed.get("table", {})
        table_data = None
        if raw_table and raw_table.get("columns") and raw_table.get("rows"):
            table_data = {"columns": raw_table["columns"], "rows": raw_table["rows"]}

        return FinalResponse(
            answer=parsed.get("answer", "Analysis complete. See details below."),
            rich_text=parsed.get("rich_text", ""),
            chart_data=parsed.get("chart_data", []),
            chart_type=parsed.get("chart_type", "bar"),
            chart_title=parsed.get("chart_title", "Campaign Performance"),
            table_data=table_data,
            recommendations=parsed.get("recommendations", []),
            confidence_score=int(parsed.get("confidence_score", 70)),
            agent_trace=agent_trace,
            reasoning_trace=[],   # populated by node_report_writer
            error="; ".join(error_log) if error_log else None,
        )
    except Exception as exc:
        recs = (strategy or {}).get("recommendations", []) or ["Review data manually."]
        return FinalResponse(
            answer=f"Analysis completed with {len(error_log)} warning(s).",
            rich_text=f"## Analysis\n\n{(synthesis or {}).get('narrative', '')}\n\n**Note:** {exc}",
            chart_data=_fallback_chart(kpi_data),
            chart_type="bar",
            chart_title="Campaign KPI Summary",
            table_data=None,
            recommendations=recs[:3],
            confidence_score=50,
            agent_trace=agent_trace,
            reasoning_trace=[],
            error=str(exc),
        )


def _fallback_chart(kpi_data: Optional[KPIData]) -> list[dict]:
    if not kpi_data:
        return []
    return [
        {"name": r.get("campaign_name", r.get("campaign_code", "")),
         "value": r.get("brand_awareness", 0),
         "metric": "Brand Awareness"}
        for r in kpi_data.get("kpi_comparison", [])[:6]
    ]
