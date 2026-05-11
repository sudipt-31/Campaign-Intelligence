"""
main.py
=======
FastAPI entry point — AI Campaign Intelligence Agent.

Endpoints (unchanged from original):
  GET  /health
  POST /query             — main NL question endpoint
  GET  /query/stream      — Server-Sent Events for live agent progress
  GET  /dataset/info
  GET  /suggestions
  POST /export
"""
from __future__ import annotations

import os
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

# Load .env from project dir
for _p in [Path.cwd(), Path.cwd().parent, Path(__file__).parent]:
    _ef = _p / ".env"
    if _ef.exists():
        try:
            load_dotenv(dotenv_path=str(_ef), encoding="utf-8", override=False)
        except UnicodeDecodeError:
            load_dotenv(dotenv_path=str(_ef), encoding="utf-16", override=False)
        break

from models import QueryRequest, QueryResponse, HealthResponse, ExportRequest
from service import run_query, get_health_info
from export.export_service import generate_docx, generate_pptx
from db.loader import get_all_campaigns, get_all_segments, get_campaign_summary_view

# ── Shared run cache ──────────────────────────────────────────────────────────
# Keyed by (question, thread_id). Stores asyncio.Future so the POST /query
# endpoint can await the result that /query/stream already kicked off,
# instead of running a second independent pipeline.
_run_cache: dict[str, asyncio.Future] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Seeding / verifying database...")
    from db.seed import seed
    from db.loader import DB_PATH
    if not DB_PATH.exists() or DB_PATH.stat().st_size < 10_000:
        seed()

    info = get_health_info()
    if info["status"] != "ok":
        raise RuntimeError(f"[Startup] Database unavailable: {info.get('error')}")
    print(f"[Startup] DB OK — {info['campaigns_count']} campaigns, "
          f"{len(info['segments_available'])} segments.")
    print("[Startup] LangGraph v2 pipeline ready: "
          "Planner → [ContextResolver?] → KPI+Trend (parallel) → "
          "FanIn → Synthesizer → Strategist → Validation → ReportWriter")
    yield


app = FastAPI(
    title="AI Campaign Intelligence Agent",
    description=(
        "Multi-agent LangGraph system for RetailCo campaign analytics. "
        "Pipeline: Planner → Context Resolver → KPI Analyst + Trend Analyst (parallel, Send()) "
        "→ Fan-In → Synthesizer → Strategist → Validation → Report Writer. "
        "LangChain tool-calling pattern used for all data-fetching agents."
    ),
    version="5.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── /health ───────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    info = get_health_info()
    if info["status"] != "ok":
        raise HTTPException(503, detail=info.get("error", "Database unavailable"))
    return HealthResponse(**info)


# ── /query ────────────────────────────────────────────────────────────────────

@app.post("/query", response_model=QueryResponse, tags=["Analytics"])
async def query_campaigns(request: QueryRequest):
    """
    Submit a natural-language question about RetailCo campaign performance.
    If /query/stream was already called for the same question, this reuses
    the in-progress pipeline run instead of launching a second one.
    """
    if not request.question.strip():
        raise HTTPException(400, detail="Question cannot be empty.")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, detail="OPENAI_API_KEY is not configured.")

    q = request.question.strip()
    history = [m.model_dump() for m in (request.chat_history or [])]

    # Reuse an already-running stream pipeline if one exists for this question.
    if q in _run_cache:
        fut = _run_cache[q]
        try:
            return await asyncio.wait_for(asyncio.shield(fut), timeout=120)
        except asyncio.TimeoutError:
            raise HTTPException(504, detail="Pipeline timed out.")
        finally:
            _run_cache.pop(q, None)

    # No stream in progress — run directly (standalone POST usage).
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: run_query(question=q, chat_history=history))


# ── /query/stream ─────────────────────────────────────────────────────────────

