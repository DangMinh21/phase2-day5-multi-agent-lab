"""Benchmark skeleton for single-agent vs multi-agent."""

from collections.abc import Callable, Iterable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics, UsageMetadata
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run one benchmark case and collect operational metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started
    metrics = metrics_from_state(run_name, state, latency)
    return state, metrics


def metrics_from_state(
    run_name: str,
    state: ResearchState,
    latency_seconds: float,
) -> BenchmarkMetrics:
    """Build benchmark metrics from a completed state."""

    usage = _sum_usage(result.usage for result in state.agent_results)
    estimated_cost = usage.estimated_cost_usd
    citation_coverage = _estimate_citation_coverage(state)
    notes = (
        f"engine={state.metrics.get('engine', 'baseline')}; "
        f"iterations={state.iteration}; errors={len(state.errors)}"
    )
    return BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency_seconds,
        estimated_cost_usd=estimated_cost,
        input_tokens=usage.input_tokens,
        output_tokens=usage.output_tokens,
        source_count=len(state.sources),
        citation_coverage=citation_coverage,
        failure_count=len(state.errors),
        notes=notes,
    )


def _sum_usage(usages: Iterable[UsageMetadata]) -> UsageMetadata:
    input_tokens = 0
    output_tokens = 0
    total_cost = 0.0
    saw_tokens = False
    saw_cost = False
    for usage in usages:
        if usage.input_tokens is not None:
            input_tokens += usage.input_tokens
            saw_tokens = True
        if usage.output_tokens is not None:
            output_tokens += usage.output_tokens
            saw_tokens = True
        if usage.estimated_cost_usd is not None:
            total_cost += usage.estimated_cost_usd
            saw_cost = True
    return UsageMetadata(
        input_tokens=input_tokens if saw_tokens else None,
        output_tokens=output_tokens if saw_tokens else None,
        estimated_cost_usd=total_cost if saw_cost else None,
    )


def _estimate_citation_coverage(state: ResearchState) -> float | None:
    if not state.sources:
        return None
    answer = state.final_answer or ""
    cited_count = sum(1 for index in range(1, len(state.sources) + 1) if f"[{index}]" in answer)
    return cited_count / len(state.sources)
