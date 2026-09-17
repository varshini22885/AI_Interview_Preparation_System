"""Provider interface + config-driven factory (lazy SDK imports only)."""

from dataclasses import dataclass, field
from typing import Any, Protocol

from app.ai.schemas import EvaluationOutput, FeedbackOutput, FollowUpOutput, QuestionOutput, ReportOutput


@dataclass(frozen=True)
class AIMetadata:
    provider: str
    model: str
    operation: str
    latency_ms: int = 0
    success: bool = True
    retry_count: int = 0
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResult:
    data: Any
    meta: AIMetadata


class AIProvider(Protocol):
    name: str

    def generate_question(self, prompt: str, *, schema: type[QuestionOutput]) -> AIResult: ...
    def evaluate_answer(self, prompt: str, *, schema: type[EvaluationOutput]) -> AIResult: ...
    def generate_follow_up(self, prompt: str, *, schema: type[FollowUpOutput]) -> AIResult: ...
    def generate_interview_feedback(self, prompt: str, *, schema: type[FeedbackOutput]) -> AIResult: ...
    def generate_performance_report(self, prompt: str, *, schema: type[ReportOutput]) -> AIResult: ...


def get_provider() -> AIProvider:
    from app.ai.exceptions import AIConfigurationError
    from app.core.config import get_settings

    settings = get_settings()
    provider_name = str(settings.AI_PROVIDER).lower()
    if provider_name in ("nvidia", "openai", "anthropic"):
        from app.ai.providers.vendor import VendorProvider

        return VendorProvider(provider_name)
    if provider_name in ("test", "deterministic-test"):
        from app.ai.providers.test_provider import TestAIProvider

        if settings.APP_ENV == "production":
            raise AIConfigurationError("Test AI provider is forbidden in production")
        return TestAIProvider()
    raise AIConfigurationError(f"Unknown AI_PROVIDER {settings.AI_PROVIDER!r}")
