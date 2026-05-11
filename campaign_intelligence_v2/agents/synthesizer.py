"""
agents/synthesizer.py -- v2
============================
Insight Synthesizer. Now includes mandatory reasoning field.
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from core.state import KPIData, TrendData, SynthesisOutput
from prompts.agent_prompts import SYNTHESIZER_PROMPT

_FALLBACK = SynthesisOutput(
    narrative="Data analysis completed. Specific insights available below.",
    key_findings=["KPI and trend data fetched", "Review charts for details"],
    top_campaign="See ranked table",
    underperforming=[],
    anomalies_noted=[],
    reasoning="Fallback used — LLM synthesis not available.",
)


def _truncate(data: list, max_rows: int = 30) -> list:
    return data[:max_rows]


def run_synthesizer(question: str, kpi_data: KPIData, trend_data: TrendData) -> SynthesisOutput:
    context = {
        "question": question,
        "kpi": {
            "brand_uplift":     _truncate(kpi_data.get("brand_uplift", []), 25),
            "target_vs_actual": _truncate(kpi_data.get("target_vs_actual", []), 20),
            "budget_summary":   _truncate(kpi_data.get("budget_summary", []), 10),
            "kpi_comparison":   _truncate(kpi_data.get("kpi_comparison", []), 10),
        },
        "trend": {
            "diagnostics":      _truncate(trend_data.get("diagnostics", []), 20),
            "trend_directions": trend_data.get("trend_directions", []),
            "top_creatives":    _truncate(trend_data.get("top_creatives", []), 10),
            "anomalies":        trend_data.get("anomalies", []),
        },
    }
    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS)
        resp = llm.invoke([
            SystemMessage(content=SYNTHESIZER_PROMPT),
            HumanMessage(content=json.dumps(context, indent=2)),
        ])
        text = resp.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        return SynthesisOutput(
            narrative=parsed.get("narrative", ""),
            key_findings=parsed.get("key_findings", []),
            top_campaign=parsed.get("top_campaign", ""),
            underperforming=parsed.get("underperforming", []),
            anomalies_noted=parsed.get("anomalies_noted", []),
            reasoning=parsed.get("reasoning", ""),
        )
    except Exception as exc:
        return SynthesisOutput(**{**_FALLBACK, "anomalies_noted": [f"Synthesis error: {exc}"]})
