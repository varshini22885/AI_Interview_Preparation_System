"""Vendor provider: lazy SDK imports, structured JSON, no secrets in logs."""

import json
import time

from app.ai.exceptions import AIConfigurationError, AIProviderError
from app.ai.provider import AIMetadata, AIResult


class VendorProvider:
    name: str

    def __init__(self, provider_name: str) -> None:
        self.name = provider_name

    def _settings(self):
        from app.core.config import get_settings

        return get_settings()

    def _call(self, prompt: str, operation: str, max_tokens: int) -> tuple[str, AIMetadata]:
        from app.core.config import get_settings

        settings = get_settings()
        started = time.monotonic()
        if self.name in ("openai", "nvidia"):
            api_key = settings.OPENAI_API_KEY if self.name == "openai" else settings.NVIDIA_API_KEY
            model = settings.OPENAI_MODEL if self.name == "openai" else settings.NVIDIA_LLM_MODEL
            base_url = None if self.name == "openai" else settings.NVIDIA_BASE_URL
            if not api_key:
                raise AIConfigurationError(f"{self.name.upper()}_API_KEY is not configured")
            if not model:
                raise AIConfigurationError(f"{self.name.upper()} model is not configured")
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise AIConfigurationError("openai SDK is not installed") from exc
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=settings.AI_TIMEOUT_SECONDS)
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=settings.AI_TEMPERATURE,
                    max_tokens=max_tokens,
                    response_format={"type": "json_object"},
                )
            except Exception as exc:
                raise AIProviderError(f"OpenAI call failed: {type(exc).__name__}") from exc
            text = resp.choices[0].message.content or ""
            usage: dict = {}
            try:
                u = resp.usage
                if u is not None:
                    usage = {"prompt_tokens": getattr(u, "prompt_tokens", 0), "completion_tokens": getattr(u, "completion_tokens", 0)}
            except Exception:
                usage = {}
            meta = AIMetadata(provider=self.name, model=model, operation=operation, latency_ms=int((time.monotonic() - started) * 1000), usage=usage)
            return text, meta
        if self.name == "anthropic":
            if not settings.ANTHROPIC_API_KEY:
                raise AIConfigurationError("ANTHROPIC_API_KEY is not configured")
            try:
                import anthropic as anthropic_sdk
            except ImportError as exc:
                raise AIConfigurationError("anthropic SDK is not installed") from exc
            client = anthropic_sdk.Anthropic(api_key=settings.ANTHROPIC_API_KEY, timeout=settings.AI_TIMEOUT_SECONDS)
            try:
                resp = client.messages.create(model=settings.ANTHROPIC_MODEL, max_tokens=max_tokens, temperature=settings.AI_TEMPERATURE, messages=[{"role": "user", "content": prompt}])
            except Exception as exc:
                raise AIProviderError(f"Anthropic call failed: {type(exc).__name__}") from exc
            parts = getattr(resp, "content", []) or []
            text = "".join(getattr(p, "text", "") for p in parts)
            usage = {}
            try:
                usage = {"input_tokens": getattr(resp.usage, "input_tokens", 0), "output_tokens": getattr(resp.usage, "output_tokens", 0)}
            except Exception:
                usage = {}
            meta = AIMetadata(provider="anthropic", model=settings.ANTHROPIC_MODEL, operation=operation, latency_ms=int((time.monotonic() - started) * 1000), usage=usage)
            return text, meta
        raise AIConfigurationError(f"Unknown vendor {self.name!r}")

    def _parse(self, text: str, operation: str, meta: AIMetadata, schema):
        from pydantic import ValidationError

        from app.ai.exceptions import AIValidationError

        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIValidationError(f"{operation}: model did not return JSON") from exc
        if isinstance(payload, dict) and "question" in payload and "question_text" not in payload and isinstance(payload["question"], dict):
            payload = payload["question"]
        try:
            data = schema.model_validate(payload)
        except ValidationError as exc:
            raise AIValidationError(f"{operation}: schema validation failed") from exc
        return AIResult(data=data, meta=meta)

    def generate_question(self, prompt: str, *, schema) -> AIResult:
        from app.core.config import get_settings

        text, meta = self._call(prompt, "generate_question", get_settings().AI_MAX_OUTPUT_TOKENS)
        return self._parse(text, "generate_question", meta, schema)

    def evaluate_answer(self, prompt: str, *, schema) -> AIResult:
        from app.core.config import get_settings

        text, meta = self._call(prompt, "evaluate_answer", get_settings().AI_MAX_OUTPUT_TOKENS)
        return self._parse(text, "evaluate_answer", meta, schema)

    def generate_follow_up(self, prompt: str, *, schema) -> AIResult:
        from app.core.config import get_settings

        text, meta = self._call(prompt, "generate_follow_up", get_settings().AI_MAX_OUTPUT_TOKENS)
        return self._parse(text, "generate_follow_up", meta, schema)

    def generate_interview_feedback(self, prompt: str, *, schema) -> AIResult:
        from app.core.config import get_settings

        text, meta = self._call(prompt, "generate_interview_feedback", get_settings().AI_MAX_OUTPUT_TOKENS)
        return self._parse(text, "generate_interview_feedback", meta, schema)

    def generate_performance_report(self, prompt: str, *, schema) -> AIResult:
        from app.core.config import get_settings

        text, meta = self._call(prompt, "generate_performance_report", get_settings().AI_MAX_OUTPUT_TOKENS)
        return self._parse(text, "generate_performance_report", meta, schema)
