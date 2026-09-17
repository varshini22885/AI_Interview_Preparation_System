"""Service tests part 2: answers, idempotency, pointers, completion."""

import uuid

import pytest

from app.interviews import service as svc
from app.interviews.exceptions import AnswerSubmissionRejected, DuplicateSubmission, InvalidCurrentQuestion
from app.models.interview import Answer, InterviewQuestion, InterviewStatus
from tests.test_interview_service import _add_q, _create, _to_ready, _user


def _started(db_session, n=2):
    u = _user(db_session)
    iv = _create(db_session, u)
    _to_ready(db_session, u, iv, n=n)
    iv = svc.start_interview(db_session, user_id=u.id, interview_id=iv.id)
    q = svc.get_current_question(db_session, user_id=u.id, interview_id=iv.id)
    return u, iv, q


def test_submit_moves_to_evaluating(db_session):
    u, iv, q = _started(db_session)
    res = svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="Python lists are mutable.", idempotency_key="key-aaaa-1111")
    assert res["is_duplicate"] is False
    assert res["status"] == InterviewStatus.EVALUATING
    assert res["answer"].attempt_number == 1
    db_session.expire_all()
    qq = db_session.get(InterviewQuestion, q.id)
    assert qq.current_answer_id == res["answer"].id


def test_idempotent_retry_same_result(db_session):
    u, iv, q = _started(db_session)
    r1 = svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="Same text", idempotency_key="idem-key-1234")
    # interview now EVALUATING; move back to WAITING via legal path for retry simulation
    svc.advance_after_evaluation(db_session, user_id=u.id, interview_id=iv.id, needs_follow_up=True)
    svc.move_to_next_question(db_session, user_id=u.id, interview_id=iv.id)
    r2 = svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="Same text", idempotency_key="idem-key-1234")
    assert r2["is_duplicate"] is True
    assert r2["answer"].id == r1["answer"].id
    assert db_session.query(Answer).filter_by(question_id=q.id).count() == 1


def test_idempotency_key_different_payload_rejected(db_session):
    u, iv, q = _started(db_session)
    svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="First", idempotency_key="idem-key-9999")
    svc.advance_after_evaluation(db_session, user_id=u.id, interview_id=iv.id, needs_follow_up=True)
    svc.move_to_next_question(db_session, user_id=u.id, interview_id=iv.id)
    with pytest.raises(DuplicateSubmission):
        svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="Different", idempotency_key="idem-key-9999")


def test_stale_question_rejected(db_session):
    u, iv, q0 = _started(db_session, n=2)
    q1 = db_session.query(InterviewQuestion).filter(InterviewQuestion.interview_id == iv.id, InterviewQuestion.order_index == 1).one()
    with pytest.raises(InvalidCurrentQuestion):
        svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q1.id, answer_text="Wrong q", idempotency_key="key-stale-0001")


def test_foreign_question_rejected(db_session):
    u, iv, q = _started(db_session)
    other = _create(db_session, u)
    oq = _add_q(db_session, other, 0, "Other?")
    with pytest.raises(InvalidCurrentQuestion):
        svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=oq.id, answer_text="x", idempotency_key="key-foreign-01")


def test_second_submit_wrong_state_rejected(db_session):
    u, iv, q = _started(db_session)
    svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="A1", idempotency_key="key-one-11111")
    with pytest.raises(AnswerSubmissionRejected):
        svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="A2", idempotency_key="key-two-22222")


def test_current_answer_pointer_invariant(db_session):
    u, iv, q = _started(db_session)
    res = svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="A1", idempotency_key="key-ptr-00001")
    other_q = _add_q(db_session, iv, 99, "Other")
    with pytest.raises(InvalidCurrentQuestion):
        svc.set_current_answer(db_session, user_id=u.id, question_id=other_q.id, answer_id=res["answer"].id)


def test_finish_and_report_lifecycle(db_session):
    u, iv, q = _started(db_session)
    svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q.id, answer_text="A1", idempotency_key="key-fin-00001")
    svc.advance_after_evaluation(db_session, user_id=u.id, interview_id=iv.id, needs_follow_up=False)
    done = svc.move_to_next_question(db_session, user_id=u.id, interview_id=iv.id)
    # 2 questions: first answered, move goes to second question WAITING
    assert done.status == InterviewStatus.WAITING_FOR_ANSWER.value
    q2 = svc.get_current_question(db_session, user_id=u.id, interview_id=iv.id)
    svc.submit_answer(db_session, user_id=u.id, interview_id=iv.id, question_id=q2.id, answer_text="A2", idempotency_key="key-fin-00002")
    svc.advance_after_evaluation(db_session, user_id=u.id, interview_id=iv.id, needs_follow_up=False)
    fin = svc.move_to_next_question(db_session, user_id=u.id, interview_id=iv.id)
    assert fin.status == InterviewStatus.COMPLETED.value
    assert fin.completed_at is not None
    rg = svc.begin_report(db_session, user_id=u.id, interview_id=iv.id)
    assert rg.status == InterviewStatus.REPORT_GENERATING.value
    rr = svc.complete_report(db_session, user_id=u.id, interview_id=iv.id)
    assert rr.status == InterviewStatus.REPORT_READY.value
    with pytest.raises(Exception):
        svc.transition_interview(db_session, rr, InterviewStatus.IN_PROGRESS, actor_user_id=u.id)

