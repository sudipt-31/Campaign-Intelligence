"""
models.py -- v2
Pydantic models for FastAPI.
New: reasoning_trace, data_quality fields in QueryResponse.
"""
from __future__ import annotations
from typing import Any, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class TableData(BaseModel):
    columns: list[str]
    rows: list[list[Any]]


class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about campaign performance")
    session_id: Optional[str] = Field(default=None)
    chat_history: Optional[list[ChatMessage]] = Field(default=[])


class ExportRequest(BaseModel):
    format: str
    summary: str
    rich_text: Optional[str] = None
    chart_data: Optional[list[dict[str, Any]]] = None
    chart_title: Optional[str] = None
    table_data: Optional[TableData] = None


class QueryResponse(BaseModel):
    summary:          str
    rich_text:        Optional[str]                  = None
    chart:            Optional[list[dict[str, Any]]] = None
    chart_type:       Optional[str]                  = "bar"
    chart_title:      Optional[str]                  = None
    table_data:       Optional[TableData]            = None
    recommendations:  Optional[list[str]]            = None
    agent_trace:      Optional[list[str]]            = None
    reasoning_trace:  Optional[list[str]]            = None   # NEW
    confidence_score: Optional[int]                  = None
    data_quality:     Optional[dict]                 = None   # NEW: exposes gate result
    critic_approved:  Optional[bool]                 = None   # NEW: was critic satisfied
    error:            Optional[str]                  = None


class HealthResponse(BaseModel):
    status:             str
    data_loaded:        bool
    campaigns_count:    int
    segments_available: list[str]
