"""Researcher agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, UsageMetadata
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient
from multi_agent_research_lab.utils.timer import elapsed_timer


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(
        self,
        search_client: SearchClient | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.search_client = search_client or SearchClient()
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        with elapsed_timer() as elapsed:
            search_response = self.search_client.search_with_metadata(
                state.request.query,
                max_results=state.request.max_sources,
            )
            state.sources = search_response.sources
            source_text = self._format_sources(state)
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are the Researcher agent. Extract concise, source-grounded notes. "
                    "Do not write the final answer."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Sources:\n{source_text}\n\n"
                    "Write research notes with source numbers for later synthesis."
                ),
            )
            state.research_notes = llm_response.content

        state.add_trace_event(
            "agent_completed",
            {
                "agent": self.name,
                "source_count": len(state.sources),
                "search_provider": search_response.provider,
                "llm_provider": llm_response.provider,
                "fallback_reason": search_response.fallback_reason or llm_response.fallback_reason,
                "latency_seconds": elapsed(),
            },
        )
        state.add_agent_result(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={
                    "source_count": len(state.sources),
                    "search_provider": search_response.provider,
                    "llm_provider": llm_response.provider,
                    "fallback_reason": (
                        search_response.fallback_reason or llm_response.fallback_reason
                    ),
                },
                usage=UsageMetadata(
                    input_tokens=llm_response.input_tokens,
                    output_tokens=llm_response.output_tokens,
                    estimated_cost_usd=llm_response.cost_usd,
                ),
                latency_seconds=elapsed(),
            )
        )
        state.set_metric("source_count", len(state.sources))
        return state

    @staticmethod
    def _format_sources(state: ResearchState) -> str:
        lines: list[str] = []
        for index, source in enumerate(state.sources, start=1):
            url = source.url or "local"
            lines.append(f"[{index}] {source.title} ({url})\n{source.snippet}")
        return "\n\n".join(lines)
