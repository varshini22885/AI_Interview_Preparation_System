"""Real DB tests for interview domain: relationships, cascades, constraints."""

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.interview import Answer, AnswerEvaluation, Interview, InterviewFeedback, InterviewFollowUp, InterviewQuestion, InterviewStatus, PerformanceReport
from app.models.resume import Resume
from app.models.user import User


def _user(db_session, email="u@example.com"):
    u = User(email=email, full_name="Test User", hashed_password="x" * 60)
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _resume(db_session, user):
    r = Resume(user_id=user.id, filename="r.pdf", content_type="application/pdf", size_bytes=10, storage_key=f"k-{uuid.uuid4().hex}")
    db_session.add(r)
    db_session.commit()
    db_session.refresh(r)
    return r


def _interview(db_session, user, resume=None):
    iv = Interview(user_id=user.id, resume_id=resume.id if resume else None, target_role="Backend Developer", programming_language="Python", total_questions=5)
    db_session.add(iv)
    db_session.commit()
    db_session.refresh(iv)
    return iv


def _eval_kwargs(**over):
    base = dict(correctness_score=8, relevance_score=7, completeness_score=6, technical_depth_score=7, technical_overall=7, clarity_score=5, structure_score=6, conciseness_score=7, communication_overall=6)
    base.update(over)
    return base


def test_full_interview_graph_persists(db_session):
    u = _user(db_session)
    r = _resume(db_session, u)
    iv = _interview(db_session, u, r)
    assert iv.status == InterviewStatus.CREATED.value
    q = InterviewQuestion(interview_id=iv.id, order_index=0, question_type="TECHNICAL", question_text="What is a list vs tuple?", question_metadata={"expected_concepts": ["mutability"]})
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    a = Answer(question_id=q.id, attempt_number=1, answer_text="List mutable, tuple immutable.")
    db_session.add(a)
    db_session.commit()
    db_session.refresh(a)
    q.current_answer_id = a.id
    ev = AnswerEvaluation(answer_id=a.id, **_eval_kwargs(), evaluation_detail={"missing_concepts": []}, evaluated_by="test")
    db_session.add(ev)
    fu = InterviewFollowUp(parent_question_id=q.id, triggering_answer_id=a.id, follow_up_text="When choose tuple?", reason="probe depth")
    db_session.add(fu)
    fb = InterviewFeedback(interview_id=iv.id, strengths="clear", areas_for_improvement="depth", detailed_feedback="good")
    db_session.add(fb)
    rep = PerformanceReport(interview_id=iv.id, technical_score=75, communication_score=60, overall_score=68, total_questions_answered=1)
    db_session.add(rep)
    db_session.commit()
    db_session.expire_all()
    got = db_session.get(Interview, iv.id)
    assert got.resume.id == r.id
    assert len(got.questions) == 1
    assert got.questions[0].answers[0].evaluation.correctness_score == 8
    assert got.questions[0].follow_ups[0].follow_up_text.startswith("When")
    assert got.feedback.strengths == "clear"
    assert got.performance_report.overall_score == 68


def test_technical_vs_communication_separable(db_session):
    u = _user(db_session, "sep@example.com")
    iv = _interview(db_session, u)
    q = InterviewQuestion(interview_id=iv.id, order_index=0, question_text="Q?")
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    a1 = Answer(question_id=q.id, attempt_number=1, answer_text="correct but rambling")
    db_session.add(a1)
    db_session.commit()
    db_session.refresh(a1)
    db_session.add(AnswerEvaluation(answer_id=a1.id, **_eval_kwargs(correctness_score=10, technical_overall=9, clarity_score=3, communication_overall=3)))
    db_session.commit()
    got = db_session.query(AnswerEvaluation).filter_by(answer_id=a1.id).one()
    assert got.technical_overall - got.communication_overall >= 5


def test_unique_question_order_enforced(db_session):
    u = _user(db_session, "u2@example.com")
    iv = _interview(db_session, u)
    db_session.add(InterviewQuestion(interview_id=iv.id, order_index=0, question_text="A"))
    db_session.commit()
    db_session.add(InterviewQuestion(interview_id=iv.id, order_index=0, question_text="B"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_unique_answer_attempt_enforced(db_session):
    u = _user(db_session, "u3@example.com")
    iv = _interview(db_session, u)
    q = InterviewQuestion(interview_id=iv.id, order_index=0, question_text="A")
    db_session.add(q)
    db_session.commit()
    db_session.refresh(q)
    db_session.add(Answer(question_id=q.id, attempt_number=1, answer_text="x"))
    db_session.commit()
    db_session.add(Answer(question_id=q.id, attempt_number=1, answer_text="y"))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


