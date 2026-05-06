# Design Notes

## Problem

Build a research assistant that can answer open-ended technical questions with source collection,
analysis, final synthesis, traceability, and benchmark evidence.

The system must support two modes:

- Single-agent baseline: one LLM call answers directly.
- Multi-agent workflow: Supervisor coordinates Researcher, Analyst, and Writer through shared state.

## Why Multi-Agent?

Single-agent mode is simpler and lower overhead, but it hides intermediate decisions. The multi-agent
workflow is useful here because the lab grades role clarity, handoff state, guardrails, benchmark
evidence, and trace explanation.

The multi-agent design makes each stage inspectable:

- Researcher owns sources and source-grounded notes.
- Analyst owns claims, tradeoffs, and limitations.
- Writer owns final synthesis and source references.
- Supervisor owns routing and stopping.

## Agent Roles

| Agent | Responsibility | Input | Output | Failure Mode |
|---|---|---|---|---|
| Supervisor | Decide next route and enforce max iterations | Full `ResearchState` | `next_route`, route history, trace event | Stops with error if max iterations are reached |
| Researcher | Collect sources and produce research notes | Query, audience, max sources | `sources`, `research_notes`, agent result | Falls back to local corpus if Tavily/search fails |
| Analyst | Turn research notes into structured insights | Query, sources, research notes | `analysis_notes`, agent result | Produces limitation-focused analysis from available notes |
| Writer | Produce final answer with source references | Query, sources, research notes, analysis notes | `final_answer`, agent result | Adds source references if model omits citation markers |
| Critic | Optional extension for validation | Final answer and sources | Review warnings | Not required for core workflow |

## Shared State

`ResearchState` is the single handoff object used by agents and workflow.

Important fields:

- `request`: user query, audience, and source budget.
- `next_route`: route selected by Supervisor.
- `route_history`: ordered route timeline for trace explanation.
- `sources`: normalized source documents.
- `research_notes`: Researcher output.
- `analysis_notes`: Analyst output.
- `final_answer`: Writer output.
- `agent_results`: per-agent outputs with metadata, usage, latency, and success flag.
- `trace`: local structured trace events.
- `errors`: recoverable and unrecoverable error notes.
- `metrics`: engine, source count, duration, trace artifact path, and benchmark metadata.
- `started_at` / `completed_at`: run timestamps.

## Routing Policy

```text
START -> supervisor

if final_answer exists:
    done
elif max_iterations reached:
    done with error
elif no sources or no research_notes:
    researcher
elif no analysis_notes:
    analyst
else:
    writer

researcher -> supervisor
analyst -> supervisor
writer -> supervisor
supervisor(done) -> END
```

The preferred engine is LangGraph. If `langgraph` is not installed, the workflow records a local
fallback trace event and runs the same route policy through a bounded local loop.

## Guardrails

- Max iterations: `MAX_ITERATIONS`, default `6`.
- Timeout: provider calls use `TIMEOUT_SECONDS`.
- Retry: LLM and search clients retry provider calls with `tenacity`.
- Fallback:
  - OpenAI -> deterministic mock LLM.
  - Tavily -> local mock corpus.
  - LangGraph unavailable -> local workflow loop.
- Validation:
  - Pydantic schemas for state and public data.
  - Empty prompts/search queries rejected.
  - Source count bounded by `ResearchQuery.max_sources`.
- Traceability:
  - Route decisions and agent completions are appended to `state.trace`.
  - Trace JSON artifacts are written under `reports/traces/`.
  - LangSmith environment variables are configured when `LANGSMITH_API_KEY` exists.

## Benchmark Plan

Configured queries live in `configs/lab_default.yaml`.

Metrics:

| Metric | Meaning |
|---|---|
| Latency | Wall-clock runtime |
| Cost | Provider usage estimate when available |
| Input/output tokens | Usage metadata from agent results |
| Source count | Number of retrieved/normalized sources |
| Citation coverage | Fraction of sources referenced in final answer |
| Failure count | Number of recorded state errors |
| Quality score | Optional manual peer-review score |

Expected outcome:

- Baseline should be faster and simpler.
- Multi-agent should have better traceability, source visibility, and handoff clarity.
- Offline fallback should preserve demo reliability even without API keys.

## Demo Evidence

For final report/demo:

- CLI pretty screenshot with route timeline and metrics.
- LangSmith trace screenshot if API key is configured.
- `reports/benchmark_report.md`.
- `reports/traces/*_multi_agent_trace.json`.
