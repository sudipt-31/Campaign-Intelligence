"""
agents/planner.py
=================
Node 1 — Planner.
Classifies the question into a query type and identifies campaigns/segments in scope.
Uses a rule engine first; falls back to LLM for ambiguous questions.
Zero tool calls — pure classification.
"""
from __future__ import annotations

import json
import re

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI

from core.config import LLM_MODEL, LLM_TEMPERATURE, VALID_CAMPAIGN_CODES
from core.state import ExecutionPlan
from prompts.agent_prompts import PLANNER_PROMPT


_QUERY_KEYWORDS: dict[str, list[str]] = {
    "budget_reallocation": ["budget", "realloc", "spend", "roi", "invest", "fund", "money", "channel", "burn"],
    "kpi_deep_dive":       ["awareness", "intent", "trust", "nps", "preference", "kpi", "target", "achieve"],
    "trend_analysis":      ["trend", "week", "over time", "improving", "declining", "trajectory", "w4", "w8", "w12", "progress"],
    "ad_creative_analysis":["creative", "recall", "tiktok", "youtube", "instagram", "reel", "video", "banner", "email"],
    "segment_analysis":    ["gen z", "millennial", "boomer", "parent", "professional", "student", "budget conscious", "eco", "fitness", "nester"],
    "cross_campaign_comparison": ["compare", "vs", "versus", "best", "worst", "rank", "which campaign", "all campaign"],
}

_CAMPAIGN_ALIASES: dict[str, str] = {
    "spring brand push": "CA01",    "ca01": "CA01",
    "gen z digital native": "CA02", "ca02": "CA02",
    "premium product reveal": "CA03","ca03": "CA03",
    "loyalty retention drive": "CA04","ca04": "CA04",
    "summer lifestyle": "CA05",     "ca05": "CA05",
    "value seeker": "CA06",         "ca06": "CA06",
}

_SEGMENT_NAMES = [
    "Gen Z", "Millennials", "Gen X Parents", "Baby Boomers", "Urban Professionals",
    "Budget Conscious", "Eco-Conscious", "Sports & Fitness", "Empty Nesters", "Students",
]


def _rule_classify(question: str) -> tuple[str, float]:
    q = question.lower()
    scores: dict[str, int] = {k: 0 for k in _QUERY_KEYWORDS}
    for qtype, keywords in _QUERY_KEYWORDS.items():
        for kw in keywords:
            if kw in q:
                scores[qtype] += 1
    best = max(scores, key=scores.get)
    confidence = min(scores[best] / 3.0, 1.0)
    return (best if confidence > 0 else "general_insight"), confidence


def _extract_campaigns(question: str) -> list[str]:
    q = question.lower()
    found = set()
    for alias, code in _CAMPAIGN_ALIASES.items():
        if alias in q:
            found.add(code)
    if not found:
        return VALID_CAMPAIGN_CODES  # all campaigns in scope
    return sorted(found)


def _extract_segments(question: str) -> list[str]:
    q = question.lower()
    return [s for s in _SEGMENT_NAMES if s.lower() in q]


def run_planner(question: str) -> ExecutionPlan:
    query_type, conf = _rule_classify(question)
    campaigns = _extract_campaigns(question)
    segments  = _extract_segments(question)
    # Use whole-word matching to avoid false positives like "it" inside "quarter"
    import re as _re
    _CR_PATTERNS = [r"\bit\b", r"\bthat\b", r"\bthose\b", r"the previous", r"the one", r"\bsame\b"]
    requires_cr = any(_re.search(p, question.lower()) for p in _CR_PATTERNS)

    # Use LLM only when rule engine is truly uncertain (raised from 0.4 to avoid
    # triggering on clear single-keyword questions like "budget" scoring 0.33)
    if conf < 0.25:
        try:
            llm = ChatOpenAI(model=LLM_MODEL, temperature=LLM_TEMPERATURE, max_tokens=512)
            resp = llm.invoke([
                SystemMessage(content=PLANNER_PROMPT),
                HumanMessage(content=f"Question: {question}"),
            ])
            text = resp.content.strip()
            # Strip markdown fences if present
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
            plan = json.loads(text)
            return ExecutionPlan(
                query_type=plan.get("query_type", query_type),
                campaigns_in_scope=plan.get("campaigns_in_scope", campaigns),
                segments_in_scope=plan.get("segments_in_scope", segments),
                requires_context_resolution=plan.get("requires_context_resolution", requires_cr),
                routing_reason=plan.get("routing_reason", "LLM classification"),
            )
        except Exception:
            pass  # fall through to rule-based result

    return ExecutionPlan(
        query_type=query_type,
        campaigns_in_scope=campaigns,
        segments_in_scope=segments,
        requires_context_resolution=requires_cr,
        routing_reason=f"Rule engine ({conf:.0%} confidence): {query_type}",
    )
