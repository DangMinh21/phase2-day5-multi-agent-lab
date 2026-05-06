from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery, RouteName
from multi_agent_research_lab.core.state import ResearchState


def test_state_records_route_and_trace() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.record_route("researcher")
    state.add_trace_event("route", {"next": "researcher"})
    assert state.iteration == 1
    assert state.next_route == RouteName.RESEARCHER
    assert state.route_history == [RouteName.RESEARCHER]
    assert state.trace[0]["name"] == "route"


def test_state_records_results_errors_metrics_and_completion() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.add_agent_result(AgentResult(agent=AgentName.RESEARCHER, content="notes"))
    state.add_error("search fallback used", agent=AgentName.RESEARCHER)
    state.set_metric("source_count", 3)
    state.mark_completed()

    assert state.agent_results[0].agent == AgentName.RESEARCHER
    assert state.errors == ["researcher: search fallback used"]
    assert state.metrics["source_count"] == 3
    assert state.metrics["duration_seconds"] >= 0
    assert state.completed_at is not None
    assert state.model_dump_json()
