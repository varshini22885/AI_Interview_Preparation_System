"""Strict Pydantic schemas for every AI operation (untrusted-output boundary)."""

from pydantic import BaseModel, Field

MIN_Q = 10
MAX_Q = 2000
MIN_CONCEPT = 1
MAX_CONCEPTS = 12
MAX_RUBRIC = 2000


class QuestionOutput(BaseModel):
    question_text: str = Field(min_length=MIN_Q, max_length=MAX_Q)
    question_type: str = Field(pattern="^(TECHNICAL|BEHAVIORAL)$")
    category: str = Field(min_length=2, max_length=128)
    skill: str = Field(min_length=2, max_length=128)
    difficulty: str = Field(pattern="^(EASY|MEDIUM|HARD|EXPERT)$")
    expected_concepts: list[str] = Field(min_length=1, max_length=MAX_CONCEPTS)
    evaluation_rubric: str = Field(min_length=10, max_length=MAX_RUBRIC)
    follow_up_allowed: bool = True
    max_follow_ups: int = Field(ge=0, le=3, default=1)


class TechnicalScores(BaseModel):
    correctness: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    technical_depth: int = Field(ge=0, le=10)


class CommunicationScores(BaseModel):
    clarity: int = Field(ge=0, le=10)
    structure: int = Field(ge=0, le=10)
    conciseness: int = Field(ge=0, le=10)


class EvaluationOutput(BaseModel):
    technical: TechnicalScores
    communication: CommunicationScores
    strengths: str = Field(min_length=1, max_length=2000)
    improvements: str = Field(min_length=1, max_length=2000)
    factual_feedback: str = Field(min_length=1, max_length=3000)
    communication_feedback: str = Field(min_length=1, max_length=3000)
    missing_concepts: list[str] = Field(default_factory=list, max_length=MAX_CONCEPTS)
    incorrect_concepts: list[str] = Field(default_factory=list, max_length=MAX_CONCEPTS)
    confidence: float = Field(ge=0.0, le=1.0)


class FollowUpOutput(BaseModel):
    follow_up_required: bool
    reason: str = Field(min_length=1, max_length=1000)
    question_text: str = Field(min_length=MIN_Q, max_length=MAX_Q)
    target_concept: str = Field(min_length=1, max_length=256)
    difficulty: str = Field(pattern="^(EASY|MEDIUM|HARD|EXPERT)$")


class FeedbackOutput(BaseModel):
    strengths: str = Field(min_length=1, max_length=4000)
    areas_for_improvement: str = Field(min_length=1, max_length=4000)
    detailed_feedback: str = Field(min_length=1, max_length=8000)


class ReportOutput(BaseModel):
    technical_score: int = Field(ge=0, le=100)
    communication_score: int = Field(ge=0, le=100)
    summary: str = Field(min_length=1, max_length=8000)
