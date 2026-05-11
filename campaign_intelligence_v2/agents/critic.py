"""
agents/critic.py -- NEW
========================
Critic Agent -- challenges the Strategist's output.

This is the intelligence layer missing from v1.
Instead of blindly accepting the strategy, the Critic:
  1. Checks whether recommendations are specific (campaign names + numbers).
  2. Verifies the reasoning aligns with the synthesis data.
  3. Challenges unjustified confidence scores.
  4. Surfaces missed anomalies or risks.

One LLM call. Returns CriticOutput.
"""
from __future__ import annotations

import json
import re
from typing import Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_TOKENS
from core.state import CriticOutput, StrategistOutput, SynthesisOutput
from prompts.agent_prompts import CRITIC_PROMPT


def run_critic(
    question: str,
    synthesis: SynthesisOutput,
    strategy: StrategistOutput,
) -> CriticOutput:
    """Challenge the strategist output. Returns CriticOutput."""

    context = {
        "question": question,
        "synthesis": synthesis,
        "strategy": {
            "ranked_campaigns": strategy.get("ranked_campaigns", []),
            "recommendations":  strategy.get("recommendations", []),
            "confidence_score": strategy.get("confidence_score", 0),
            "reasoning":        strategy.get("reasoning", ""),
        },
    }

    try:
        llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2, max_tokens=LLM_MAX_TOKENS)
        resp = llm.invoke([
            SystemMessage(content=CRITIC_PROMPT),
            HumanMessage(content=json.dumps(context, indent=2)),
        ])
        text = resp.content.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        parsed = json.loads(text)

        return CriticOutput(
            approved=bool(parsed.get("approved", True)),
            challenges=parsed.get("challenges", []),
            revised_recommendations=parsed.get("revised_recommendations", []),
            critique_reasoning=parsed.get("critique_reasoning", ""),
        )
    except Exception as exc:
        # If critic fails, approve and log — don't block the pipeline
        return CriticOutput(
            approved=True,
            challenges=[],
            revised_recommendations=[],
            critique_reasoning=f"Critic LLM error: {exc} — auto-approved",
        )
