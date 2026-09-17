"""Contract tests for follow-up exposure + transcript endpoint.

Covers the two API gaps the frontend integration depends on:
- GET /interviews/{id}/current exposes the persisted follow-up prompt
  while the interview is FOLLOW_UP_REQUIRED (and answering it creates
  attempt 2 on the same question).
- GET /interviews/{id}/transcript returns the ordered read-only
  transcript (questions, answers, follow-ups), owner-only.
"""

import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef-xyz1234567890")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ["AI_PROVIDER"] = "test"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool

from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db.base import Base
    import app.models  # noqa: F401

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)

    import app.db.base as base_mod

    base_mod.engine = engine
    base_mod.SessionLocal = TestingSession

    yield

    Base.metadata.drop_all(engine)
    engine.dispose()


def _user(email="owner@ex.com"):
    client.post("/api/v1/auth/register", json={"email": email, "full_name": "O", "password": "password123"})
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def no_dispatch(monkeypatch):
    """Deterministic HTTP-contract tests: worker boundary stubbed so the
    test itself drives the state machine (simulating the async worker)."""
    import app.interviews.pipeline as pipeline

    monkeypatch.setattr(pipeline, "enqueue_question_generation", lambda **kw: None)
    monkeypatch.setattr(pipeline, "enqueue_answer_evaluation", lambda **kw: None)
    monkeypatch.setattr(pipeline, "enqueue_report_generation", lambda **kw: None)


