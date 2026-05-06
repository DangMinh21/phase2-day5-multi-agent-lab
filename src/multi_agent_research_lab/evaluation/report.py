"""Benchmark report rendering."""

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    trace_paths: list[str] | None = None,
) -> str:
    """Render benchmark metrics to markdown."""

    lines = [
        "# Benchmark Report",
        "",
        "## Summary",
        "",
        "This report compares the single-agent baseline against the multi-agent workflow.",
        "Metrics are collected from runtime state, agent usage metadata, and trace events.",
        "",
        "## Metrics",
        "",
        (
            "| Run | Latency (s) | Cost (USD) | Input Tokens | Output Tokens | "
            "Sources | Citation Coverage | Failures | Quality | Notes |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "" if item.estimated_cost_usd is None else f"{item.estimated_cost_usd:.4f}"
        quality = "" if item.quality_score is None else f"{item.quality_score:.1f}"
        citation_coverage = (
            ""
            if item.citation_coverage is None
            else f"{item.citation_coverage * 100:.0f}%"
        )
        lines.append(
            f"| {item.run_name} | {item.latency_seconds:.2f} | "
            f"{cost} | {item.input_tokens or ''} | {item.output_tokens or ''} | "
            f"{item.source_count} | {citation_coverage} | {item.failure_count} | "
            f"{quality} | {item.notes} |"
        )
    lines.extend(
        [
            "",
            "## Trace Evidence",
            "",
        ]
    )
    if trace_paths:
        for path in trace_paths:
            lines.append(f"- Local trace artifact: `{path}`")
    else:
        lines.append("- Add LangSmith screenshot or trace URL here after the demo run.")
    lines.extend(
        [
            "",
            "## Qualitative Notes",
            "",
            "- Single-agent baseline is simpler and usually lower overhead.",
            "- Multi-agent workflow is easier to inspect because routing, sources, analysis, "
            "and writing are separated.",
            "- Multi-agent workflow is preferable when the task needs source collection, "
            "explicit reasoning handoff, and traceable quality review.",
            "",
            "## Failure Modes And Fixes",
            "",
            "| Failure Mode | Mitigation |",
            "|---|---|",
            "| Missing API keys | Hybrid mock fallback keeps CLI, tests, and demo runnable. |",
            "| Provider/search failure | Retry first, then fallback to local behavior. |",
            "| Infinite routing loop | Supervisor max-iteration guard and graph recursion limit. |",
            "| Weak citation coverage | Report metric highlights missing source references. |",
            "| LangSmith unavailable | Local JSON trace artifacts are always exported. |",
            "",
            "## Demo Evidence To Attach",
            "",
            "- LangSmith screenshot showing workflow and agent spans.",
            "- CLI pretty-mode screenshot with route timeline and metrics.",
            "- `reports/traces/*_multi_agent_trace.json` artifact.",
        ]
    )
    return "\n".join(lines) + "\n"
