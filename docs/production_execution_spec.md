# Production Execution Spec

Goal: turn this starter skeleton into a strong lab submission that is easy to demo, easy to review, and aligned with the full peer-review rubric.

Chosen direction:

- LLM provider: hybrid OpenAI + deterministic mock fallback.
- Search provider: hybrid Tavily/web search + local mock corpus fallback.
- Workflow engine: LangGraph.
- CLI demo: both rich pretty output and JSON output.
- Observability: LangSmith tracing, plus local JSON trace artifacts.
- Scope: balanced. Build a robust core first, then add showcase polish where it directly improves grading.

## Success Criteria

The final submission should satisfy all 10 rubric points:

| Rubric Area | Target Evidence |
|---|---|
| Role clarity | Each agent has a distinct prompt, input contract, output contract, and trace span. |
| State design | `ResearchState` captures sources, notes, results, route history, errors, metrics, and trace events. |
| Failure guard | Max iterations, timeout, retry, fallback, validation, and graceful error reporting are implemented. |
| Benchmark | Baseline vs multi-agent metrics are rendered into `reports/benchmark_report.md`. |
| Trace explanation | LangSmith trace and local trace file show who did what, duration, cost/tokens, and failures. |

## Target Architecture

```text
CLI
 |
 |-- baseline runner
 |     `-- Single agent prompt via LLMClient
 |
 `-- multi-agent runner
       `-- LangGraph workflow
             |
             |-- SupervisorAgent: route and stop decisions
             |-- ResearcherAgent: search, source filtering, research notes
             |-- AnalystAgent: claims, tradeoffs, weak-evidence flags
             |-- WriterAgent: final answer with source references
             `-- Optional CriticAgent: validation pass if time allows

Services
 |
 |-- LLMClient: OpenAI first, mock fallback, retry, timeout, token/cost metadata
 |-- SearchClient: Tavily first, local mock fallback
 `-- LocalArtifactStore: reports, traces, benchmark outputs

Observability
 |
 |-- LangSmith trace spans
 `-- Local trace events in ResearchState and JSON artifact
```

## Implementation Milestones

### Milestone 1: Core Contracts

Files:

- `src/multi_agent_research_lab/core/schemas.py`
- `src/multi_agent_research_lab/core/state.py`
- `src/multi_agent_research_lab/core/config.py`

Tasks:

- Add route enum or literal values: `researcher`, `analyst`, `writer`, `critic`, `done`.
- Extend `AgentResult` metadata to consistently carry latency, token usage, cost, source count, and validation status.
- Extend `ResearchState` with:
  - `next_route`
  - `metrics`
  - `started_at` / `completed_at` or equivalent timing metadata
  - helper methods for appending errors, agent results, and trace events.
- Keep all state serializable with Pydantic.

Acceptance checks:

- State can be dumped to JSON.
- Route history and trace events are readable after a run.
- Tests cover route recording, error recording, and result recording.

### Milestone 2: Hybrid LLM Client

Files:

- `src/multi_agent_research_lab/services/llm_client.py`
- `src/multi_agent_research_lab/core/config.py`
- tests for LLM mock behavior.

Tasks:

- Implement `LLMClient.complete(system_prompt, user_prompt)`.
- If `OPENAI_API_KEY` exists, use OpenAI.
- If OpenAI fails or key is missing, use deterministic mock fallback.
- Add retry with `tenacity`.
- Add timeout from settings.
- Return `LLMResponse` with content and best-effort token/cost metadata.
- Never let agents import provider SDKs directly.

Guardrails:

- Empty prompts raise validation errors before provider calls.
- Provider errors are captured and returned through fallback metadata.
- Mock responses should be deterministic so tests remain stable.

Acceptance checks:

- Works without API key.
- Works with API key.
- Unit tests do not require network.

### Milestone 3: Hybrid Search Client

Files:

- `src/multi_agent_research_lab/services/search_client.py`
- optional local corpus file under `configs/` or `src/.../services/`.

Tasks:

- Implement `SearchClient.search(query, max_results)`.
- If `TAVILY_API_KEY` exists, use Tavily.
- If Tavily fails or key is missing, use local mock search.
- Normalize all results to `SourceDocument`.
- Deduplicate by URL/title.
- Enforce `max_results`.