@app.get("/query/stream", tags=["Analytics"])
async def stream_query(question: str):
    """
    Server-Sent Events endpoint. Streams live agent progress to the frontend.

    Usage: GET /query/stream?question=Which+campaign+should+get+more+budget

    Each SSE event:  data: [AGENT_NAME] status message\\n\\n
    Final event:     data: __DONE__\\n\\n
    """
    if not question.strip():
        raise HTTPException(400, detail="Question cannot be empty.")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        async def _err():
            yield "data: [ERROR] OPENAI_API_KEY not set.\n\n"
            yield "data: __DONE__\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache"})

    async def event_generator():
        from core.graph import nodes as nodes_module
        nodes_module.LIVE_UPDATES.clear()

        loop = asyncio.get_event_loop()
        result_holder: dict = {}

        # Register a Future in the shared cache so POST /query can reuse this run.
        fut: asyncio.Future = loop.create_future()
        q = question.strip()
        _run_cache[q] = fut

        def _run():
            try:
                result = run_query(question=question, chat_history=[])
                result_holder["result"] = result
                loop.call_soon_threadsafe(fut.set_result, result)
            except Exception as exc:
                result_holder["error"] = str(exc)
                loop.call_soon_threadsafe(fut.set_exception, exc)

        task = loop.run_in_executor(None, _run)

        last_idx = 0
        while not task.done():
            current = nodes_module.LIVE_UPDATES
            if len(current) > last_idx:
                for line in current[last_idx:]:
                    yield f"data: {line}\n\n"
                last_idx = len(current)
            await asyncio.sleep(0.25)

        # Drain remaining
        for line in nodes_module.LIVE_UPDATES[last_idx:]:
            yield f"data: {line}\n\n"

        if "error" in result_holder:
            yield f"data: [ERROR] {result_holder['error']}\n\n"

        # Clean up cache entry once stream is done.
        _run_cache.pop(question.strip(), None)

        yield "data: __DONE__\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── /dataset/info ─────────────────────────────────────────────────────────────

@app.get("/dataset/info", tags=["Data"])
async def dataset_info():
    try:
        campaigns = get_all_campaigns()
        segments  = get_all_segments()
        summary   = get_campaign_summary_view()
        return {
            "campaigns":      [c["campaign_name"] for c in campaigns],
            "campaign_codes": [c["campaign_code"] for c in campaigns],
            "segments":       list({s["segment_name"] for s in segments}),
            "kpi_metrics":    ["Brand Awareness", "Purchase Intent", "Brand Trust", "Preference", "NPS Score"],
            "diagnostic_metrics": [
                "Campaign Recall", "Ad Exposure", "Message Clarity",
                "CTA Recall", "Relevance", "Enjoyment", "Branded Recall",
            ],
            "ad_creatives": [
                "YouTube 30s", "Instagram Static", "Display Banner",
                "Meta Video 15s", "Email Creative", "TikTok Short 10s", "Instagram Reel",
            ],
            "time_periods": ["Baseline", "Week 4", "Week 8", "Week 12", "Current"],
            "row_counts": {
                "campaigns":    len(campaigns),
                "segments":     len(segments),
                "summary_rows": len(summary),
            },
        }
    except Exception as exc:
        raise HTTPException(500, detail=str(exc))


# ── /suggestions ──────────────────────────────────────────────────────────────

@app.get("/suggestions", tags=["Analytics"])
async def get_suggestions():
    return {
        "suggestions": [
            "Which campaign should get more budget next quarter?",
            "Compare CA01 and CA03 on brand trust uplift",
            "Is Gen Z Digital Native improving week over week?",
            "How did Millennials respond to the Spring Brand Push?",
            "Break down everything about the Premium Product Reveal",
            "Which campaigns are missing their KPI targets?",
            "Which ad creative had the best recall across all campaigns?",
            "What is the current budget burn rate for CA04?",
            "Which campaign performed best for Gen Z?",
            "Are there any campaigns with high recall but low purchase intent?",
            "How is Summer Lifestyle Campaign trending?",
            "Compare ROI across all channels",
            "Which segment is responding best to the Value Seeker Promo?",
        ]
    }


# ── /export ───────────────────────────────────────────────────────────────────

@app.post("/export", tags=["Analytics"])
async def export_report(request: ExportRequest):
    if request.format == "docx":
        buffer   = generate_docx(request)
        filename = "campaign_report.docx"
        media    = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif request.format == "ppt":
        buffer   = generate_pptx(request)
        filename = "campaign_report.pptx"
        media    = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    else:
        raise HTTPException(400, detail=f"Unsupported format '{request.format}'. Use 'docx' or 'ppt'.")

    return StreamingResponse(
        buffer, media_type=media,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)