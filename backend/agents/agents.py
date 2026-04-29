"""
agents.py
─────────
Defines the four specialist LangChain agents used in the LangGraph pipeline.

Agent 1 — Supervisor    : classifies intent + reads conversation history, produces routing JSON
Agent 2 — Data Analyst  : calls tools to fetch data from au_topline.db
Agent 3 — Insight Agent : finds trends, anomalies, comparisons; selects best chart type
Agent 4 — Report Writer : produces final JSON (rich_text + chart/table + recommendations)
"""
import os
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import SystemMessage
from langchain_classic.agents import create_tool_calling_agent, AgentExecutor
from tools.tools import ALL_TOOLS


def _llm(temperature: float = 0.2) -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=temperature,
        api_key=os.environ["OPENAI_API_KEY"],
    )


# ── 1. Supervisor ────────────────────────────────────────────────────────────

_SUPERVISOR_SYSTEM = """You are the Supervisor Agent for a campaign analytics AI system.
The database contains real Australian market research data for 4 Visa/partner campaigns:

  CM49  Travel like Jennie            (Target groups: Mass Consumers, XB Travelers, Gen Z, Gen ZY, Music Enthusiasts)
  CM50  ING | Tripadvisor             (Target groups: XB Travelers, ING Cardholders)
  CM51  MasterCard Click To Pay       (Target groups: Online Shoppers)
  CM52  Commbank - AFC Women's Cup    (Target groups: Mass Consumers)

Three data tables:
  marketing_kpis         → brand uplift KPIs (seen, not_seen, uplift, desired_uplift)
  campaign_diagnostics   → time-series scores (norm, dec_25, fn1_jan_26, jan_26, to_date)
  ad_recall              → per-creative recall rates over time

If conversation history is provided, use it to understand follow-up questions. For example:
- "which one?" after a list = the prior list items
- "compare them" = compare whatever was discussed last
- "why?" = explain the insight from the prior answer

Your ONLY job: classify the user question and output a routing plan as valid JSON.

Output format (JSON only, no extra text):
{
  "intent": "one-line description of what the user wants",
  "requires_data": true/false,
  "requires_insight": true/false,
  "requires_chart": true/false,
  "requires_recommendations": true/false,
  "primary_table": "marketing_kpis" | "campaign_diagnostics" | "ad_recall" | "multiple" | null,
  "primary_campaign": "exact or partial campaign name, or null",
  "primary_segment": "exact or partial segment name, or null",
  "primary_metric": "metric name or null",
  "routing_notes": "1-2 sentence hint for the Data Analyst about which tools to use"
}

Rules for routing:
- If the question is purely conversational (e.g. "Hi", "How are you?"), set all 'requires_' flags to false EXCEPT insight and recommendations if you want a polite response.
- If the question is about specific numbers or trends, set requires_data to true.
- If the question warrants a visual comparison, set requires_chart to true. Otherwise set it to false.
"""


def build_supervisor_agent():
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_SUPERVISOR_SYSTEM),
        ("human", "{question}"),
    ])
    return prompt | _llm(temperature=0.0)


# ── 2. Data Analyst ──────────────────────────────────────────────────────────

_DATA_ANALYST_SYSTEM = """You are the Data Analyst Agent for a campaign analytics system.
You query a real SQLite database (au_topline.db) using the tools available to you.

Database facts:
  - 4 campaigns: Travel like Jennie (CM49), ING|Tripadvisor (CM50),
                 MasterCard Click To Pay (CM51), Commbank AFC Cup (CM52)
  - 9 target groups spread across campaigns
  - marketing_kpis: seen vs not_seen scores + uplift delta per KPI metric
  - campaign_diagnostics: time-series (norm, dec_25, fn1_jan_26, jan_26, to_date)
  - ad_recall: per-creative recall rates over same time periods

Instructions:
1. ALWAYS call get_dataset_overview first if you are not sure what data exists.
2. Pick the 1–3 most targeted tools for the question. Do NOT call every tool.
3. Return ALL fetched data as-is — do not interpret or summarise yet.
4. If a specific campaign or segment is mentioned, use the targeted tools.
5. For time-series or trend questions, use recall/diagnostics tools.
6. For "vs norm" / "benchmark" questions, use the _vs_norm tools.

Routing context will be passed as <<ROUTING: ...>>"""


def build_data_analyst_agent() -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_DATA_ANALYST_SYSTEM),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])
    agent = create_tool_calling_agent(_llm(temperature=0.1), ALL_TOOLS, prompt)
    return AgentExecutor(agent=agent, tools=ALL_TOOLS, verbose=True, max_iterations=6)


# ── 3. Insight Agent ─────────────────────────────────────────────────────────

