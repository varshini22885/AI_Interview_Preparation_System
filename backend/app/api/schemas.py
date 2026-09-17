"""Shared API response schemas (never serialize ORM directly)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Page(BaseModel):
    items: list
    page: int
    page_size: int
    total: int


class InterviewCreateRequest(BaseModel):
    resume_id: uuid.UUID | None = None
    target_role: str = Field(min_length=2, max_length=255)
    programming_language: str | None = Field(default=None, max_length=128)
    interview_type: str = Field(pattern="^(TECHNICAL|BEHAVIORAL|MIXED)$", default="MIXED")
    difficulty: str = Field(pattern="^(EASY|MEDIUM|HARD|EXPERT)$", default="MEDIUM")
    interviewer_persona: str = Field(pattern="^(FRIENDLY|PROFESSIONAL|STRICT)$", default="PROFESSIONAL")
    question_count: int = Field(ge=1, le=50, default=10)


class InterviewSummaryResponse(BaseModel):
    id: uuid.UUID
    status: str
    target_role: str
    interview_type: str
    difficulty: str
    interviewer_persona: str
    total_questions: int
    current_question_index: int
    created_at: datetime


class InterviewDetailResponse(InterviewSummaryResponse):
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime
    report_available: bool = False


class CurrentQuestionResponse(BaseModel):
    interview_id: uuid.UUID
    status: str
    order_index: int
    total_questions: int
    question_id: uuid.UUID
    question_type: str
    question_text: str
    answer_allowed: bool


class AnswerSubmitRequest(BaseModel):
    question_id: uuid.UUID
    answer_text: str = Field(min_length=1, max_length=20000)
    idempotency_key: str | None = Field(default=None, min_length=8, max_length=128)


class AnswerSubmissionResponse(BaseModel):
    answer_id: uuid.UUID
    attempt_number: int
    status: str
    is_duplicate: bool
    accepted: bool = True


class ReportResponse(BaseModel):
    interview_id: uuid.UUID
    status: str
    technical_score: int | None = None
    communication_score: int | None = None
    overall_score: int | None = None
    total_questions_answered: int | None = None
    strengths: str | None = None
    areas_for_improvement: str | None = None


class HistoryItemResponse(BaseModel):
    id: uuid.UUID
    status: str
    target_role: str
    interview_type: str
    difficulty: str
    total_questions: int
    completed_at: datetime | None = None
    overall_score: int | None = None


class ResumeResponse(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime
    parsed_at: datetime | None = None


class RealtimeSessionResponse(BaseModel):
    session_id: uuid.UUID
    interview_id: uuid.UUID
    status: str
    websocket_path: str


class RoleInfo(BaseModel):
    role: str
    interview_types: list[str]
    difficulties: list[str]
    languages: list[str]
