"""Second half of interview domain DB tests (helpers imported from sibling module)."""
import uuid
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.interview import Answer, AnswerEvaluation, Interview, InterviewFeedback, InterviewFollowUp, InterviewQuestion, PerformanceReport
from app.models.resume import Resume
from app.models.user import User
from tests.test_interview_models import _user, _resume, _interview, _eval_kwargs


def test_one_evaluation_per_answer(db_session):
    u = _user(db_session, "u4@example.com")
    iv = _interview(db_session, u)
    q = InterviewQuestion(interview_id=iv.id, order_index=0, question_text="A")
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    a = Answer(question_id=q.id, attempt_number=1, answer_text="x")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    db_session.add(AnswerEvaluation(answer_id=a.id, **_eval_kwargs()))
    db_session.commit()
    db_session.add(AnswerEvaluation(answer_id=a.id, **_eval_kwargs()))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_cascade_delete_interview(db_session):
    u = _user(db_session, "u5@example.com")
    iv = _interview(db_session, u)
    q = InterviewQuestion(interview_id=iv.id, order_index=0, question_text="A")
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    a = Answer(question_id=q.id, attempt_number=1, answer_text="x")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    db_session.add(AnswerEvaluation(answer_id=a.id, **_eval_kwargs()))
    db_session.add(InterviewFollowUp(parent_question_id=q.id, follow_up_text="F?"))
    db_session.add(InterviewFeedback(interview_id=iv.id, strengths="s"))
    db_session.add(PerformanceReport(interview_id=iv.id, technical_score=10, communication_score=10, overall_score=10, total_questions_answered=1))
    db_session.commit()
    db_session.delete(db_session.get(Interview, iv.id))
    db_session.commit()
    assert db_session.query(InterviewQuestion).count() == 0
    assert db_session.query(Answer).count() == 0
    assert db_session.query(AnswerEvaluation).count() == 0
    assert db_session.query(InterviewFollowUp).count() == 0
    assert db_session.query(InterviewFeedback).count() == 0
    assert db_session.query(PerformanceReport).count() == 0


def test_resume_delete_sets_interview_resume_null(db_session):
    u = _user(db_session, "u6@example.com")
    r = _resume(db_session, u)
    iv = _interview(db_session, u, r)
    db_session.delete(r)
    db_session.commit()
    db_session.expire_all()
    assert db_session.get(Interview, iv.id).resume_id is None
