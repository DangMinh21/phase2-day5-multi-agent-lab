"""Supervisor / router skeleton."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, RouteName
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route."""

        if state.iteration >= self.settings.max_iterations:
            route = RouteName.DONE
            state.add_error("max iterations reached", agent=AgentName.SUPERVISOR)
        elif state.final_answer:
            route = RouteName.DONE
        elif not state.sources or not state.research_notes:
            route = RouteName.RESEARCHER
        elif not state.analysis_notes:
            route = RouteName.ANALYST
        else:
            route = RouteName.WRITER

        state.record_route(route)
        state.add_trace_event(
            "route_decision",
            {
                "agent": self.name,
                "next_route": route.value,
                "iteration": state.iteration,
                "has_sources": bool(state.sources),
                "has_research_notes": bool(state.research_notes),
                "has_analysis_notes": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
            },
        )
        state.add_agent_result(
            AgentResult(
                agent=AgentName.SUPERVISOR,
                content=f"Next route: {route.value}",
                metadata={"next_route": route.value, "iteration": state.iteration},
            )
        )
        return state