def _seed_active_interview(token, n=2):
    """Create an interview, seed questions, start it (WAITING_FOR_ANSWER)."""
    import uuid

    from app.db.base import SessionLocal
    from app.models.interview import Interview, InterviewQuestion
    from app.models.user import User

    r = client.post(
        "/api/v1/interviews",
        json={"target_role": "Backend Developer", "interview_type": "TECHNICAL", "difficulty": "MEDIUM", "interviewer_persona": "PROFESSIONAL", "question_count": n},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    iv = r.json()
    with SessionLocal() as db:
        row = db.get(Interview, uuid.UUID(iv["id"]))
        row.status = "READY"
        for i in range(n):
            db.add(InterviewQuestion(interview_id=row.id, order_index=i, question_type="TECHNICAL", question_text=f"Question {i}"))
        db.commit()
        user = db.query(User).filter_by(email="owner@ex.com").one()
        user_id, iv_id = str(user.id), str(row.id)
    s = client.post(f"/api/v1/interviews/{iv_id}/start", headers=_auth(token))
    assert s.status_code == 200, s.text
    return user_id, iv_id


def _current(token, iv_id):
    return client.get(f"/api/v1/interviews/{iv_id}/current", headers=_auth(token))


def _submit(token, iv_id, question_id, text, key):
    return client.post(
        f"/api/v1/interviews/{iv_id}/answers",
        json={"question_id": question_id, "answer_text": text, "idempotency_key": key},
        headers={**_auth(token), "Idempotency-Key": key},
    )


def test_transcript_owner_only_and_ordered(no_dispatch):
    token = _user()
    _user("other@ex.com")
    _, iv_id = _seed_active_interview(token)
    cur = _current(token, iv_id).json()
    _submit(token, iv_id, cur["question_id"], "My answer text", "idem-transcript-1")

    r = client.get(f"/api/v1/interviews/{iv_id}/transcript", headers=_auth(token))
    assert r.status_code == 200, r.text
    items = r.json()
    assert [i["order_index"] for i in items] == [0, 1]
    assert items[0]["question_text"] == "Question 0"
    assert items[0]["is_current"] is True
    assert items[1]["is_current"] is False
    assert len(items[0]["answers"]) == 1
    assert items[0]["answers"][0]["attempt_number"] == 1
    assert items[0]["answers"][0]["answer_text"] == "My answer text"
    assert items[1]["answers"] == []
    # No internal metadata leakage
    assert "question_metadata" not in items[0]
    assert "rubric" not in str(items).lower()

    # Cross-user access must not reveal existence
    other = client.post("/api/v1/auth/login", json={"email": "other@ex.com", "password": "password123"}).json()["access_token"]
    assert client.get(f"/api/v1/interviews/{iv_id}/transcript", headers=_auth(other)).status_code == 404


def test_full_inline_pipeline_loop():
    """Real end-to-end backend loop with the deterministic test AI provider.

    POST /interviews dispatches question generation -> READY; start ->
    current question; answer -> EVALUATING then worker advances;
    finish -> COMPLETED -> report dispatch -> REPORT_READY with real
    persisted scores. Proves the dispatch points + UUID coercion work.
    """
    import app.workers as workers_mod

    # Inline pipeline must run against the same fixture engine.
    from app.db.base import SessionLocal as _Fix  # noqa: F401  (sanity import)

    workers_mod.SessionLocal = _Fix

    token = _user()
    r = client.post(
        "/api/v1/interviews",
        json={"target_role": "Backend Developer", "interview_type": "TECHNICAL", "difficulty": "MEDIUM", "interviewer_persona": "PROFESSIONAL", "question_count": 2},
        headers=_auth(token),
    )
    assert r.status_code == 201, r.text
    iv = r.json()
    # Inline worker generated real questions via the test provider and marked READY.
    assert iv["status"] == "READY", iv

    s = client.post(f"/api/v1/interviews/{iv['id']}/start", headers=_auth(token))
    assert s.status_code == 200, s.text
    assert s.json()["status"] == "WAITING_FOR_ANSWER"

    cur = _current(token, iv["id"]).json()
    assert cur["answer_allowed"] is True
    assert cur["question_text"], cur

    sub = _submit(token, iv["id"], cur["question_id"], "An answer exercising the deterministic provider.", "idem-e2e-loop-1")
    assert sub.status_code == 202, sub.text

    after = client.get(f"/api/v1/interviews/{iv['id']}", headers=_auth(token)).json()
    # Worker ran inline: interview advanced out of EVALUATING.
    assert after["status"] in ("FOLLOW_UP_REQUIRED", "WAITING_FOR_ANSWER", "NEXT_QUESTION", "COMPLETED"), after

    evs = client.get(f"/api/v1/interviews/{iv['id']}/evaluations", headers=_auth(token))
    assert evs.status_code == 200, evs.text
    assert len(evs.json()) == 1
    scores = evs.json()[0]["scores"]
    assert set(scores) == {"correctness", "relevance", "completeness", "technical_depth", "technical_overall", "clarity", "structure", "conciseness", "communication_overall"}

    fin = client.post(f"/api/v1/interviews/{iv['id']}/finish", headers=_auth(token))
    assert fin.status_code == 200, fin.text
    assert fin.json()["status"] == "COMPLETED"

    rep = client.get(f"/api/v1/reports/{iv['id']}", headers=_auth(token))
    assert rep.status_code == 200, rep.text
    body = rep.json()
    assert body["status"] == "REPORT_READY"
    for field in ("technical_score", "communication_score", "overall_score", "total_questions_answered"):
        assert body[field] is not None
    assert 0 <= body["overall_score"] <= 100


def test_current_exposes_follow_up_and_attempt_two(no_dispatch):
    import uuid
    from datetime import datetime, timezone

    from app.db.base import SessionLocal
    from app.interviews import service as svc
    from app.models.interview import Interview, InterviewFollowUp

    token = _user()
    user_id, iv_id = _seed_active_interview(token)
    cur = _current(token, iv_id).json()
    r = _submit(token, iv_id, cur["question_id"], "Answer one", "idem-followup-1")
    assert r.status_code == 202, r.text
    assert r.json()["attempt_number"] == 1

    # Simulate the evaluation worker deciding a follow-up is required
    with SessionLocal() as db:
        svc.advance_after_evaluation(db, user_id=uuid.UUID(user_id), interview_id=uuid.UUID(iv_id), needs_follow_up=True)
        db.add(InterviewFollowUp(parent_question_id=uuid.UUID(cur["question_id"]), follow_up_text="Can you make this more specific?", reason="missing concept", created_at=datetime.now(timezone.utc)))
        db.commit()

    cur2 = _current(token, iv_id).json()
    assert cur2["status"] == "FOLLOW_UP_REQUIRED"
    assert cur2["answer_allowed"] is True
    assert cur2["follow_up"]["follow_up_text"] == "Can you make this more specific?"
    assert cur2["follow_up"]["reason"] == "missing concept"

    # Answering the follow-up: same question, attempt 2, EVALUATING
    r2 = _submit(token, iv_id, cur["question_id"], "Answer two with more detail", "idem-followup-2")
    assert r2.status_code == 202, r2.text
    body = r2.json()
    assert body["attempt_number"] == 2
    assert body["answer_id"] != r.json()["answer_id"]
    assert body["status"] == "EVALUATING"
