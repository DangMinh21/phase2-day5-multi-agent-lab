"""Search client abstraction for ResearcherAgent."""

import json
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import Request, urlopen

from tenacity import RetryError, Retrying, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import SourceDocument


@dataclass(frozen=True)
class SearchResponse:
    sources: list[SourceDocument]
    provider: str
    fallback_reason: str | None = None


class SearchClient:
    """Provider-agnostic search client with local corpus fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query.

        Compatibility wrapper used by agents. For provider metadata, call `search_with_metadata`.
        """

        return self.search_with_metadata(query, max_results).sources

    def search_with_metadata(self, query: str, max_results: int = 5) -> SearchResponse:
        if not query or not query.strip():
            raise ValueError("query must not be empty")
        if max_results < 1:
            raise ValueError("max_results must be at least 1")

        if not self.settings.tavily_api_key:
            return self._mock_search(query, max_results, "TAVILY_API_KEY is not set")

        try:
            return SearchResponse(
                sources=self._tavily_search_with_retry(query, max_results),
                provider="tavily",
            )
        except Exception as exc:
            return self._mock_search(query, max_results, f"Tavily fallback: {exc}")

    def _tavily_search_with_retry(self, query: str, max_results: int) -> list[SourceDocument]:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
                reraise=True,
            ):
                with attempt:
                    return self._tavily_search(query, max_results)
        except RetryError as exc:
            raise RuntimeError(f"Search retry exhausted: {exc}") from exc

        raise RuntimeError("Search retry exhausted without results")

    def _tavily_search(self, query: str, max_results: int) -> list[SourceDocument]:
        payload = json.dumps(
            {
                "api_key": self.settings.tavily_api_key,
                "query": query,
                "max_results": max_results,
                "search_depth": "basic",
                "include_answer": False,
            }
        ).encode("utf-8")
        request = Request(
            "https://api.tavily.com/search",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.settings.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except URLError as exc:
            raise RuntimeError(f"Tavily request failed: {exc}") from exc

        data = json.loads(raw)
        results = data.get("results", [])
        if not isinstance(results, list):
            raise RuntimeError("Tavily response did not include a results list")

        sources: list[SourceDocument] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or "").strip()
            snippet = str(item.get("content") or item.get("snippet") or "").strip()
            url = str(item.get("url") or "").strip() or None
            if not title or not snippet:
                continue
            sources.append(
                SourceDocument(
                    title=title,
                    url=url,
                    snippet=snippet,
                    metadata={"provider": "tavily", "score": item.get("score")},
                )
            )

        return self._dedupe(sources)[:max_results]

    def _mock_search(self, query: str, max_results: int, fallback_reason: str) -> SearchResponse:
        query_terms = {term.lower() for term in query.split() if len(term) > 3}
        ranked = sorted(
            self._local_corpus(),
            key=lambda source: self._score_source(source, query_terms),
            reverse=True,
        )
        sources = self._dedupe(ranked)[:max_results]
        if not sources:
            sources = self._local_corpus()[:1]
        return SearchResponse(
            sources=[
                source.model_copy(
                    update={
                        "metadata": {
                            **source.metadata,
                            "provider": "local-mock",
                            "fallback_reason": fallback_reason,
                        }
                    }
                )
                for source in sources
            ],
            provider="local-mock",
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _local_corpus() -> list[SourceDocument]:
        return [
            SourceDocument(
                title="Anthropic: Building Effective Agents",
                url="https://www.anthropic.com/engineering/building-effective-agents",
                snippet=(
                    "Agent systems work best when workflows are simple, observable, and "
                    "built from composable patterns such as routing, parallelization, "
                    "and evaluation."
                ),
                metadata={"topic": "agent design"},
            ),
            SourceDocument(
                title="LangGraph Concepts",
                url="https://langchain-ai.github.io/langgraph/concepts/",
                snippet=(
                    "LangGraph models agent applications as stateful graphs with nodes, edges, "
                    "conditional routing, persistence, and controllable execution."
                ),
                metadata={"topic": "workflow orchestration"},
            ),
            SourceDocument(
                title="LangSmith Tracing Documentation",
                url="https://docs.smith.langchain.com/",
                snippet=(
                    "LangSmith helps developers trace, debug, evaluate, and monitor LLM "
                    "applications across development and production workflows."
                ),
                metadata={"topic": "observability"},
            ),
            SourceDocument(
                title="OpenAI Agents SDK Orchestration",
                url="https://developers.openai.com/",
                snippet=(
                    "Agent orchestration benefits from explicit handoffs, tool boundaries, "
                    "guardrails, and traceable execution paths."
                ),
                metadata={"topic": "agent orchestration"},
            ),
            SourceDocument(
                title="Lab Rubric: Multi-Agent Research System",
                url=None,
                snippet=(
                    "The lab rewards role clarity, shared state design, failure guards, "
                    "benchmarking, and trace explanations."
                ),
                metadata={"topic": "grading rubric"},
            ),
        ]

    @staticmethod
    def _score_source(source: SourceDocument, query_terms: set[str]) -> int:
        haystack = f"{source.title} {source.snippet} {source.metadata}".lower()
        return sum(1 for term in query_terms if term in haystack)

    @staticmethod
    def _dedupe(sources: list[SourceDocument]) -> list[SourceDocument]:
        seen: set[str] = set()
        unique: list[SourceDocument] = []
        for source in sources:
            key = source.url or source.title.lower()
            if key in seen:
                continue
            seen.add(key)
            unique.append(source)
        return unique
