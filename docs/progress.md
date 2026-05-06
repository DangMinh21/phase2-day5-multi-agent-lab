# Progress

## Commit 1: Add Core Workflow State Contracts

Đã làm:

- Thêm route enum, usage metadata, agent result metadata và benchmark fields.
- Mở rộng `ResearchState` với `next_route`, `metrics`, timestamps, trace events, errors và agent results.
- Thêm helper methods để workflow/agents ghi state nhất quán.
- Cập nhật tests cho state serialization, route tracking, error tracking và metrics.

Để làm gì:

- Tạo shared state đủ mạnh cho LangGraph, tracing, benchmark và CLI demo.
- Giúp handoff giữa agents rõ ràng, dễ debug, dễ xuất JSON artifact.

Thông tin quan trọng:

- Verification: `pytest`, `ruff check src tests`, `mypy src` passed.
- Đây là nền tảng cho rubric: state design, trace explanation, failure guard.

## Commit 2: Add Hybrid LLM And Search Clients

Đã làm:

- Implement `LLMClient`: dùng OpenAI khi có `OPENAI_API_KEY`, fallback deterministic mock khi thiếu key hoặc provider lỗi.
- Implement `SearchClient`: dùng Tavily khi có `TAVILY_API_KEY`, fallback local mock corpus khi thiếu key hoặc provider lỗi.
- Thêm retry bằng `tenacity`, timeout theo settings, metadata provider/fallback.
- Thêm tests offline cho LLM/search không cần network hoặc API keys.

Để làm gì:

- Đảm bảo demo và tests vẫn chạy ổn định trong môi trường không có API keys.
- Vẫn hỗ trợ đường production-like khi cấu hình OpenAI/Tavily thật.

Thông tin quan trọng:

- Verification: `pytest`, `ruff check src tests`, `mypy src` passed.
- Fallback mock là first-class path, không chỉ là test stub.
- `.gitignore` có thay đổi riêng của user, Codex không chỉnh file đó.

## Commit 3: Implement Agents And Routing Behavior

Đã làm:

- Implement `SupervisorAgent` route theo state:
  - thiếu sources/research notes -> `researcher`
  - thiếu analysis notes -> `analyst`
  - đủ research + analysis -> `writer`
  - có final answer hoặc quá max iterations -> `done`
- Implement `ResearcherAgent`: gọi `SearchClient`, lấy sources, gọi `LLMClient`, tạo research notes.
- Implement `AnalystAgent`: gọi `LLMClient`, tạo structured analysis notes.
- Implement `WriterAgent`: gọi `LLMClient`, tạo final answer có định hướng citation/limitations.
- Mỗi agent đều ghi `AgentResult`, trace event, metadata provider/fallback, usage và latency.
- Thay test TODO bằng behavior tests cho supervisor/researcher/analyst/writer.

Để làm gì:

- Biến skeleton agent thành workflow components thật, có thể được LangGraph gọi ở phase tiếp theo.
- Tăng điểm rubric cho role clarity, state design, failure visibility và trace explanation.

Thông tin quan trọng:

- Verification: `pytest`, `ruff check src tests`, `mypy src` passed.
- Tests hiện chạy offline bằng mock LLM/search, không cần API keys.
- Supervisor đã có guardrail `max_iterations`.

## Commit 4: Add LangGraph Workflow Integration

Đã làm:

- Implement `MultiAgentWorkflow.build()` bằng LangGraph `StateGraph` khi package `langgraph` được install.
- Add nodes: `supervisor`, `researcher`, `analyst`, `writer`.
- Add conditional edges từ supervisor theo `state.next_route`.
- Add worker edges quay về supervisor để tiếp tục route.
- Implement `MultiAgentWorkflow.run()` trả về `ResearchState` hoàn chỉnh.
- Add local-loop fallback khi môi trường chưa install LangGraph, có trace event rõ ràng nhưng không tính là workflow error.
- Add workflow tests cho end-to-end offline run và JSON serialization.

Để làm gì:

- Biến các agent rời rạc thành một workflow có orchestration rõ ràng.
- Đáp ứng yêu cầu dùng LangGraph thật trong môi trường production/demo đầy đủ.
- Giữ demo/test không bị vỡ nếu máy chưa cài optional dependency.

Thông tin quan trọng:

- Verification: `pytest`, `ruff check src tests`, `mypy src` passed.
- CLI smoke test chạy được với `PYTHONPATH=src python -m multi_agent_research_lab.cli multi-agent --query "..."`
- Môi trường hiện tại chưa install `langgraph`, nên smoke test dùng fallback `local-loop`.
- Để chạy graph engine thật: dùng `make install` trước demo.

## Commit 5: Add CLI Pretty/JSON Demo And Trace Artifacts

Đã làm:

- Add `--format pretty|json` cho `baseline` và `multi-agent`.
- Pretty mode hiển thị:
  - query panel
  - route timeline
  - sources table
  - agent results table
  - final answer panel
  - run metrics table
- JSON mode in full serialized `ResearchState` để debug/pipe vào tool khác.
- Multi-agent run tự ghi trace artifact vào `reports/traces/*_multi_agent_trace.json`.
- Add CLI tests cho JSON output và invalid format handling.

Để làm gì:

- Làm CLI đủ đẹp để demo trực tiếp hoặc quay màn hình.
- Giữ JSON mode sạch để dễ inspect state, trace, metrics.
- Tạo local trace artifact làm bằng chứng fallback nếu LangSmith chưa sẵn sàng.

Thông tin quan trọng:

- Verification: `pytest`, `ruff check src tests`, `mypy src` passed.
- Pretty smoke test passed trong thư mục tạm bằng `PYTHONPATH=... python -m multi_agent_research_lab.cli multi-agent --query "..." --format pretty`.
- Trace artifact được ghi tương đối dưới `reports/traces/`.

## Current Phase

- Ready for commit: Commit 5 - CLI pretty/json demo and trace artifacts.
- Next phase: Commit 6 - benchmark report and LangSmith tracing polish.

Mục tiêu:

- Implement richer benchmark metrics.
- Add `benchmark` CLI command with pretty/json modes.
- Render `reports/benchmark_report.md`.
- Add LangSmith-oriented tracing configuration/evidence notes.
