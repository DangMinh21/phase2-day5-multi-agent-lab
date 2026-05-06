from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import ResearchQuery, RouteName
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_workflow_runs_to_final_answer_offline() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain LangGraph tracing"))
    workflow = MultiAgentWorkflow(settings=Settings(_env_file=None, MAX_ITERATIONS=6))

    result = workflow.run(state)

    assert result.final_answer
    assert result.next_route == RouteName.DONE
    assert result.route_history == [
        RouteName.RESEARCHER,
        RouteName.ANALYST,
        RouteName.WRITER,
        RouteName.DONE,
    ]
    assert result.metrics["engine"] in {"langgraph", "local-loop"}
    assert result.completed_at is not None
    assert not result.errors


def test_workflow_serializes_result() -> None:
    state = ResearchState(request=ResearchQuery(query="Compare agent workflows"))
    workflow = MultiAgentWorkflow(settings=Settings(_env_file=None, MAX_ITERATIONS=6))

    result = workflow.run(state)

    assert result.model_dump_json()
    assert any(event["name"] == "workflow_completed" for event in result.trace)
