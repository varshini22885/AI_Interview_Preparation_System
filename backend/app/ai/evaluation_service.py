"""Answer evaluation service: validated AI dims + app-owned overall formula."""

from dataclasses import dataclass

from app.ai.retry import run_with_retries
from app.ai.schemas import EvaluationOutput
from app.evaluations.scoring import communication_overall_0_10, technical_overall_0_10


@dataclass(frozen=True)
class EvaluationRequest:
    role: str
    question_text: str
    rubric: str
    expected_concepts: list[str]
    answer_text: str
    persona: str


@dataclass(frozen=True)
class EvaluatedAnswer:
    output: EvaluationOutput
    technical_overall: int
    communication_overall: int
    attempts: int
    provider: str
    model: str


class AnswerEvaluationService:
    def __init__(self, provider=None) -> None:
        self.provider = provider

    def _provider(self):
        if self.provider is not None:
            return self.provider
        from app.ai.provider import get_provider

        return get_provider()

    def evaluate(self, req: EvaluationRequest) -> EvaluatedAnswer:
        from app.ai.prompts import build_evaluation_prompt
        from app.core.config import get_settings

        settings = get_settings()
        if not req.answer_text.strip():
            from app.ai.exceptions import AIValidationError

            raise AIValidationError("Empty answer")
        prompt = build_evaluation_prompt(role=req.role, question=req.question_text, rubric=req.rubric, expected=req.expected_concepts, answer=req.answer_text[: settings.AI_MAX_ANSWER_CHARS], persona=req.persona)

        def _call():
            return self._provider().evaluate_answer(prompt, schema=EvaluationOutput)

        result, attempts = run_with_retries("evaluate_answer", _call, max_attempts=settings.AI_MAX_RETRIES)
        data: EvaluationOutput = result.data
        tech = technical_overall_0_10(data)
        comm = communication_overall_0_10(data)
        return EvaluatedAnswer(output=data, technical_overall=tech, communication_overall=comm, attempts=attempts, provider=result.meta.provider, model=result.meta.model)
