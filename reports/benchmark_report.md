# Benchmark Report

## Summary

This report compares the single-agent baseline against the multi-agent workflow.
Metrics are collected from runtime state, agent usage metadata, and trace events.

## Metrics

| Run | Latency (s) | Cost (USD) | Input Tokens | Output Tokens | Sources | Citation Coverage | Failures | Quality | Notes |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| q1-baseline | 0.56 | 0.0000 | 29 | 60 | 0 |  | 0 |  | engine=single-agent; iterations=0; errors=0; trace=reports/traces/20260506T054535692423Z_baseline_trace.json |
| q1-multi-agent | 2.43 | 0.0000 | 464 | 189 | 5 | 100% | 0 |  | engine=local-loop; iterations=4; errors=0; trace=reports/traces/20260506T054538118396Z_multi_agent_trace.json |
| q2-baseline | 0.30 | 0.0000 | 29 | 60 | 0 |  | 0 |  | engine=single-agent; iterations=0; errors=0; trace=reports/traces/20260506T054538417395Z_baseline_trace.json |
| q2-multi-agent | 2.45 | 0.0000 | 462 | 188 | 5 | 100% | 0 |  | engine=local-loop; iterations=4; errors=0; trace=reports/traces/20260506T054540870149Z_multi_agent_trace.json |
| q3-baseline | 0.31 | 0.0000 | 27 | 58 | 0 |  | 0 |  | engine=single-agent; iterations=0; errors=0; trace=reports/traces/20260506T054541183850Z_baseline_trace.json |
| q3-multi-agent | 2.45 | 0.0000 | 450 | 182 | 5 | 100% | 0 |  | engine=local-loop; iterations=4; errors=0; trace=reports/traces/20260506T054543637621Z_multi_agent_trace.json |

## Trace Evidence

- Local trace artifact: `reports/traces/20260506T054535692423Z_baseline_trace.json`
- Local trace artifact: `reports/traces/20260506T054538118396Z_multi_agent_trace.json`
- Local trace artifact: `reports/traces/20260506T054538417395Z_baseline_trace.json`
- Local trace artifact: `reports/traces/20260506T054540870149Z_multi_agent_trace.json`
- Local trace artifact: `reports/traces/20260506T054541183850Z_baseline_trace.json`
- Local trace artifact: `reports/traces/20260506T054543637621Z_multi_agent_trace.json`

## Qualitative Notes

- Single-agent baseline is simpler and usually lower overhead.
- Multi-agent workflow is easier to inspect because routing, sources, analysis, and writing are separated.
- Multi-agent workflow is preferable when the task needs source collection, explicit reasoning handoff, and traceable quality review.

## Failure Modes And Fixes

| Failure Mode | Mitigation |
|---|---|
| Missing API keys | Hybrid mock fallback keeps CLI, tests, and demo runnable. |
| Provider/search failure | Retry first, then fallback to local behavior. |
| Infinite routing loop | Supervisor max-iteration guard and graph recursion limit. |
| Weak citation coverage | Report metric highlights missing source references. |
| LangSmith unavailable | Local JSON trace artifacts are always exported. |

## Demo Evidence To Attach

- LangSmith screenshot showing workflow and agent spans.
- CLI pretty-mode screenshot with route timeline and metrics.
- `reports/traces/*_baseline_trace.json` artifacts.
- `reports/traces/*_multi_agent_trace.json` artifacts.
