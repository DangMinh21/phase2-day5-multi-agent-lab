import pytest

from multi_agent_research_lab.core.config import Settings
from multi_agent_research_lab.core.errors import ValidationError
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient


def test_llm_client_uses_deterministic_mock_without_api_key() -> None:
    settings = Settings(_env_file=None, OPENAI_API_KEY=None)
    response = LLMClient(settings=settings).complete(
        system_prompt="You are a careful research assistant.",
        user_prompt="Explain multi-agent research systems.",
    )

    assert response.provider == "mock"
    assert response.model == "deterministic-mock"
    assert response.cost_usd == 0.0
    assert response.input_tokens is not None
    assert response.output_tokens is not None
    assert "Mock LLM response" in response.content


def test_llm_client_rejects_empty_prompts() -> None:
    settings = Settings(_env_file=None, OPENAI_API_KEY=None)
    with pytest.raises(ValidationError):
        LLMClient(settings=settings).complete("", "Explain multi-agent systems.")


def test_search_client_uses_local_mock_without_api_key() -> None:
    settings = Settings(_env_file=None, TAVILY_API_KEY=None)
    response = SearchClient(settings=settings).search_with_metadata(
        "LangGraph tracing multi-agent workflow",
        max_results=3,
    )

    assert response.provider == "local-mock"
    assert response.fallback_reason
    assert 1 <= len(response.sources) <= 3
    assert all(source.title and source.snippet for source in response.sources)
    assert all(source.metadata["provider"] == "local-mock" for source in response.sources)


def test_search_client_rejects_invalid_limits() -> None:
    settings = Settings(_env_file=None, TAVILY_API_KEY=None)
    with pytest.raises(ValueError):
        SearchClient(settings=settings).search("multi-agent", max_results=0)