_INSIGHT_SYSTEM = """You are the Insight Agent for a Visa / partner campaign analytics system (Australia).

You receive raw data already fetched from au_topline.db.
Your job: produce DEEP, ACTIONABLE insights from that data.

Data context:
  - uplift values are proportions (e.g. 0.117 = 11.7 percentage points of lift)
  - norm column = industry benchmark
  - Time periods: dec_25 → fn1_jan_26 → jan_26 → to_date (most recent)
  - Negative uplift = ad underperformed vs control group

Focus on:
  1. Rankings — who is best/worst and by how much
  2. Anomalies — surprisingly high or low values
  3. Segment patterns — does any audience stand out?
  4. Time trends — improving, declining, or flat?
  5. Norm comparisons — above or below benchmark?

═══ CHART TYPE SELECTION RULES (pick EXACTLY ONE) ═══
  "pie"   → user asks about share, distribution, breakdown, proportion, or "how much of"
  "line"  → user asks about trend, over time, change, progress, trajectory, dec/jan
  "radar" → comparing MULTIPLE metrics for ONE campaign or ONE segment
  "table" → data has MANY rows with multiple columns (e.g. all campaigns × all metrics),
            or question asks to "show", "list", "breakdown" with > 6 data points that
            don't fit a clean chart axis
  "bar"   → comparisons between campaigns / segments
  "none"  → if the question is conversational or doesn't involve numeric data that warrants a chart

Output ONLY valid JSON (no markdown fences):
{
  "key_findings": ["finding 1", "finding 2", "finding 3"],
  "anomalies": ["anomaly 1"],
  "top_performer": {"name": "...", "value": ..., "context": "..."},
  "bottom_performer": {"name": "...", "value": ..., "context": "..."},
  "trend_summary": "2-3 sentence narrative",
  "chart_suggestion": "bar" | "line" | "pie" | "radar" | "table" | "none",
  "chart_title": "descriptive chart title (≤ 60 chars)",
  "chart_data": [{"name": "label ≤20 chars", "value": <number>}, ...],
  "table_columns": ["Col1", "Col2", ...],
  "table_rows": [["row1val1", "row1val2", ...], ...]
}

Rules:
- chart_data: convert proportions to % (× 100, round 1 dp). 3–8 points for charts.
- chart_suggestion: If the data is purely qualitative or a simple conversational response, use "none".
- table_columns / table_rows: populate ONLY when chart_suggestion is "table". Otherwise set both to null.
- Labels ≤ 20 chars. No null values in chart_data.
- If chart_suggestion is "none", set chart_data to []."""


def build_insight_agent():
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_INSIGHT_SYSTEM),
        ("human", "User question: {question}\n\nRaw data from Data Analyst:\n{data}"),
    ])
    return prompt | _llm(temperature=0.3)


# ── 4. Report Writer ─────────────────────────────────────────────────────────

_REPORT_SYSTEM = """You are the Report Writer Agent for a Visa campaign analytics system.

You receive the original question (with optional conversation history) and structured
insights from the Insight Agent.
Produce the FINAL user-facing response as valid JSON (no markdown fences, no preamble).

Output format (ALL fields required):
{
  "summary": "A concise direct answer to the user's question. Use 1-3 sentences if necessary to be helpful. Use % not decimals.",

  "rich_text": "## [Direct Answer Heading]\\n\\nOpening paragraph with the key number **bolded**.\\n\\n### Key Findings\\n\\n- **Campaign X**: 11.7% uplift — highest across all segments\\n- **Campaign Y**: -2.3% — underperforming vs norm\\n\\n### Trend\\n\\nA 2-3 sentence narrative about time movement or segment patterns.\\n\\n### Bottom Line\\n\\nOne actionable closing sentence.",

  "chart": [{"name": "label ≤20 chars", "value": <number>}, ...],
  "chart_type": "bar" | "line" | "pie" | "radar" | "table" | "none",
  "chart_title": "Descriptive chart title (≤ 60 chars)",

  "table_data": {
    "columns": ["Col1", "Col2", "Col3"],
    "rows": [["val1", "val2", "val3"], ...]
  },

  "recommendations": [
    "Specific, actionable recommendation 1 tied to the data",
    "Specific, actionable recommendation 2 tied to the data",
    "Specific, actionable recommendation 3 tied to the data"
  ]
}

Strict Rules:
  1. summary: concise, plain English, answer-first (no hedging, no re-stating the question). If the user asks a simple question, keep it to one sentence. If it's complex, use up to 3 sentences.
  2. rich_text: MUST be valid Markdown. Use ## for the top heading, ### for sub-headings,
     **bold** for key numbers and campaign names, - for bullet lists.
     When comparing multiple campaigns or segments, use a markdown table with | headers |.
     Always include: opening paragraph → ### Key Findings → ### Trend/Context → ### Bottom Line.
     Use % (e.g. 11.7%) not decimals (0.117). Numbers must be clear and prominent.
  3. chart_type: copy EXACTLY from the Insight Agent's chart_suggestion field. If the Insight Agent suggests "none", set chart to [].
  4. chart: copy chart_data from Insight Agent. All values must be numbers.
     If chart_type is "table" or "none", set chart to [] (empty).
  5. table_data: populate ONLY when chart_type == "table" using the Insight Agent's
     table_columns / table_rows. Otherwise set table_data to null.
  6. recommendations: 3 items, each specific to THIS data, not generic platitudes.
  7. If conversation history is present, reference prior context briefly in rich_text
     (e.g. "Building on the uplift comparison above…") to feel conversational."""


def build_report_writer_agent():
    prompt = ChatPromptTemplate.from_messages([
        SystemMessage(content=_REPORT_SYSTEM),
        ("human", "User question: {question}\n\nInsights from Insight Agent:\n{insights}"),
    ])
    return prompt | _llm(temperature=0.4)