"""Interview domain models (part 1: enums + Interview)."""

import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class InterviewStatus(str, Enum):
    CREATED = "CREATED"
    PREPARING = "PREPARING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_ANSWER = "WAITING_FOR_ANSWER"
    EVALUATING = "EVALUATING"
    FOLLOW_UP_REQUIRED = "FOLLOW_UP_REQUIRED"
    NEXT_QUESTION = "NEXT_QUESTION"
    COMPLETED = "COMPLETED"
    REPORT_GENERATING = "REPORT_GENERATING"
    REPORT_READY = "REPORT_READY"
    FAILED = "FAILED"


class InterviewType(str, Enum):
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    MIXED = "MIXED"


class DifficultyLevel(str, Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
    EXPERT = "EXPERT"


class InterviewerPersona(str, Enum):
    FRIENDLY = "FRIENDLY"
    PROFESSIONAL = "PROFESSIONAL"
    STRICT = "STRICT"


class QuestionType(str, Enum):
    TECHNICAL = "TECHNICAL"
    BEHAVIORAL = "BEHAVIORAL"
    FOLLOW_UP = "FOLLOW_UP"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    resume_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), index=True, nullable=True)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    programming_language: Mapped[str | None] = mapped_column(String(128), nullable=True)
    interview_type: Mapped[str] = mapped_column(String(32), nullable=False, default=InterviewType.MIXED.value)
    difficulty: Mapped[str] = mapped_column(String(32), nullable=False, default=DifficultyLevel.MEDIUM.value)
    interviewer_persona: Mapped[str] = mapped_column(String(32), nullable=False, default=InterviewerPersona.PROFESSIONAL.value)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=InterviewStatus.CREATED.value, index=True)
    current_question_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("total_questions >= 1 AND total_questions <= 50", name="ck_interviews_total_questions_range"),
        CheckConstraint("current_question_index >= 0", name="ck_interviews_current_index_nonneg"),
        Index("ix_interviews_user_status", "user_id", "status"),
        Index("ix_interviews_user_created", "user_id", "created_at"),
    )

    user: Mapped["User"] = relationship(back_populates="interviews")
    resume: Mapped["Resume | None"] = relationship(back_populates="interviews")
    questions: Mapped[list["InterviewQuestion"]] = relationship(back_populates="interview", cascade="all, delete-orphan", order_by="InterviewQuestion.order_index")
    feedback: Mapped["InterviewFeedback | None"] = relationship(back_populates="interview", cascade="all, delete-orphan", uselist=False)
    performance_report: Mapped["PerformanceReport | None"] = relationship(back_populates="interview", cascade="all, delete-orphan", uselist=False)


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), index=True, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False, default=QuestionType.TECHNICAL.value)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    current_answer_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("interview_id", "order_index", name="uq_question_interview_order"),
        CheckConstraint("order_index >= 0", name="ck_question_order_nonneg"),
        Index("ix_questions_interview_order", "interview_id", "order_index"),
    )

    interview: Mapped["Interview"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan", order_by="Answer.attempt_number")
    follow_ups: Mapped[list["InterviewFollowUp"]] = relationship(back_populates="parent_question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    answer_text: Mapped[str] = mapped_column(Text, nullable=False)
    time_taken_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("question_id", "attempt_number", name="uq_answer_question_attempt"),
        CheckConstraint("attempt_number >= 1", name="ck_answer_attempt_positive"),
        Index("ix_answers_question_attempt", "question_id", "attempt_number"),
    )

    question: Mapped["InterviewQuestion"] = relationship(back_populates="answers")
    evaluation: Mapped["AnswerEvaluation | None"] = relationship(back_populates="answer", cascade="all, delete-orphan", uselist=False)


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    answer_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("answers.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    correctness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    relevance_score: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    technical_depth_score: Mapped[int] = mapped_column(Integer, nullable=False)
    technical_overall: Mapped[int] = mapped_column(Integer, nullable=False)
    clarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    structure_score: Mapped[int] = mapped_column(Integer, nullable=False)
    conciseness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    communication_overall: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluation_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evaluated_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("correctness_score >= 0 AND correctness_score <= 10", name="ck_eval_correctness_range"),
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 10", name="ck_eval_relevance_range"),
        CheckConstraint("completeness_score >= 0 AND completeness_score <= 10", name="ck_eval_completeness_range"),
        CheckConstraint("technical_depth_score >= 0 AND technical_depth_score <= 10", name="ck_eval_depth_range"),
        CheckConstraint("technical_overall >= 0 AND technical_overall <= 10", name="ck_eval_tech_overall_range"),
        CheckConstraint("clarity_score >= 0 AND clarity_score <= 10", name="ck_eval_clarity_range"),
        CheckConstraint("structure_score >= 0 AND structure_score <= 10", name="ck_eval_structure_range"),
        CheckConstraint("conciseness_score >= 0 AND conciseness_score <= 10", name="ck_eval_conciseness_range"),
        CheckConstraint("communication_overall >= 0 AND communication_overall <= 10", name="ck_eval_comm_overall_range"),
    )

    answer: Mapped["Answer"] = relationship(back_populates="evaluation")


class InterviewFollowUp(Base):
    __tablename__ = "interview_follow_ups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    parent_question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interview_questions.id", ondelete="CASCADE"), index=True, nullable=False)
    triggering_answer_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("answers.id", ondelete="SET NULL"), index=True, nullable=True)
    follow_up_text: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    follow_up_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    parent_question: Mapped["InterviewQuestion"] = relationship(back_populates="follow_ups")
    triggering_answer: Mapped["Answer | None"] = relationship()


class InterviewFeedback(Base):
    __tablename__ = "interview_feedback"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    areas_for_improvement: Mapped[str | None] = mapped_column(Text, nullable=True)
    detailed_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    feedback_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    interview: Mapped["Interview"] = relationship(back_populates="feedback")


class PerformanceReport(Base):
    __tablename__ = "performance_reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    technical_score: Mapped[int] = mapped_column(Integer, nullable=False)
    communication_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions_answered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    report_detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("technical_score >= 0 AND technical_score <= 100", name="ck_report_technical_range"),
        CheckConstraint("communication_score >= 0 AND communication_score <= 100", name="ck_report_communication_range"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 100", name="ck_report_overall_range"),
        CheckConstraint("total_questions_answered >= 0", name="ck_report_answered_nonneg"),
    )

    interview: Mapped["Interview"] = relationship(back_populates="performance_report")





