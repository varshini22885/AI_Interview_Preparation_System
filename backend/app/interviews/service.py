"""Interview service layer: business rules + transactions + ownership."""

import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.interviews import state_machine as sm
from app.interviews.exceptions import InterviewAccessDenied, InterviewNotFound, InvalidInterviewConfig, ResumeNotUsable
from app.interviews.schemas import MAX_QUESTIONS, MIN_QUESTIONS
from app.models.interview import DifficultyLevel, Interview, InterviewerPersona, InterviewType
from app.models.resume import Resume
from app.models.user import User


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _require_actor(actor_user_id: uuid.UUID | None) -> uuid.UUID:
    if actor_user_id is None:
        raise InterviewAccessDenied("Authentication required")
    return actor_user_id


def _coerce_status(value: str):
    from app.models.interview import InterviewStatus

    return InterviewStatus(str(value))


def get_user_interview(db: Session, interview_id: uuid.UUID, user_id: uuid.UUID) -> Interview:
    interview = db.get(Interview, interview_id)
    if interview is None or interview.user_id != user_id:
        raise InterviewNotFound("Interview not found")
    return interview


def get_locked_interview(db: Session, interview_id: uuid.UUID, user_id: uuid.UUID) -> Interview:
    stmt = select(Interview).where(Interview.id == interview_id).with_for_update()
    interview = db.execute(stmt).scalar_one_or_none()
    if interview is None or interview.user_id != user_id:
        raise InterviewNotFound("Interview not found")
    return interview


def transition_interview(db: Session, interview: Interview, target, *, actor_user_id: uuid.UUID | None, reason: str | None = None) -> Interview:
    from app.models.interview import InterviewStatus

    _require_actor(actor_user_id)
    if interview.user_id != actor_user_id:
        raise InterviewNotFound("Interview not found")
    target_status = target if isinstance(target, InterviewStatus) else InterviewStatus(str(target))
    sm.validate_transition(_coerce_status(interview.status), target_status)
    interview.status = target_status.value
    now = _utcnow()
    if target_status == InterviewStatus.IN_PROGRESS and interview.started_at is None:
        interview.started_at = now
    if target_status == InterviewStatus.COMPLETED and interview.completed_at is None:
        interview.completed_at = now
    interview.updated_at = now
    db.add(interview)
    db.flush()
    return interview


def create_interview(db: Session, *, user_id: uuid.UUID, resume_id, target_role: str, programming_language, interview_type, difficulty, interviewer_persona, question_count: int) -> Interview:
    from app.models.interview import InterviewStatus

    role = (target_role or "").strip()
    if len(role) < 2 or len(role) > 255:
        raise InvalidInterviewConfig("target_role must be 2-255 chars")
    if not (MIN_QUESTIONS <= int(question_count) <= MAX_QUESTIONS):
        raise InvalidInterviewConfig("question_count out of range")
    try:
        itype = interview_type if isinstance(interview_type, InterviewType) else InterviewType(str(interview_type))
    except ValueError:
        raise InvalidInterviewConfig("Invalid interview_type")
    try:
        diff = difficulty if isinstance(difficulty, DifficultyLevel) else DifficultyLevel(str(difficulty))
    except ValueError:
        raise InvalidInterviewConfig("Invalid difficulty")
    try:
        persona = interviewer_persona if isinstance(interviewer_persona, InterviewerPersona) else InterviewerPersona(str(interviewer_persona))
    except ValueError:
        raise InvalidInterviewConfig("Invalid interviewer_persona")
    lang = (programming_language or "").strip() or None
    if lang is not None and len(lang) > 128:
        raise InvalidInterviewConfig("programming_language too long")
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise InterviewNotFound("User not found or inactive")
    resume = None
    if resume_id is not None:
        resume = db.get(Resume, resume_id)
        if resume is None or resume.user_id != user_id:
            raise InterviewNotFound("Resume not found")
        if not resume.filename or not resume.storage_key:
            raise ResumeNotUsable("Resume is not usable")
    interview = Interview(user_id=user_id, resume_id=resume.id if resume else None, target_role=role, programming_language=lang, interview_type=itype.value, difficulty=diff.value, interviewer_persona=persona.value, total_questions=int(question_count), status=InterviewStatus.CREATED.value, current_question_index=0)
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return interview


