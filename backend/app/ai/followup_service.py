"""Follow-up service: evidence-justified, deduped, bounded."""

from dataclasses import dataclass

from app.ai.retry import run_with_retries
from app.ai.schemas import FollowUpOutput

FILLER = ("because interviews need follow-ups", "ask another question")


@dataclass(frozen=True)
class FollowUpRequest:
    question_text: str
    answer_text: str
    missing_concepts: list[str]
    incorrect_concepts: list[str]
    difficulty: str
    persona: str
    prior_follow_ups: list[str]
    max_follow_ups: int = 1


@dataclass(frozen=True)
class FollowUpDecision:
    output: FollowUpOutput
    attempts: int


def _norm(text: str) -> str:
    import re

    return re.sub(r"\s+", " ", text.strip().lower())


class FollowUpService:
    def __init__(self, provider=None) -> None:
        self.provider = provider

    def _provider(self):
        if self.provider is not None:
            return self.provider
        from app.ai.provider import get_provider

        return get_provider()

    def decide(self, req: FollowUpRequest) -> FollowUpDecision:
        from app.ai.exceptions import AIQuestionRejected
        from app.ai.prompts import build_followup_prompt
        from app.core.config import get_settings

        settings = get_settings()
        if len(req.prior_follow_ups) >= max(0, req.max_follow_ups):
            return FollowUpDecision(output=FollowUpOutput(follow_up_required=False, reason="Follow-up budget exhausted.", question_text="No further follow-up; the identified gap has been covered.", target_concept=(req.missing_concepts + req.incorrect_concepts + ["general"])[:1][0], difficulty=req.difficulty), attempts=0)
        prompt = build_followup_prompt(question=req.question_text, answer=req.answer_text[: settings.AI_MAX_ANSWER_CHARS], missing=req.missing_concepts, incorrect=req.incorrect_concepts, difficulty=req.difficulty, persona=req.persona, prior=req.prior_follow_ups)

        def _call():
            result = self._provider().generate_follow_up(prompt, schema=FollowUpOutput)
            data = result.data
            if any(f in data.reason.lower() for f in FILLER):
                raise AIQuestionRejected("Filler follow-up reason")
            if not data.follow_up_required:
                return result
            norm = _norm(data.question_text)
            for prior in req.prior_follow_ups:
                if norm == _norm(prior):
                    raise AIQuestionRejected("Duplicate follow-up")
            has_evidence = bool(req.missing_concepts or req.incorrect_concepts or len(req.answer_text.strip()) < 40)
            if not has_evidence and data.follow_up_required and "sufficient" in data.reason.lower():
                raise AIQuestionRejected("Unjustified follow-up")
            return result

        result, attempts = run_with_retries("generate_follow_up", _call, max_attempts=settings.AI_MAX_RETRIES)
        return FollowUpDecision(output=result.data, attempts=attempts)
