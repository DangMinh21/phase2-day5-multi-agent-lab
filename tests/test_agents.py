from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.schemas import AgentName, ResearchQuery, RouteName
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


def _offline_llm() -> LLMClient:
    return LLMClient(settings=Settings(_env_file=None, OPENAI_API_KEY=None))


def _offline_search() -> SearchClient:
    return SearchClient(settings=Settings(_env_file=None, TAVILY_API_KEY=None))


def test_supervisor_routes_by_missing_state() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    supervisor = SupervisorAgent(settings=Settings(_env_file=None, MAX_ITERATIONS=6))

    supervisor.run(state)
    assert state.next_route == RouteName.RESEARCHER

    state.sources = _offline_search().search("multi-agent systems", max_results=1)
    state.research_notes = "Research notes"
    supervisor.run(state)
    assert state.next_route == RouteName.ANALYST

    state.analysis_notes = "Analysis notes"
    supervisor.run(state)
    assert state.next_route == RouteName.WRITER

    state.final_answer = "Final answer"
    supervisor.run(state)
    assert state.next_route == RouteName.DONE


def test_supervisor_stops_at_max_iterations() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.iteration = 1
    supervisor = SupervisorAgent(settings=Settings(_env_file=None, MAX_ITERATIONS=1))

    supervisor.run(state)

    assert state.next_route == RouteName.DONE
    assert state.errors == ["supervisor: max iterations reached"]


def test_researcher_populates_sources_notes_and_result() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain LangGraph tracing"))
    agent = ResearcherAgent(search_client=_offline_search(), llm_client=_offline_llm())

    agent.run(state)

    assert state.sources
    assert state.research_notes
    assert state.metrics["source_count"] == len(state.sources)
    assert state.agent_results[-1].agent == AgentName.RESEARCHER


def test_analyst_populates_analysis_notes_and_result() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Explain LangGraph tracing"),
        research_notes="Research notes with sources [1].",
    )
    agent = AnalystAgent(llm_client=_offline_llm())

    agent.run(state)

    assert state.analysis_notes
    assert state.agent_results[-1].agent == AgentName.ANALYST


def test_writer_populates_final_answer_and_result() -> None:
    state = ResearchState(
        request=ResearchQuery(query="Explain LangGraph tracing"),
        sources=_offline_search().search("LangGraph tracing", max_results=2),
        research_notes="Research notes with sources [1].",
        analysis_notes="Analysis notes.",
    )
    agent = WriterAgent(llm_client=_offline_llm())

    agent.run(state)

    assert state.final_answer
    assert state.agent_results[-1].agent == AgentName.WRITER
