"""LangGraph workflow skeleton."""

from typing import Any

from multi_agent_research_lab.agents import (
    AnalystAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError
from multi_agent_research_lab.core.schemas import AgentName, RouteName
from multi_agent_research_lab.core.state import ResearchState


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph.

    Keep orchestration here; keep agent internals in `agents/`.
    """

    def __init__(
        self,
        settings: Settings | None = None,
        supervisor: SupervisorAgent | None = None,
        researcher: ResearcherAgent | None = None,
        analyst: AnalystAgent | None = None,
        writer: WriterAgent | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.supervisor = supervisor or SupervisorAgent(settings=self.settings)
        self.researcher = researcher or ResearcherAgent()
        self.analyst = analyst or AnalystAgent()
        self.writer = writer or WriterAgent()

    def build(self) -> Any:
        """Create a LangGraph graph.

        LangGraph is used when installed. The project keeps a local fallback runner in
        `run` so tests and offline demos still work before optional dependencies are installed.
        """

        try:
            from langgraph.graph import END, StateGraph
        except ImportError as exc:
            raise AgentExecutionError(
                "LangGraph is not installed. Run `make install` for the full graph engine."
            ) from exc

        graph = StateGraph(ResearchState)
        graph.add_node(RouteName.SUPERVISOR.value, self._supervisor_node)
        graph.add_node(RouteName.RESEARCHER.value, self._researcher_node)
        graph.add_node(RouteName.ANALYST.value, self._analyst_node)
        graph.add_node(RouteName.WRITER.value, self._writer_node)
        graph.set_entry_point(RouteName.SUPERVISOR.value)
        graph.add_conditional_edges(
            RouteName.SUPERVISOR.value,
            self._route_after_supervisor,
            {
                RouteName.RESEARCHER.value: RouteName.RESEARCHER.value,
                RouteName.ANALYST.value: RouteName.ANALYST.value,
                RouteName.WRITER.value: RouteName.WRITER.value,
                RouteName.DONE.value: END,
            },
        )
        graph.add_edge(RouteName.RESEARCHER.value, RouteName.SUPERVISOR.value)
        graph.add_edge(RouteName.ANALYST.value, RouteName.SUPERVISOR.value)
        graph.add_edge(RouteName.WRITER.value, RouteName.SUPERVISOR.value)
        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""

        state.add_trace_event("workflow_started", {"engine": "langgraph"})
        try:
            graph = self.build()
        except AgentExecutionError as exc:
            state.add_trace_event(
                "workflow_engine_fallback",
                {"engine": "local-loop", "reason": str(exc)},
            )
            result = self._run_local_loop(state)
        else:
            raw_result = graph.invoke(
                state,
                config={"recursion_limit": self.settings.max_iterations * 3},
            )
            result = self._coerce_state(raw_result)
            result.set_metric("engine", "langgraph")

        result.mark_completed()
        result.add_trace_event(
            "workflow_completed",
            {
                "engine": result.metrics.get("engine", "unknown"),
                "iterations": result.iteration,
                "route_history": [route.value for route in result.route_history],
                "error_count": len(result.errors),
            },
        )
        return result

    def _run_local_loop(self, state: ResearchState) -> ResearchState:
        state.set_metric("engine", "local-loop")
        while state.iteration < self.settings.max_iterations:
            self._supervisor_node(state)
            if state.next_route == RouteName.DONE:
                return state
            if state.next_route == RouteName.RESEARCHER:
                self._researcher_node(state)
            elif state.next_route == RouteName.ANALYST:
                self._analyst_node(state)
            elif state.next_route == RouteName.WRITER:
                self._writer_node(state)
            else:
                state.add_error(
                    f"unsupported route: {state.next_route}",
                    agent=AgentName.SUPERVISOR,
                )
                return state

        state.add_error("workflow local loop reached max iterations", agent=AgentName.SUPERVISOR)
        state.record_route(RouteName.DONE)
        return state

    def _supervisor_node(self, state: ResearchState) -> ResearchState:
        return self.supervisor.run(self._coerce_state(state))

    def _researcher_node(self, state: ResearchState) -> ResearchState:
        return self.researcher.run(self._coerce_state(state))

    def _analyst_node(self, state: ResearchState) -> ResearchState:
        return self.analyst.run(self._coerce_state(state))

    def _writer_node(self, state: ResearchState) -> ResearchState:
        return self.writer.run(self._coerce_state(state))

    @staticmethod
    def _route_after_supervisor(state: ResearchState) -> str:
        return MultiAgentWorkflow._coerce_state(state).next_route.value

    @staticmethod
    def _coerce_state(raw_state: Any) -> ResearchState:
        if isinstance(raw_state, ResearchState):
            return raw_state
        if isinstance(raw_state, dict):
            return ResearchState.model_validate(raw_state)
        raise TypeError(f"Unsupported workflow state type: {type(raw_state)!r}")
