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

## Current Phase

- Ready for commit: Commit 3 - implement agents and routing behavior.
- Next phase: Commit 4 - LangGraph workflow integration.

Mục tiêu:

- Build `StateGraph` với supervisor/researcher/analyst/writer nodes.
- Add conditional edges theo `state.next_route`.
- `MultiAgentWorkflow.run` trả về `ResearchState` hoàn chỉnh.
- CLI `multi-agent` bắt đầu chạy được end-to-end.