Guardrails:

- If no sources are found, return at least one clearly labeled fallback source from the local corpus.
- Invalid source objects should be skipped and logged.

Acceptance checks:

- Researcher can run offline.
- Source list is never larger than `max_sources`.
- Sources have title, snippet, and optional URL.

### Milestone 4: Agent Implementations

Files:

- `src/multi_agent_research_lab/agents/supervisor.py`
- `src/multi_agent_research_lab/agents/researcher.py`
- `src/multi_agent_research_lab/agents/analyst.py`
- `src/multi_agent_research_lab/agents/writer.py`
- optional `src/multi_agent_research_lab/agents/critic.py`

Agent contracts:

| Agent | Input | Output | Failure Fallback |
|---|---|---|---|
| Supervisor | Full state | `next_route`, route trace | Stop with error summary if max iterations exceeded. |
| Researcher | Query and source budget | `sources`, `research_notes` | Use local corpus and concise fallback notes. |
| Analyst | Research notes and sources | `analysis_notes` | Produce limitations-focused analysis from available notes. |
| Writer | Query, sources, analysis | `final_answer` | Produce transparent answer with limitations section. |
| Critic | Final answer and sources | validation metadata | Append warnings without blocking demo unless severe. |

Routing policy:

```text
if final_answer exists:
    done
elif no research_notes or no sources:
    researcher
elif no analysis_notes:
    analyst
else:
    writer
```

Stop conditions:

- `next_route == "done"`
- `iteration >= max_iterations`
- unrecoverable validation failure.

Acceptance checks:

- Each agent appends an `AgentResult`.
- Each agent emits trace events.
- Each agent has a clear prompt and output shape.
- Multi-agent run produces a final answer offline.

### Milestone 5: LangGraph Workflow

Files:

- `src/multi_agent_research_lab/graph/workflow.py`

Tasks:

- Build a LangGraph `StateGraph`.
- Add nodes for supervisor, researcher, analyst, writer, optional critic.
- Add conditional edges from supervisor based on `state.next_route`.
- Compile and invoke graph in `MultiAgentWorkflow.run`.
- Convert graph result back into `ResearchState`.

Expected graph:

```text
START -> supervisor
supervisor -> researcher -> supervisor
supervisor -> analyst -> supervisor
supervisor -> writer -> supervisor
supervisor -> done
```

Guardrails:

- Enforce max iterations in supervisor and/or graph recursion limit.
- Wrap node execution with tracing and error capture.
- Failed worker node should add error and allow supervisor to decide fallback/stop.

Acceptance checks:

- `python -m multi_agent_research_lab.cli multi-agent --query "..."` completes.
- Route history shows expected sequence.
- No infinite loops.

### Milestone 6: Observability and LangSmith

Files:

- `src/multi_agent_research_lab/observability/tracing.py`
- `src/multi_agent_research_lab/observability/logging.py`
- `src/multi_agent_research_lab/services/storage.py`

Tasks:

- Configure LangSmith from environment:
  - `LANGSMITH_API_KEY`
  - `LANGSMITH_PROJECT`
  - tracing enabled flag if needed.
- Wrap workflow and each agent in named spans.
- Add structured local trace events to `state.trace`.
- Export local trace JSON into `reports/traces/`.

Trace span names:

- `workflow.run`
- `agent.supervisor`
- `agent.researcher`
- `agent.analyst`
- `agent.writer`
- `service.llm.complete`
- `service.search.search`
- `evaluation.benchmark`

Acceptance checks:

- LangSmith UI clearly shows each agent step.
- Local trace artifact exists even without LangSmith.
- Report can reference screenshot or trace URL manually.

### Milestone 7: CLI Demo Polish

Files:

- `src/multi_agent_research_lab/cli.py`

Commands:

```bash
malab baseline --query "..."
malab multi-agent --query "..." --format pretty
malab multi-agent --query "..." --format json
malab benchmark --format pretty
malab benchmark --format json
```

Pretty output should include:

- Query panel.
- Route timeline table.
- Sources table.
- Agent result summary.
- Final answer panel.
- Metrics panel: latency, estimated cost, source count, iterations, error count.
- Artifact paths for trace and benchmark report.

JSON output should include:

- Full serialized `ResearchState`.
- Metrics.
- Artifact paths.

