"""Service tests: state machine + ownership + lifecycle + idempotency."""

import uuid

import pytest
from sqlalchemy import select

from app.interviews import service as svc
from app.interviews.exceptions import (
    AnswerSubmissionRejected,
    DuplicateSubmission,
    InterviewNotFound,
    InterviewNotReady,
    InvalidCurrentQuestion,
    InvalidInterviewConfig,
    InvalidInterviewTransition,
)
from app.models.interview import InterviewQuestion, InterviewStatus
from app.models.resume import Resume
from app.models.user import User


def _user(db_session, email=None, active=True):
    email = email or f"u-{uuid.uuid4().hex[:8]}@ex.com"
    u = User(email=email, full_name="U", hashed_password="x" * 60, is_active=active)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _resume(db_session, user):
    r = Resume(user_id=user.id, filename="r.pdf", content_type="application/pdf", size_bytes=5, storage_key=f"k-{uuid.uuid4().hex}")
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


def _create(db_session, user, resume=None, **kw):
    args = dict(user_id=user.id, resume_id=resume.id if resume else None, target_role="Backend Dev", programming_language="Python", interview_type="MIXED", difficulty="MEDIUM", interviewer_persona="PROFESSIONAL", question_count=3)
    args.update(kw)
    return svc.create_interview(db_session, **args)


def _add_q(db_session, interview, idx=0, text="Q?"):
    q = InterviewQuestion(interview_id=interview.id, order_index=idx, question_text=text)
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    return q


def _to_ready(db_session, user, interview, n=2):
    for i in range(n):
        _add_q(db_session, interview, i, f"Q{i}")
    svc.begin_preparation(db_session, user_id=user.id, interview_id=interview.id)
    return svc.mark_ready(db_session, user_id=user.id, interview_id=interview.id)


def test_create_defaults_to_created(db_session):
    u = _user(db_session)
    r = _resume(db_session, u)
    iv = _create(db_session, u, r)
    assert iv.status == InterviewStatus.CREATED.value
    assert iv.total_questions == 3


def test_create_rejects_bad_config(db_session):
    u = _user(db_session)
    with pytest.raises(InvalidInterviewConfig):
        _create(db_session, u, question_count=0)
    with pytest.raises(InvalidInterviewConfig):
        _create(db_session, u, difficulty="NOPE")
    with pytest.raises(InvalidInterviewConfig):
        _create(db_session, u, target_role="x")


def test_create_rejects_foreign_resume(db_session):
    a = _user(db_session)
    b = _user(db_session)
    r = _resume(db_session, b)
    with pytest.raises(InterviewNotFound):
        _create(db_session, a, r)


def test_cross_user_access_hidden(db_session):
    a = _user(db_session)
    b = _user(db_session)
    iv = _create(db_session, a)
    with pytest.raises(InterviewNotFound):
        svc.get_user_interview(db_session, iv.id, b.id)
    with pytest.raises(InterviewNotFound):
        svc.start_interview(db_session, user_id=b.id, interview_id=iv.id)


def test_preparation_requires_questions(db_session):
    u = _user(db_session)
    iv = _create(db_session, u)
    svc.begin_preparation(db_session, user_id=u.id, interview_id=iv.id)
    with pytest.raises(InterviewNotReady):
        svc.mark_ready(db_session, user_id=u.id, interview_id=iv.id)


def test_start_requires_ready(db_session):
    u = _user(db_session)
    iv = _create(db_session, u)
    _add_q(db_session, iv, 0)
    with pytest.raises(InterviewNotReady):
        svc.start_interview(db_session, user_id=u.id, interview_id=iv.id)


def test_start_sets_waiting_and_index(db_session):
    u = _user(db_session)
    iv = _create(db_session, u)
    _to_ready(db_session, u, iv, n=2)
    out = svc.start_interview(db_session, user_id=u.id, interview_id=iv.id)
    assert out.status == InterviewStatus.WAITING_FOR_ANSWER.value
    assert out.started_at is not None
    assert out.current_question_index == 0
    q = svc.get_current_question(db_session, user_id=u.id, interview_id=iv.id)
    assert q.order_index == 0


def test_illegal_transition_blocked(db_session):
    u = _user(db_session)
    iv = _create(db_session, u)
    with pytest.raises(InvalidInterviewTransition):
        svc.transition_interview(db_session, iv, InterviewStatus.REPORT_READY, actor_user_id=u.id)
    db_session.rollback()
    with pytest.raises(InvalidInterviewTransition):
        svc.transition_interview(db_session, iv, InterviewStatus.IN_PROGRESS, actor_user_id=u.id)
    db_session.rollback()


def test_all_legal_transitions(db_session):
    from app.interviews.state_machine import ALLOWED_TRANSITIONS

    u = _user(db_session)
    for cur, targets in ALLOWED_TRANSITIONS.items():
        for tgt in targets:
            iv = _create(db_session, u)
            iv.status = cur.value
            db_session.add(iv)
            db_session.commit()
            svc.transition_interview(db_session, iv, tgt, actor_user_id=u.id)
            assert iv.status == tgt.value
            db_session.rollback()

