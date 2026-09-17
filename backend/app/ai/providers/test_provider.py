"""Deterministic test provider (tests only, never production)."""

import re

from app.ai.provider import AIMetadata, AIResult
from app.ai.schemas import EvaluationOutput, FeedbackOutput, FollowUpOutput, QuestionOutput, ReportOutput


def _param(prompt: str, key: str, default: str) -> str:
    """Read a declared parameter marker (e.g. 'Type: TECHNICAL') from the
    deterministic prompt so generated output always matches the request."""
    match = re.search(rf"{key}:\s*([A-Z]+)", prompt)
    return match.group(1) if match else default


class TestAIProvider:
    name = "test"

    def _meta(self, operation: str) -> AIMetadata:
        return AIMetadata(provider="test", model="deterministic-v1", operation=operation)

    def generate_question(self, prompt: str, *, schema: type[QuestionOutput] = QuestionOutput) -> AIResult:
        interview_type = _param(prompt, "Type", "MIXED")
        difficulty = _param(prompt, "Difficulty", "MEDIUM")
        qtype = "BEHAVIORAL" if interview_type == "BEHAVIORAL" else "TECHNICAL"
        data = schema.model_validate({
            "question_text": "Explain how a Python dictionary works and when you would prefer it over a list for lookups?",
            "question_type": qtype,
            "category": "data-structures" if qtype == "TECHNICAL" else "teamwork",
            "skill": "python-dicts" if qtype == "TECHNICAL" else "communication",
            "difficulty": difficulty,
            "expected_concepts": ["hash-table", "average-O(1)-lookup", "key-hashability"],
            "evaluation_rubric": "Award credit for hashing, O(1) average case, hashable keys, and list-vs-dict trade-off.",
            "follow_up_allowed": True,
            "max_follow_ups": 1,
        })
        return AIResult(data=data, meta=self._meta("generate_question"))

    def evaluate_answer(self, prompt: str, *, schema: type[EvaluationOutput] = EvaluationOutput) -> AIResult:
        low = "empty" in prompt.lower()
        tech = {"correctness": 2, "relevance": 2, "completeness": 2, "technical_depth": 2} if low else {"correctness": 8, "relevance": 8, "completeness": 7, "technical_depth": 7}
        comm = {"clarity": 3, "structure": 3, "conciseness": 4} if ("rambling" in prompt.lower()) else {"clarity": 8, "structure": 8, "conciseness": 7}
        data = schema.model_validate({
            "technical": tech,
            "communication": comm,
            "strengths": "Covers the core idea.",
            "improvements": "Add complexity trade-offs.",
            "factual_feedback": "Hash-table explanation present; collision handling missing.",
            "communication_feedback": "Structured but could be more concise.",
            "missing_concepts": ["collision-handling"],
            "incorrect_concepts": [],
            "confidence": 0.8,
        })
        return AIResult(data=data, meta=self._meta("evaluate_answer"))

    def generate_follow_up(self, prompt: str, *, schema: type[FollowUpOutput] = FollowUpOutput) -> AIResult:
        need = "collision-handling" in prompt.lower() or "missing" in prompt.lower()
        data = schema.model_validate({
            "follow_up_required": bool(need),
            "reason": "Probe the missing collision-handling concept." if need else "Answer is sufficient.",
            "question_text": "How does Python handle hash collisions in dictionaries, and what is the performance impact?",
            "target_concept": "collision-handling",
            "difficulty": "MEDIUM",
        })
        return AIResult(data=data, meta=self._meta("generate_follow_up"))

    def generate_interview_feedback(self, prompt: str, *, schema: type[FeedbackOutput] = FeedbackOutput) -> AIResult:
        data = schema.model_validate({"strengths": "Solid fundamentals.", "areas_for_improvement": "Deepen trade-off analysis.", "detailed_feedback": "Good progress; focus on edge cases."})
        return AIResult(data=data, meta=self._meta("generate_interview_feedback"))

    def generate_performance_report(self, prompt: str, *, schema: type[ReportOutput] = ReportOutput) -> AIResult:
        data = schema.model_validate({"technical_score": 75, "communication_score": 70, "summary": "Steady performance."})
        return AIResult(data=data, meta=self._meta("generate_performance_report"))
