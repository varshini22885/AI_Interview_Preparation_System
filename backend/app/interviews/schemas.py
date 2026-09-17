"""Pydantic domain schemas for interview service input/output."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.interview import DifficultyLevel, InterviewerPersona, InterviewStatus, InterviewType

MIN_QUESTIONS = 1
MAX_QUESTIONS = 50
MIN_ANSWER_CHARS = 1
MAX_ANSWER_CHARS = 20000
MIN_ROLE_CHARS = 2
MAX_ROLE_CHARS = 255
MAX_LANGUAGE_CHARS = 128


class InterviewCreateInput(BaseModel):
    user_id: uuid.UUID
    resume_id: uuid.UUID | None = None
    target_role: str = Field(min_length=MIN_ROLE_CHARS, max_length=MAX_ROLE_CHARS)
    programming_language: str | None = Field(default=None, max_length=MAX_LANGUAGE_CHARS)
    interview_type: InterviewType = InterviewType.MIXED
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    interviewer_persona: InterviewerPersona = InterviewerPersona.PROFESSIONAL
    question_count: int = Field(ge=MIN_QUESTIONS, le=MAX_QUESTIONS, default=10)


class AnswerSubmitInput(BaseModel):
    user_id: uuid.UUID
    interview_id: uuid.UUID
    question_id: uuid.UUID
    answer_text: str = Field(min_length=MIN_ANSWER_CHARS, max_length=MAX_ANSWER_CHARS)
    idempotency_key: str = Field(min_length=8, max_length=128)
    time_taken_seconds: int | None = Field(default=None, ge=0, le=86400)


class InterviewState(BaseModel):
    interview_id: uuid.UUID
    status: InterviewStatus
    current_question_index: int
    total_questions: int
    started_at: datetime | None = None
    completed_at: datetime | None = None


class InterviewSummary(BaseModel):
    id: uuid.UUID
    status: InterviewStatus
    target_role: str
    interview_type: InterviewType
    difficulty: DifficultyLevel
    interviewer_persona: InterviewerPersona
    total_questions: int
    current_question_index: int
    created_at: datetime


class CurrentQuestionView(BaseModel):
    question_id: uuid.UUID
    interview_id: uuid.UUID
    order_index: int
    question_type: str
    question_text: str


class AnswerResult(BaseModel):
    answer_id: uuid.UUID
    question_id: uuid.UUID
    attempt_number: int
    interview_status: InterviewStatus
    is_duplicate: bool = False