Acceptance checks:

- CLI is pleasant enough for a live screen-recorded demo.
- JSON mode is stable for debugging.
- CLI exits non-zero only for unrecoverable errors.

### Milestone 8: Benchmark and Report

Files:

- `src/multi_agent_research_lab/evaluation/benchmark.py`
- `src/multi_agent_research_lab/evaluation/report.py`
- `configs/lab_default.yaml`
- `reports/benchmark_report.md`

Tasks:

- Run baseline and multi-agent for all configured benchmark queries.
- Capture:
  - latency
  - estimated cost
  - token usage if available
  - source count
  - citation coverage
  - failure count
  - quality score placeholder or manually entered peer score.
- Render a markdown report with a comparison table and short analysis.

Report sections:

- Summary
- Benchmark setup
- Metrics table
- Trace evidence
- Qualitative comparison
- Failure modes and fixes
- Recommendation: when multi-agent is worth it and when it is not.

Acceptance checks:

- `reports/benchmark_report.md` exists.
- Report references LangSmith screenshot/trace evidence.
- Benchmark can run offline using mock fallback.

## Testing Strategy

Update tests as implementation replaces TODO behavior.

Required tests:

- Settings load defaults and env overrides.
- State records routes, traces, errors, metrics, and agent results.
- LLM mock fallback returns deterministic content.
- Search mock fallback returns valid `SourceDocument` objects.
- Supervisor routing sequence is correct.
- Each worker updates expected state fields.
- Workflow completes within max iterations.
- Report renders benchmark metrics.
- CLI smoke tests for pretty and JSON modes.

Commands before submission:

```bash
make lint
make typecheck
make test
```

## Environment Variables

Required for full online demo:

```bash
OPENAI_API_KEY=...
TAVILY_API_KEY=...
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=multi-agent-research-lab
```

Useful runtime config:

```bash
OPENAI_MODEL=gpt-4o-mini
MAX_ITERATIONS=6
TIMEOUT_SECONDS=60
LOG_LEVEL=INFO
```

Offline demo should still work without any API keys.

## Demo Script

Suggested live demo flow:

1. Show `.env.example` to prove keys are externalized.
2. Run tests:

   ```bash
   make test
   ```

3. Run baseline:

   ```bash
   malab baseline --query "Compare single-agent and multi-agent workflows for customer support"
   ```

4. Run multi-agent pretty mode:

   ```bash
   malab multi-agent --query "Compare single-agent and multi-agent workflows for customer support" --format pretty
   ```

5. Show route timeline and final answer in terminal.
6. Open LangSmith trace and capture screenshot.
7. Run benchmark:

   ```bash
   malab benchmark --format pretty
   ```

8. Show `reports/benchmark_report.md`.

## Submission Checklist

- [ ] Agents have clear responsibilities and no major overlap.
- [ ] LangGraph workflow completes with bounded iterations.
- [ ] OpenAI/Tavily online path works.
- [ ] Mock fallback path works without keys.
- [ ] LangSmith trace shows workflow and agent spans.
- [ ] Local trace JSON is written.
- [ ] CLI supports pretty and JSON output.
- [ ] Benchmark report is generated.
- [ ] Failure modes are documented in the report.
- [ ] `make lint`, `make typecheck`, and `make test` pass.
- [ ] `.env` is not committed.

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| API key missing during demo | Demo fails | Hybrid mock fallback must be first-class. |
| LangGraph recursion loop | Workflow hangs | Supervisor max iterations and graph recursion limit. |
| Search provider returns poor sources | Weak answer quality | Dedup, validate, and fallback to local corpus. |
| LLM output is malformed | Broken state | Keep outputs mostly text, validate required fields, use fallback summaries. |
| LangSmith unavailable | Missing trace screenshot | Always export local JSON trace and terminal timeline. |
| CLI too noisy | Hard to present | Provide `pretty` summary and `json` debug modes separately. |

## Recommended Build Order

1. Core schemas and state helpers.
2. Mock-first LLM and search clients.
3. Worker agents using mock clients.
4. Supervisor routing.
5. LangGraph workflow.
6. Pretty and JSON CLI.
7. LangSmith tracing.
8. Benchmark report.
9. Online OpenAI/Tavily integration.
10. Tests, docs, and final demo pass.
