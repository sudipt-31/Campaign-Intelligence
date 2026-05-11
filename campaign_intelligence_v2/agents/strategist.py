"""
agents/strategist.py -- v2
===========================
Budget Strategist.

Changes vs v1:
  - Accepts critique_block (from Critic) AND confidence_note (threshold pressure).
  - reasoning field is now mandatory in the response schema.
  - Critique is injected directly into the system prompt.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from core.state import SynthesisOutput, KPIData, TrendData, StrategistOutput
from prompts.agent_prompts import STRATEGIST_PROMPT


def run_strategist(
    question: str,
    synthesis: SynthesisOutput,
    kpi_data: KPIData,
    trend_data: TrendData,
    validation_critique: Optional[str] = None,  # kept for v1 compat
    confidence_note: Optional[str] = None,       # NEW
) -> StrategistOutput:
    """One LLM call to produce ranked campaign strategy with chain-of-thought reasoning."""

    # Support both v1 string critique and v2 block format
    critique_block = ""
    if validation_critique:
        critique_block = (
            f"\nCRITIC CHALLENGES (you MUST address each in your reasoning):\n"
            f"{validation_critique}\n"
        )

    prompt = STRATEGIST_PROMPT.format(
        critique_block=critique_block,
        confidence_note=confidence_note or "",
    )

    context = {
        "question":         question,
        "synthesis":        synthesis,
        "budget_data":      kpi_data.get("budget_summary", [])[:8],
        "kpi_comparison":   kpi_data.get("kpi_comparison", []),
        "trend_directions": trend_data.get("trend_directions", []),
        "top_creatives":    trend_data.get("top_creatives", [])[:5],
    }

    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=LLM_MAX_TOKENS)
        resp = llm.invoke([
            SystemMessage(content=prompt),
            HumanMessage(content=json.dumps(context, indent=2)),
        ])
        text = resp.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)
        return StrategistOutput(
            ranked_campaigns=parsed.get("ranked_campaigns", []),
            recommendations=parsed.get("recommendations", []),
            confidence_score=int(parsed.get("confidence_score", 70)),
            reasoning=parsed.get("reasoning", ""),
        )
    except Exception as exc:
        return StrategistOutput(
            ranked_campaigns=[],
            recommendations=[f"Analysis error: {exc}. Please review the data manually."],
            confidence_score=40,
            reasoning=f"Strategist LLM call failed: {exc}",
        )