def begin_preparation(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    transition_interview(db, interview, InterviewStatus.PREPARING, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def mark_ready(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewQuestion, InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) != InterviewStatus.PREPARING:
        from app.interviews.exceptions import InterviewNotReady

        raise InterviewNotReady("Interview must be PREPARING to become READY")
    count = db.scalar(select(func.count()).select_from(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id)) or 0
    if count == 0:
        from app.interviews.exceptions import InterviewNotReady

        raise InterviewNotReady("Cannot mark READY without persisted questions")
    transition_interview(db, interview, InterviewStatus.READY, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def start_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewQuestion, InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) != InterviewStatus.READY:
        from app.interviews.exceptions import InterviewNotReady

        raise InterviewNotReady("Only READY interviews can start")
    first = db.execute(select(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id).order_by(InterviewQuestion.order_index).limit(1)).scalar_one_or_none()
    if first is None:
        from app.interviews.exceptions import InterviewNotReady

        transition_interview(db, interview, InterviewStatus.FAILED, actor_user_id=user_id)
        db.commit()
        db.refresh(interview)
        raise InterviewNotReady("No persisted questions; interview marked FAILED")
    transition_interview(db, interview, InterviewStatus.IN_PROGRESS, actor_user_id=user_id)
    interview.current_question_index = int(first.order_index)
    db.add(interview)
    db.flush()
    transition_interview(db, interview, InterviewStatus.WAITING_FOR_ANSWER, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def list_interview_evaluations(db: Session, *, interview_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    """Read-only, ownership-checked evaluation projection for the API layer.

    Returns one row per persisted AnswerEvaluation (ordered by question order,
    then attempt). No rubric/metadata exposure; only the candidate-facing
    evaluation content itself.
    """
    from sqlalchemy import select

    from app.models.interview import Answer, AnswerEvaluation, InterviewQuestion

    interview = get_user_interview(db, interview_id, user_id)
    rows = db.execute(
        select(AnswerEvaluation, Answer, InterviewQuestion)
        .join(Answer, AnswerEvaluation.answer_id == Answer.id)
        .join(InterviewQuestion, Answer.question_id == InterviewQuestion.id)
        .where(InterviewQuestion.interview_id == interview.id)
        .order_by(InterviewQuestion.order_index.asc(), Answer.attempt_number.asc())
    ).all()
    return [
        {
            "answer_id": str(answer.id),
            "attempt_number": answer.attempt_number,
            "question_id": str(question.id),
            "order_index": question.order_index,
            "question_text": question.question_text,
            "question_type": str(question.question_type),
            "scores": {
                "correctness": ev.correctness_score,
                "relevance": ev.relevance_score,
                "completeness": ev.completeness_score,
                "technical_depth": ev.technical_depth_score,
                "technical_overall": ev.technical_overall,
                "clarity": ev.clarity_score,
                "structure": ev.structure_score,
                "conciseness": ev.conciseness_score,
                "communication_overall": ev.communication_overall,
            },
            "detail": ev.evaluation_detail or {},
            "evaluated_by": ev.evaluated_by,
            "created_at": ev.created_at.isoformat() if ev.created_at else None,
        }
        for ev, answer, question in rows
    ]


def get_current_question(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID):
    from app.models.interview import InterviewQuestion, InterviewStatus

    interview = get_user_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) not in (InterviewStatus.WAITING_FOR_ANSWER, InterviewStatus.IN_PROGRESS, InterviewStatus.FOLLOW_UP_REQUIRED, InterviewStatus.NEXT_QUESTION, InterviewStatus.EVALUATING):
        from app.interviews.exceptions import InterviewNotActive

        raise InterviewNotActive("Interview is not accepting answers in its current state")
    q = db.execute(select(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id, InterviewQuestion.order_index == interview.current_question_index).limit(1)).scalar_one_or_none()
    if q is None:
        from app.interviews.exceptions import InvalidCurrentQuestion

        raise InvalidCurrentQuestion("No current question for this interview state")
    return q


def set_current_answer(db: Session, *, user_id: uuid.UUID, question_id: uuid.UUID, answer_id: uuid.UUID):
    from app.models.interview import Answer, InterviewQuestion

    question = db.get(InterviewQuestion, question_id)
    if question is None:
        from app.interviews.exceptions import InvalidCurrentQuestion

        raise InvalidCurrentQuestion("Question not found")
    get_user_interview(db, question.interview_id, user_id)
    answer = db.get(Answer, answer_id)
    if answer is None or answer.question_id != question.id:
        from app.interviews.exceptions import InvalidCurrentQuestion

        raise InvalidCurrentQuestion("Answer does not belong to question")
    question.current_answer_id = answer.id
    db.add(question)
    db.flush()
    return question


def _hash_request(answer_text: str, question_id: uuid.UUID, time_taken) -> str:
    h = hashlib.sha256()
    h.update(str(question_id).encode())
    h.update(b"|")
    h.update(answer_text.encode())
    h.update(b"|")
    h.update(str(time_taken).encode())
    return h.hexdigest()


def submit_answer(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID, question_id: uuid.UUID, answer_text: str, idempotency_key: str, time_taken_seconds=None):
    from app.models.idempotency import AnswerIdempotencyKey
    from app.models.interview import Answer, InterviewQuestion, InterviewStatus

    text = (answer_text or "").strip()
    if len(text) < 1 or len(text) > 20000:
        from app.interviews.exceptions import InvalidAnswer

        raise InvalidAnswer("Answer must be 1-20000 chars")
    key = (idempotency_key or "").strip()
    if len(key) < 8 or len(key) > 128:
        from app.interviews.exceptions import InvalidAnswer

        raise InvalidAnswer("Invalid idempotency_key")
    interview = get_locked_interview(db, interview_id, user_id)
    question = db.get(InterviewQuestion, question_id)
    if question is None or question.interview_id != interview.id:
        from app.interviews.exceptions import InvalidCurrentQuestion

        raise InvalidCurrentQuestion("Question does not belong to interview")
    req_hash = _hash_request(text, question.id, time_taken_seconds)
    existing = db.execute(select(AnswerIdempotencyKey).where(AnswerIdempotencyKey.user_id == user_id, AnswerIdempotencyKey.interview_id == interview.id, AnswerIdempotencyKey.idempotency_key == key).limit(1)).scalar_one_or_none()
    if existing is not None:
        if existing.question_id != question.id or existing.request_hash != req_hash:
            from app.interviews.exceptions import DuplicateSubmission

            raise DuplicateSubmission("Idempotency key already used for a different payload")
        ans = db.get(Answer, existing.answer_id)
        return {"answer": ans, "is_duplicate": True, "status": _coerce_status(interview.status)}
    if _coerce_status(interview.status) not in (InterviewStatus.WAITING_FOR_ANSWER, InterviewStatus.FOLLOW_UP_REQUIRED):
        from app.interviews.exceptions import AnswerSubmissionRejected

        raise AnswerSubmissionRejected("Interview is not accepting an answer")
    if _coerce_status(interview.status) == InterviewStatus.FOLLOW_UP_REQUIRED:
        transition_interview(db, interview, InterviewStatus.WAITING_FOR_ANSWER, actor_user_id=user_id)
    if int(question.order_index) != int(interview.current_question_index):
        from app.interviews.exceptions import InvalidCurrentQuestion

        raise InvalidCurrentQuestion("Question is not the current question")

    max_attempt = db.scalar(select(func.max(Answer.attempt_number)).where(Answer.question_id == question.id)) or 0
    answer = Answer(question_id=question.id, attempt_number=int(max_attempt) + 1, answer_text=text, time_taken_seconds=time_taken_seconds)
    db.add(answer)
    db.flush()
    question.current_answer_id = answer.id
    db.add(question)
    db.flush()
    try:
        db.add(AnswerIdempotencyKey(user_id=user_id, interview_id=interview.id, question_id=question.id, idempotency_key=key, answer_id=answer.id, request_hash=req_hash))
        db.flush()
    except IntegrityError:
        db.rollback()
        locked = get_locked_interview(db, interview_id, user_id)
        row = db.execute(select(AnswerIdempotencyKey).where(AnswerIdempotencyKey.user_id == user_id, AnswerIdempotencyKey.interview_id == locked.id, AnswerIdempotencyKey.idempotency_key == key).limit(1)).scalar_one_or_none()
        if row is None:
            raise
        if row.question_id != question_id or row.request_hash != req_hash:
            from app.interviews.exceptions import DuplicateSubmission

            raise DuplicateSubmission("Idempotency key already used for a different payload")
        return {"answer": db.get(Answer, row.answer_id), "is_duplicate": True, "status": _coerce_status(locked.status)}
    transition_interview(db, interview, InterviewStatus.EVALUATING, actor_user_id=user_id)
    db.commit()
    db.refresh(answer)
    db.refresh(interview)
    return {"answer": answer, "is_duplicate": False, "status": _coerce_status(interview.status)}


def advance_after_evaluation(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID, needs_follow_up: bool) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) != InterviewStatus.EVALUATING:
        from app.interviews.exceptions import InterviewNotActive

        raise InterviewNotActive("Only EVALUATING interviews can advance")
    transition_interview(db, interview, InterviewStatus.FOLLOW_UP_REQUIRED if needs_follow_up else InterviewStatus.NEXT_QUESTION, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def move_to_next_question(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewQuestion, InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    cur = _coerce_status(interview.status)
    if cur == InterviewStatus.FOLLOW_UP_REQUIRED:
        transition_interview(db, interview, InterviewStatus.WAITING_FOR_ANSWER, actor_user_id=user_id)
        db.commit()
        db.refresh(interview)
        return interview
    if cur != InterviewStatus.NEXT_QUESTION:
        from app.interviews.exceptions import InterviewNotActive

        raise InterviewNotActive("Interview is not ready to move on")
    nxt = db.execute(select(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id, InterviewQuestion.order_index > interview.current_question_index).order_by(InterviewQuestion.order_index).limit(1)).scalar_one_or_none()
    if nxt is None:
        finish_interview(db, user_id=user_id, interview_id=interview.id, manual=False)
        return db.get(Interview, interview.id)
    interview.current_question_index = int(nxt.order_index)
    db.add(interview)
    db.flush()
    transition_interview(db, interview, InterviewStatus.WAITING_FOR_ANSWER, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def finish_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID, manual: bool = False) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    cur = _coerce_status(interview.status)
    if cur in (InterviewStatus.COMPLETED, InterviewStatus.REPORT_GENERATING, InterviewStatus.REPORT_READY):
        from app.interviews.exceptions import InterviewAlreadyCompleted

        raise InterviewAlreadyCompleted("Interview already completed")
    if cur not in (InterviewStatus.IN_PROGRESS, InterviewStatus.WAITING_FOR_ANSWER, InterviewStatus.EVALUATING, InterviewStatus.FOLLOW_UP_REQUIRED, InterviewStatus.NEXT_QUESTION):
        from app.interviews.exceptions import InterviewNotActive

        raise InterviewNotActive("Interview cannot be finished from its current state")
    # manual=True records an operator-initiated finish; completion itself is
    # still server-determined (completed_at + COMPLETED transition here).
    transition_interview(db, interview, InterviewStatus.COMPLETED, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def fail_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) == InterviewStatus.REPORT_READY:
        from app.interviews.exceptions import InvalidInterviewTransition

        raise InvalidInterviewTransition(interview.status, InterviewStatus.FAILED.value)
    transition_interview(db, interview, InterviewStatus.FAILED, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def begin_report(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) != InterviewStatus.COMPLETED:
        from app.interviews.exceptions import ReportNotEligible

        raise ReportNotEligible("Only COMPLETED interviews can begin reporting")
    transition_interview(db, interview, InterviewStatus.REPORT_GENERATING, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def complete_report(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID) -> Interview:
    from app.models.interview import InterviewStatus

    interview = get_locked_interview(db, interview_id, user_id)
    if _coerce_status(interview.status) != InterviewStatus.REPORT_GENERATING:
        from app.interviews.exceptions import ReportNotEligible

        raise ReportNotEligible("Report is not generating")
    transition_interview(db, interview, InterviewStatus.REPORT_READY, actor_user_id=user_id)
    db.commit()
    db.refresh(interview)
    return interview


def pause_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID):
    raise InterviewNotActive("Pause is not representable: no PAUSED state exists; client must retain position and resume via get_current_question; documented in docs/interview-state-machine.md")


def resume_interview(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID):
    interview = get_user_interview(db, interview_id, user_id)
    return {"interview": interview, "question": get_current_question(db, user_id=user_id, interview_id=interview.id) if _coerce_status(interview.status) in (InterviewStatus.WAITING_FOR_ANSWER, InterviewStatus.FOLLOW_UP_REQUIRED, InterviewStatus.NEXT_QUESTION, InterviewStatus.IN_PROGRESS, InterviewStatus.EVALUATING) else None}


def get_latest_follow_up(db: Session, *, user_id: uuid.UUID, interview_id: uuid.UUID):
    """Latest persisted follow-up for the CURRENT question (read-only).

    Used by the API layer to expose the follow-up prompt when the
    interview is in FOLLOW_UP_REQUIRED. Returns None when there is no
    current question or no follow-up has been generated for it.
    """
    from app.models.interview import InterviewFollowUp, InterviewQuestion

    interview = get_user_interview(db, interview_id, user_id)
    question = db.execute(
        select(InterviewQuestion)
        .where(InterviewQuestion.interview_id == interview.id, InterviewQuestion.order_index == interview.current_question_index)
        .limit(1)
    ).scalar_one_or_none()
    if question is None:
        return None
    return db.execute(
        select(InterviewFollowUp)
        .where(InterviewFollowUp.parent_question_id == question.id)
        .order_by(InterviewFollowUp.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()


def list_interview_transcript(db: Session, *, interview_id: uuid.UUID, user_id: uuid.UUID) -> list[dict]:
    """Ordered, read-only transcript for the owning user.

    Projects questions (with all answer attempts) and follow-ups so a
    refreshed client can reconstruct the conversation from the database.
    Never exposes question metadata (rubric, expected concepts).
    """
    from app.models.interview import Answer, InterviewFollowUp, InterviewQuestion

    interview = get_user_interview(db, interview_id, user_id)
    questions = db.execute(
        select(InterviewQuestion).where(InterviewQuestion.interview_id == interview.id).order_by(InterviewQuestion.order_index)
    ).scalars().all()
    transcript: list[dict] = []
    for q in questions:
        answers = db.execute(select(Answer).where(Answer.question_id == q.id).order_by(Answer.attempt_number)).scalars().all()
        follow_ups = db.execute(
            select(InterviewFollowUp).where(InterviewFollowUp.parent_question_id == q.id).order_by(InterviewFollowUp.created_at)
        ).scalars().all()
        transcript.append(
            {
                "question_id": str(q.id),
                "order_index": q.order_index,
                "question_type": str(q.question_type),
                "question_text": q.question_text,
                "is_current": int(q.order_index) == int(interview.current_question_index),
                "answers": [
                    {
                        "answer_id": str(a.id),
                        "attempt_number": a.attempt_number,
                        "answer_text": a.answer_text,
                        "created_at": a.created_at.isoformat() if a.created_at else None,
                    }
                    for a in answers
                ],
                "follow_ups": [
                    {
                        "follow_up_text": f.follow_up_text,
                        "reason": f.reason,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in follow_ups
                ],
            }
        )
    return transcript



