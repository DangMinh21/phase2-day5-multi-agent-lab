"""Analyst agent skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, UsageMetadata
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.utils.timer import elapsed_timer


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        with elapsed_timer() as elapsed:
            llm_response = self.llm_client.complete(
                system_prompt=(
                    "You are the Analyst agent. Convert research notes into structured "
                    "insights, tradeoffs, and evidence limitations. Do not write final prose."
                ),
                user_prompt=(
                    f"Query: {state.request.query}\n"
                    f"Research notes:\n{state.research_notes or 'No research notes available.'}\n\n"
                    "Return: key claims, supporting evidence, tradeoffs, weak evidence, "
                    "and suggested answer structure."
                ),
            )
            state.analysis_notes = llm_response.content

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
                agent=AgentName.ANALYST,
                content=state.analysis_notes,
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
