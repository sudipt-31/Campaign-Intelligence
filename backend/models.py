from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatMessage(BaseModel):
    role: str   # "user" | "assistant"
    content: str


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about campaign performance")
    session_id: Optional[str] = None
    chat_history: Optional[list[ChatMessage]] = Field(
        default=[],
        description="Prior turns for conversational memory (last N messages)"
    )


class TableData(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class QueryResponse(BaseModel):
    summary:         str
    rich_text:       Optional[str]                  = None
    chart:           Optional[list[dict[str, Any]]] = None
    chart_type:      Optional[str]                  = "bar"
    chart_title:     Optional[str]                  = None
    table_data:      Optional[TableData]            = None
    recommendations: Optional[list[str]]            = None
    agent_trace:     Optional[list[str]]             = None
    error:           Optional[str]                   = None


class HealthResponse(BaseModel):
    status:             str
    data_loaded:        bool
    campaigns_count:    int
    segments_available: list[str]