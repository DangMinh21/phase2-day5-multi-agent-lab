"""Command-line entrypoint for the lab starter."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
import yaml  # type: ignore[import-untyped]
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import (
    AgentName,
    AgentResult,
    BenchmarkMetrics,
    ResearchQuery,
    UsageMetadata,
)
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_langsmith
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()
SUPPORTED_FORMATS = {"pretty", "json"}


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_langsmith(settings)


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
    state = _run_baseline(query)
    trace_path = _write_trace_artifact(state, run_kind="baseline")
    state.set_metric("trace_path", str(trace_path))
    if output_format == "json":
        console.print_json(state.model_dump_json())
    else:
        console.print(Panel.fit(state.final_answer or "", title="Single-Agent Baseline"))
        _render_metrics(state, trace_path)


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
    trace_path = _write_trace_artifact(result, run_kind="multi_agent")
    result.set_metric("trace_path", str(trace_path))

    if output_format == "json":
        console.print_json(result.model_dump_json())
    else:
        _render_pretty_result(result, trace_path)


@app.command()
def benchmark(
    output_format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: pretty or json"),
    ] = "pretty",
    config_path: Annotated[
        Path,
        typer.Option("--config", "-c", help="Benchmark YAML config"),
    ] = Path("configs/lab_default.yaml"),
) -> None:
    """Run baseline vs multi-agent benchmark and write a markdown report."""

    _init()
    _validate_output_format(output_format)
    queries = _load_benchmark_queries(config_path)
    metrics = []
    trace_paths: list[str] = []

    for index, query in enumerate(queries, start=1):
        baseline_state, baseline_metrics = run_benchmark(
            f"q{index}-baseline",
            query,
            _run_baseline,
        )
        baseline_trace_path = _write_trace_artifact(baseline_state, run_kind="baseline")
        baseline_state.set_metric("trace_path", str(baseline_trace_path))
        baseline_metrics.notes = f"{baseline_metrics.notes}; trace={baseline_trace_path}"
        multi_state, multi_metrics = run_benchmark(
            f"q{index}-multi-agent",
            query,
            lambda item: MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=item))),
        )
        multi_trace_path = _write_trace_artifact(multi_state, run_kind="multi_agent")
        multi_state.set_metric("trace_path", str(multi_trace_path))
        multi_metrics.notes = f"{multi_metrics.notes}; trace={multi_trace_path}"
        metrics.extend([baseline_metrics, multi_metrics])
        trace_paths.extend([str(baseline_trace_path), str(multi_trace_path)])

    report = render_markdown_report(metrics, trace_paths=trace_paths)
    report_path = LocalArtifactStore().write_text("benchmark_report.md", report)

    if output_format == "json":
        payload = {
            "report_path": str(report_path),
            "trace_paths": trace_paths,
            "metrics": [item.model_dump(mode="json") for item in metrics],
        }
        console.print_json(data=payload)
    else:
        _render_benchmark_summary(metrics, report_path)


def _validate_output_format(output_format: str) -> None:
    if output_format not in SUPPORTED_FORMATS:
        supported = ", ".join(sorted(SUPPORTED_FORMATS))
        raise typer.BadParameter(f"format must be one of: {supported}")


def _write_trace_artifact(state: ResearchState, run_kind: str) -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    filename = f"traces/{timestamp}_{run_kind}_trace.json"
    return LocalArtifactStore().write_text(filename, state.model_dump_json(indent=2))


def _run_baseline(query: str) -> ResearchState:
    state = ResearchState(request=ResearchQuery(query=query))
    state.add_trace_event("baseline_started", {"engine": "single-agent"})
    llm_response = LLMClient().complete(
        system_prompt=(
            "You are a single-agent research assistant. Answer directly and mention "
            "limitations when evidence is incomplete."
        ),
        user_prompt=f"Query: {query}\nWrite a concise research answer.",
    )
    state.final_answer = llm_response.content
    state.add_agent_result(
        AgentResult(
            agent=AgentName.WRITER,
            content=llm_response.content,
            metadata={"mode": "single-agent", "llm_provider": llm_response.provider},
            usage=UsageMetadata(
                input_tokens=llm_response.input_tokens,
                output_tokens=llm_response.output_tokens,
                estimated_cost_usd=llm_response.cost_usd,
            ),
        )
    )
    state.set_metric("engine", "single-agent")
    state.mark_completed()
    state.add_trace_event(
        "baseline_completed",
        {
            "engine": "single-agent",
            "llm_provider": llm_response.provider,
            "error_count": len(state.errors),
        },
    )
    return state


def _load_benchmark_queries(config_path: Path) -> list[str]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    queries = config.get("benchmark", {}).get("queries", [])
    if not isinstance(queries, list) or not all(isinstance(item, str) for item in queries):
        raise typer.BadParameter("benchmark.queries must be a list of strings")
    if not queries:
        raise typer.BadParameter("benchmark.queries must not be empty")
    return queries


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


def _render_benchmark_summary(metrics: list[BenchmarkMetrics], report_path: Path) -> None:
    table = Table(title="Benchmark Summary")
    table.add_column("Run")
    table.add_column("Latency", justify="right")
    table.add_column("Sources", justify="right")
    table.add_column("Citation", justify="right")
    table.add_column("Failures", justify="right")
    for metric in metrics:
        citation = (
            "-"
            if metric.citation_coverage is None
            else f"{metric.citation_coverage * 100:.0f}%"
        )
        table.add_row(
            metric.run_name,
            f"{metric.latency_seconds:.2f}s",
            str(metric.source_count),
            citation,
            str(metric.failure_count),
        )
    console.print(table)
    console.print(Panel.fit(str(report_path), title="Benchmark Report"))


def _format_tokens(input_tokens: int | None, output_tokens: int | None) -> str:
    if input_tokens is None and output_tokens is None:
        return "-"
    return f"{input_tokens or 0}/{output_tokens or 0}"


if __name__ == "__main__":
    app()
