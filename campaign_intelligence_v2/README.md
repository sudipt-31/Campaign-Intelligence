# AI Campaign Intelligence Agent — v2 (Multi-Agent with Control Loops)

## What Changed from v1

v1 was a structured chain. v2 is an intelligent system with real control loops.

```
v1 (chain):
  Planner → Context → KPI+Trend → FanIn → Synthesizer → Strategist → Validation → Report
  Problem: Validation at end (too late), no retry, no critique, no data gate.

v2 (control loops):
  Planner → [ContextResolver?] → KPI+Trend (parallel)
  → FanIn → DataQualityGate ──(FAIL + retry budget)──→ [KPI+Trend retry]
                             ──(PASS/WARN)────────────→ Synthesizer
  → Strategist → Critic ──(not approved + attempts left)──→ Strategist (revision)
                        ──(approved or exhausted)──────────→ ReportWriter
```

## The 4 Problems Fixed

### 1. Validation moved to where it belongs (right after data fetch)
- `DataQualityGate` runs immediately after `FanIn`
- Pure Python, zero LLM calls — fast and deterministic
- Checks: KPI rows empty? Trend directions empty? Fetch errors excessive?
- If critical data is missing and retry budget allows → re-dispatches KPI+Trend analysts

### 2. Real retry loop for bad data
- `data_retry_count` tracked in state (cap: `MAX_DATA_RETRIES = 1`)
- Gate fails → `kpi_data_chunks` and `trend_data_chunks` reset → analysts re-run
- Same `Send()` parallel fan-out as initial run
- After retry exhausted → proceeds with warning, never blocks

### 3. Critic loop (intelligence layer)
- New `Critic` agent runs after every Strategist call
- Checks: Are recs specific? Does reasoning match data? Confidence honest?
- If `approved=False` → critique injected into Strategist prompt → strategy revised once
- Cap: `MAX_CRITIC_ATTEMPTS = 1` (prevents infinite loop)

### 4. Chain-of-thought reasoning throughout
- Every agent now emits a `reasoning` field
- `reasoning_trace` accumulates across the whole pipeline (Annotated reducer)
- Exposed in API response as `reasoning_trace`
- You can see exactly how each agent decided what it decided

## LangGraph Features Demonstrated

| Feature | Where |
|---------|-------|
| `StateGraph(AgentState)` | `core/graph/builder.py` |
| `Send()` parallel fan-out | Planner → KPI+Trend, DataQualityGate retry |
| `Annotated[list, operator.add]` reducer | `kpi_data_chunks`, `trend_data_chunks`, `reasoning_trace`, `error_log` |
| Conditional edges | 3 branch points: planner, DQG, critic |
| Back-edge retry loop | DataQualityGate → KPI+Trend |
| Back-edge critique loop | Critic → Strategist |
| `MemorySaver` checkpointer | Multi-turn conversation memory |
| Zero-LLM nodes | `FAN_IN`, `DATA_QUALITY_GATE` |
| LangChain `bind_tools()` | KPI Analyst, Trend Analyst |

## New Files

- `agents/critic.py` — Critic agent (challenges strategy)
- `core/state.py` — `DataQualityResult`, `CriticOutput`, `reasoning_trace` fields
- `core/config.py` — `MAX_DATA_RETRIES`, `MAX_CRITIC_ATTEMPTS`, `CONFIDENCE_THRESHOLD`

## New API Response Fields

- `reasoning_trace`: list of per-agent reasoning strings
- `data_quality`: `{severity, issues, reasoning, retry_count}`
- `critic_approved`: bool — was the strategy approved by the Critic?

## Setup

```bash
cp .env.example .env
# add: OPENAI_API_KEY=sk-...

pip install -r requirements.txt
python main.py
# → http://localhost:8000/docs
```

## Key Config Knobs

```python
# core/config.py
CONFIDENCE_THRESHOLD = 55   # min strategist score (currently informational)
MAX_DATA_RETRIES     = 1    # how many times to retry on bad data
MAX_CRITIC_ATTEMPTS  = 1    # how many times critic can bounce strategy back
```
