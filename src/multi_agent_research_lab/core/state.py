"""Shared state for the multi-agent workflow."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field

from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    ResearchQuery,
    RouteName,
    SourceDocument,
)


class ResearchState(BaseModel):
    """Single source of truth passed through the workflow."""

    request: ResearchQuery
    iteration: int = 0
    next_route: RouteName = RouteName.SUPERVISOR
    route_history: list[RouteName] = Field(default_factory=list)

    sources: list[SourceDocument] = Field(default_factory=list)
    research_notes: str | None = None
    analysis_notes: str | None = None
    final_answer: str | None = None

    agent_results: list[AgentResult] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None

    def record_route(self, route: RouteName | str) -> None:
        next_route = RouteName(route)
        self.next_route = next_route
        self.route_history.append(next_route)
        self.iteration += 1

    def add_trace_event(self, name: str, payload: dict[str, Any]) -> None:
        self.trace.append(
            {
                "name": name,
                "payload": payload,
                "timestamp": datetime.now(UTC).isoformat(),
            }
        )

    def add_agent_result(self, result: AgentResult) -> None:
        self.agent_results.append(result)

    def add_error(self, message: str, agent: AgentName | str | None = None) -> None:
        prefix = f"{AgentName(agent).value}: " if agent is not None else ""
        error = f"{prefix}{message}"
        self.errors.append(error)
        self.add_trace_event(
            "error",
            {
                "agent": str(agent) if agent is not None else None,
                "message": message,
            },
        )

    def set_metric(self, name: str, value: Any) -> None:
        self.metrics[name] = value

    def mark_completed(self) -> None:
        self.completed_at = datetime.now(UTC)
        self.set_metric("duration_seconds", (self.completed_at - self.started_at).total_seconds())
