"""
main.py — FastAPI entry point for the AI Campaign Intelligence Agent.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models import QueryRequest, QueryResponse, HealthResponse
from service import run_query, get_health_info
from data_loader import get_data_summary

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Startup] Verifying database connection...")
    get_data_summary()          # will raise if DB missing
    print("[Startup] au_topline.db loaded OK.")
    yield


app = FastAPI(
    title="AI Campaign Intelligence Agent",
    description="Conversational AI over the AU Topline campaign database.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    info = get_health_info()
    if info["status"] != "ok":
        raise HTTPException(503, detail=info.get("error", "DB unavailable"))
    return HealthResponse(**info)


@app.post("/query", response_model=QueryResponse, tags=["Analytics"])
async def query_campaigns(request: QueryRequest):
    """Submit a natural-language question about campaign performance."""
    if not request.question.strip():
        raise HTTPException(400, detail="Question cannot be empty.")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(503, detail="OPENAI_API_KEY not set.")
    history = [m.model_dump() for m in (request.chat_history or [])]
    return run_query(request.question, chat_history=history)


@app.get("/dataset/info", tags=["Data"])
async def dataset_info():
    """Returns metadata about the loaded database."""
    try:
        s = get_data_summary()
        return {
            "campaigns":          s["campaigns"],
            "campaign_codes":     s["campaign_codes"],
            "segments":           s["segments"],
            "kpi_metrics":        s["kpi_metrics"],
            "diagnostic_metrics": s["diagnostic_metrics"],
            "ad_creatives":       s["ad_creatives"],
            "time_periods":       s["time_periods"],
            "row_counts":         s["row_counts"],
        }
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@app.get("/suggestions", tags=["Analytics"])
async def get_suggestions():
    """Returns example questions grounded in the real campaigns in the DB."""
    return {
        "suggestions": [
            "Which campaign had the highest brand uplift overall?",
            "How did Travel like Jennie perform for Gen Z vs Mass Consumers?",
            "Compare preference uplift across all campaigns",
            "Which campaign metrics are underperforming (negative uplift)?",
            "Show Campaign Recall trend over time for Travel like Jennie",
            "Are any campaigns beating the norm benchmark?",
            "Which ad creative had the best recall for MasterCard?",
            "Break down ING | Tripadvisor diagnostics — XB Travelers vs ING Cardholders",
            "How is Commbank AFC Cup performing on brand awareness?",
            "Which segment responded best to Travel like Jennie?",
        ]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)