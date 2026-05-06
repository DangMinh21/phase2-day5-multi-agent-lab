"""Command-line entrypoint for the lab starter."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()
SUPPORTED_FORMATS = {"pretty", "json"}


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: pretty or json"),
    ] = "pretty",
) -> None:
    """Run a minimal single-agent baseline placeholder."""

    _init()
    _validate_output_format(output_format)
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)
    state.final_answer = (
        "Baseline skeleton response. TODO(student): replace this with a real single-agent "
        "implementation and record latency/cost/quality metrics."
    )
    state.mark_completed()
    if output_format == "json":
        console.print_json(state.model_dump_json())
    else:
        console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: pretty or json"),
    ] = "pretty",
) -> None:
    """Run the multi-agent workflow."""

    _init()
    _validate_output_format(output_format)
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    result = workflow.run(state)
    trace_path = _write_trace_artifact(result)
    result.set_metric("trace_path", str(trace_path))

    if output_format == "json":
        console.print_json(result.model_dump_json())
    else:
        _render_pretty_result(result, trace_path)


def _validate_output_format(output_format: str) -> None:
    if output_format not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise typer.BadParameter(f"format must be one of: {supported}")


def _write_trace_artifact(state: ResearchState) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    filename = f"traces/{timestamp}_multi_agent_trace.json"
    return LocalArtifactStore().write_text(filename, state.model_dump_json(indent=2))


def _render_pretty_result(state: ResearchState, trace_path: Path) -> None:
    console.print(Panel.fit(state.request.query, title="Research Query", style="cyan"))
    _render_route_timeline(state)
    _render_sources(state)
    _render_agent_results(state)
    console.print(Panel(state.final_answer or "No final answer produced.", title="Final Answer"))
    _render_metrics(state, trace_path)


def _render_route_timeline(state: ResearchState) -> None:
    table = Table(title="Route Timeline")
    table.add_column("#", justify="right")
    table.add_column("Route")
    for index, route in enumerate(state.route_history, start=1):
        table.add_row(str(index), route.value)
    console.print(table)


def _render_sources(state: ResearchState) -> None:
    table = Table(title="Sources")
    table.add_column("#", justify="right")
    table.add_column("Title")
    table.add_column("Provider")
    table.add_column("URL")
    for index, source in enumerate(state.sources, start=1):
        table.add_row(
            str(index),
            source.title,
            str(source.metadata.get("provider", "unknown")),
            source.url or "local",
        )
    console.print(table)


def _render_agent_results(state: ResearchState) -> None:
    table = Table(title="Agent Results")
    table.add_column("Agent")
    table.add_column("Provider")
    table.add_column("Tokens", justify="right")
    table.add_column("Latency", justify="right")
    for result in state.agent_results:
        provider = str(
            result.metadata.get("llm_provider")
            or result.metadata.get("next_route", "-")
        )
        tokens = _format_tokens(result.usage.input_tokens, result.usage.output_tokens)
        latency = "-" if result.latency_seconds is None else f"{result.latency_seconds:.3f}s"
        table.add_row(result.agent.value, provider, tokens, latency)
    console.print(table)


def _render_metrics(state: ResearchState, trace_path: Path) -> None:
    table = Table(title="Run Metrics")
    table.add_column("Metric")
    table.add_column("Value")
    table.add_row("Engine", str(state.metrics.get("engine", "unknown")))
    table.add_row("Iterations", str(state.iteration))
    table.add_row("Sources", str(len(state.sources)))
    table.add_row("Errors", str(len(state.errors)))
    table.add_row("Duration", f"{state.metrics.get('duration_seconds', 0):.3f}s")
    table.add_row("Trace artifact", str(trace_path))
    console.print(table)


def _format_tokens(input_tokens: int | None, output_tokens: int | None) -> str:
    if input_tokens is None and output_tokens is None:
        return "-"
    return f"{input_tokens or 0}/{output_tokens or 0}"


if __name__ == "__main__":
    app()
