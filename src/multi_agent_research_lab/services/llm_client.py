"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

from dataclasses import dataclass
from typing import Any

from tenacity import RetryError, Retrying, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import ValidationError


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    provider: str = "mock"
    model: str | None = None
    fallback_reason: str | None = None


class LLMClient:
    """Provider-agnostic LLM client with deterministic offline fallback."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion.

        Uses OpenAI when configured. If the key/package/provider call is unavailable,
        returns a deterministic mock response so tests and demos can run offline.
        """

        self._validate_prompt(system_prompt, "system_prompt")
        self._validate_prompt(user_prompt, "user_prompt")

        if not self.settings.openai_api_key:
            return self._mock_complete(system_prompt, user_prompt, "OPENAI_API_KEY is not set")

        try:
            return self._complete_with_retry(system_prompt, user_prompt)
        except Exception as exc:
            return self._mock_complete(system_prompt, user_prompt, f"OpenAI fallback: {exc}")

    def _complete_with_retry(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(2),
                wait=wait_exponential(multiplier=0.25, min=0.25, max=1),
                reraise=True,
            ):
                with attempt:
                    return self._openai_complete(system_prompt, user_prompt)
        except RetryError as exc:
            raise RuntimeError(f"LLM retry exhausted: {exc}") from exc

        raise RuntimeError("LLM retry exhausted without a response")

    def _openai_complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai package is not installed") from exc

        client = OpenAI(
            api_key=self.settings.openai_api_key,
            timeout=self.settings.timeout_seconds,
            max_retries=0,
        )
        response = client.chat.completions.create(
            model=self.settings.openai_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        content = response.choices[0].message.content or ""
        usage: Any = response.usage
        input_tokens = getattr(usage, "prompt_tokens", None) if usage is not None else None
        output_tokens = getattr(usage, "completion_tokens", None) if usage is not None else None
        return LLMResponse(
            content=content.strip(),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            provider="openai",
            model=self.settings.openai_model,
        )

    def _mock_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback_reason: str,
    ) -> LLMResponse:
        input_tokens = self._estimate_tokens(system_prompt) + self._estimate_tokens(user_prompt)
        topic = self._first_sentence(user_prompt)
        content = (
            "Mock LLM response.\n\n"
            f"Topic: {topic}\n"
            "Key points:\n"
            "- Use the available sources and state fields before making claims.\n"
            "- Keep handoffs explicit so the next agent can inspect the reasoning.\n"
            "- Mention limitations when evidence is incomplete.\n\n"
            "This deterministic fallback is intended for offline tests and demos."
        )
        return LLMResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=self._estimate_tokens(content),
            cost_usd=0.0,
            provider="mock",
            model="deterministic-mock",
            fallback_reason=fallback_reason,
        )

    @staticmethod
    def _validate_prompt(prompt: str, field_name: str) -> None:
        if not prompt or not prompt.strip():
            raise ValidationError(f"{field_name} must not be empty")

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return max(1, len(text.split()))

    @staticmethod
    def _first_sentence(text: str) -> str:
        compact = " ".join(text.strip().split())
        if not compact:
            return "No topic provided"
        return compact.split(".")[0][:160]
