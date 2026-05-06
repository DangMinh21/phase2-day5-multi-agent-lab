"""Writer agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, UsageMetadata
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.utils.timer import elapsed_timer


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer`."""

        with elapsed_timer() as elapsed:
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are the Writer agent. Produce a clear final answer for the target "
                    "audience. Use source numbers like [1] when making sourced claims. "
                    "Be transparent about limitations."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Audience: {state.request.audience}\n\n"
                    f"Research notes:\n{state.research_notes or 'No research notes.'}\n\n"
                    f"Analysis notes:\n{state.analysis_notes or 'No analysis notes.'}\n\n"
                    f"Sources:\n{self._format_source_list(state)}\n\n"
                    "Write the final answer with a short limitations section."
                ),
            )
            state.final_answer = llm_response.content

        state.add_trace_event(
            "agent_completed",
            {
                "agent": self.name,
                "llm_provider": llm_response.provider,
                "fallback_reason": llm_response.fallback_reason,
                "latency_seconds": elapsed(),
            },
        )
        state.add_agent_result(
            AgentResult(
                agent=AgentName.WRITER,
                content=state.final_answer,
                metadata={
                    "llm_provider": llm_response.provider,
                    "fallback_reason": llm_response.fallback_reason,
                },
                usage=UsageMetadata(
                    input_tokens=llm_response.input_tokens,
                    output_tokens=llm_response.output_tokens,
                    estimated_cost_usd=llm_response.cost_usd,
                ),
                latency_seconds=elapsed(),
            )
        )
        return state

    @staticmethod
    def _format_source_list(state: ResearchState) -> str:
        lines: list[str] = []
        for index, source in enumerate(state.sources, start=1):
            url = source.url or "local"
            lines.append(f"[{index}] {source.title} - {url}")
        return "\n".join(lines)
