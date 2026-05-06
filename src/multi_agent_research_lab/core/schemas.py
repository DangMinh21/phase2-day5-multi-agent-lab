"""Public schemas exchanged between CLI, agents, and evaluators."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AgentName(StrEnum):
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    CRITIC = "critic"


class RouteName(StrEnum):
    SUPERVISOR = "supervisor"
    RESEARCHER = "researcher"
    ANALYST = "analyst"
    WRITER = "writer"
    CRITIC = "critic"
    DONE = "done"


class ResearchQuery(BaseModel):
    query: str = Field(..., min_length=5)
    max_sources: int = Field(default=5, ge=1, le=20)
    audience: str = "technical learners"


class UsageMetadata(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None


class AgentResult(BaseModel):
    agent: AgentName
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    usage: UsageMetadata = Field(default_factory=UsageMetadata)
    latency_seconds: float | None = None
    success: bool = True


class SourceDocument(BaseModel):
    title: str
    url: str | None = None
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class BenchmarkMetrics(BaseModel):
    run_name: str
    latency_seconds: float
    estimated_cost_usd: float | None = None
    quality_score: float | None = Field(default=None, ge=0, le=10)
    input_tokens: int | None = None
    output_tokens: int | None = None
    source_count: int = 0
    citation_coverage: float | None = Field(default=None, ge=0, le=1)
    failure_count: int = 0
    notes: str = ""
