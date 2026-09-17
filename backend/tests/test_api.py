"""API integration tests with FastAPI TestClient."""

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
def _no_dispatch(monkeypatch):
    """API tests assert the HTTP contract (202 EVALUATING etc.) with the
    worker boundary stubbed; worker execution is covered by the inline
    pipeline test in test_interview_contract.py and by Playwright E2E."""
    import app.interviews.pipeline as pipeline

    monkeypatch.setattr(pipeline, "enqueue_question_generation", lambda **kw: None)
    monkeypatch.setattr(pipeline, "enqueue_answer_evaluation", lambda **kw: None)
    monkeypatch.setattr(pipeline, "enqueue_report_generation", lambda **kw: None)


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


def _register(email="u1@ex.com", password="password123"):
    r = client.post("/api/v1/auth/register", json={"email": email, "full_name": "U", "password": password})
    assert r.status_code == 201, r.text
    return r.json()


def _login(email="u1@ex.com", password="password123"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_ready_interview(user_id, interview_id, n=3):
    import uuid

    from app.db.base import SessionLocal
    from app.interviews import service as svc
    from app.models.interview import InterviewQuestion

    iv_uuid = uuid.UUID(str(interview_id))
    db = SessionLocal()
    try:
        for i in range(n):
            db.add(InterviewQuestion(interview_id=iv_uuid, order_index=i, question_text=f"Q{i}", question_type="TECHNICAL"))
        db.commit()
        from app.models.interview import Interview

        cur = db.get(Interview, iv_uuid)
        if str(cur.status) == "CREATED":
            svc.begin_preparation(db, user_id=user_id, interview_id=iv_uuid)
        svc.mark_ready(db, user_id=user_id, interview_id=iv_uuid)
    finally:
        db.close()


def test_health():
    assert client.get("/health/live").json()["status"] == "ok"
    assert client.get("/health/ready").status_code == 200


def test_register_duplicate():
    _register()
    r = client.post("/api/v1/auth/register", json={"email": "u1@ex.com", "full_name": "U", "password": "password123"})
    assert r.status_code == 409


def test_login_wrong_password():
    _register()
    r = client.post("/api/v1/auth/login", json={"email": "u1@ex.com", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_and_me():
    _register()
    tokens = _login()
    r = client.get("/api/v1/auth/me", headers=_auth(tokens["access_token"]))
    assert r.status_code == 200 and r.json()["email"] == "u1@ex.com"
    assert "hashed_password" not in str(r.json())


def test_refresh_rotation():
    _register()
    t = _login()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r.status_code == 200
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": t["refresh_token"]})
    assert r2.status_code == 401


def test_protected_route_requires_auth():
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get("/api/v1/interviews").status_code == 401


def test_error_contract_shape():
    _register()
    t = _login()
    r = client.get("/api/v1/interviews/00000000-0000-0000-0000-000000000000", headers=_auth(t["access_token"]))
    assert r.status_code == 404
    body = r.json().get("error")
    assert body and body["code"] == "INTERVIEW_NOT_FOUND" and body["request_id"]


def test_interview_flow():
    _register()
    t = _login()
    h = _auth(t["access_token"])
    r = client.post("/api/v1/interviews", headers=h, json={"target_role": "Backend Developer", "programming_language": "Python", "interview_type": "TECHNICAL", "difficulty": "MEDIUM", "interviewer_persona": "PROFESSIONAL", "question_count": 3})
    assert r.status_code == 201, r.text
    iv = r.json()
    iv_id = iv["id"]
    assert iv["status"] == "PREPARING"
    assert client.post(f"/api/v1/interviews/{iv_id}/start", headers=h).status_code == 409

    from app.db.base import SessionLocal
    from app.models.user import User

    u = SessionLocal().query(User).first()
    _seed_ready_interview(u.id, iv_id, n=3)
    s = client.post(f"/api/v1/interviews/{iv_id}/start", headers=h)
    assert s.status_code == 200, s.text
    assert s.json()["status"] == "WAITING_FOR_ANSWER"
    cur = client.get(f"/api/v1/interviews/{iv_id}/current", headers=h)
    assert cur.status_code == 200
    qid = cur.json()["question_id"]
    body = {"question_id": qid, "answer_text": "Python lists are mutable.", "idempotency_key": "api-key-0001"}
    a = client.post(f"/api/v1/interviews/{iv_id}/answers", headers={**h, "Idempotency-Key": "api-key-0001"}, json=body)
    assert a.status_code == 202, a.text
    assert a.json()["status"] == "EVALUATING"
    a2 = client.post(f"/api/v1/interviews/{iv_id}/answers", headers={**h, "Idempotency-Key": "api-key-0001"}, json=body)
    assert a2.status_code == 202
    assert a2.json()["answer_id"] == a.json()["answer_id"]


def test_cross_user_interview_hidden():
    _register("a@ex.com")
    ta = _login("a@ex.com")
    _register("b@ex.com")
    tb = _login("b@ex.com")
    r = client.post("/api/v1/interviews", headers=_auth(ta["access_token"]), json={"target_role": "Backend Developer", "question_count": 2})
    assert r.status_code == 201
    iv_id = r.json()["id"]
    rb = client.get(f"/api/v1/interviews/{iv_id}", headers=_auth(tb["access_token"]))
    assert rb.status_code == 404
    assert rb.json()["error"]["code"] == "INTERVIEW_NOT_FOUND"


def test_report_unavailable_then_available():
    _register()
    t = _login()
    h = _auth(t["access_token"])
    r = client.post("/api/v1/interviews", headers=h, json={"target_role": "Backend Developer", "question_count": 2})
    iv_id = r.json()["id"]
    rep = client.get(f"/api/v1/reports/{iv_id}", headers=h)
    assert rep.status_code in (404, 409)

    from app.db.base import SessionLocal
    from app.interviews import service as svc
    from app.models.interview import PerformanceReport
    from app.models.user import User

    import uuid

    iv_uuid = uuid.UUID(str(iv_id))
    db = SessionLocal()
    u = db.query(User).first()
    _seed_ready_interview(u.id, iv_uuid, n=2)

    svc.start_interview(db, user_id=u.id, interview_id=iv_uuid)
    # progress through EVALUATING -> NEXT_QUESTION -> COMPLETED (legal transitions)
    q = svc.get_current_question(db, user_id=u.id, interview_id=iv_uuid)
    svc.submit_answer(db, user_id=u.id, interview_id=iv_uuid, question_id=q.id, answer_text="answer text here", idempotency_key="rep-key-000001")
    svc.advance_after_evaluation(db, user_id=u.id, interview_id=iv_uuid, needs_follow_up=False)
    svc.finish_interview(db, user_id=u.id, interview_id=iv_uuid, manual=True)
    svc.begin_report(db, user_id=u.id, interview_id=iv_uuid)
    svc.complete_report(db, user_id=u.id, interview_id=iv_uuid)
    db.add(PerformanceReport(interview_id=iv_uuid, technical_score=75, communication_score=70, overall_score=72, total_questions_answered=2))
    db.commit()
    db.close()
    rep2 = client.get(f"/api/v1/reports/{iv_id}", headers=h)
    assert rep2.status_code == 200
    assert rep2.json()["overall_score"] == 72


def test_history_pagination_and_ownership():
    _register("a@ex.com")
    ta = _login("a@ex.com")
    _register("b@ex.com")
    tb = _login("b@ex.com")
    ha = _auth(ta["access_token"])
    for _ in range(3):
        client.post("/api/v1/interviews", headers=ha, json={"target_role": "Backend Developer", "question_count": 1})
    hist = client.get("/api/v1/history", headers=ha, params={"page": 1, "page_size": 2})
    assert hist.status_code == 200
    body = hist.json()
    assert body["total"] == 3 and len(body["items"]) == 2
    histb = client.get("/api/v1/history", headers=_auth(tb["access_token"]))
    assert histb.json()["total"] == 0


def test_resumes_ownership_and_validation():
    _register("a@ex.com")
    ta = _login("a@ex.com")
    _register("b@ex.com")
    tb = _login("b@ex.com")
    ha = _auth(ta["access_token"])
    hb = _auth(tb["access_token"])
    bad = client.post("/api/v1/resumes", headers=ha, files={"file": ("x.txt", b"hello", "text/plain")})
    assert bad.status_code == 422
    good = client.post("/api/v1/resumes", headers=ha, files={"file": ("r.pdf", b"%PDF-1.4 fake", "application/pdf")})
    assert good.status_code == 201, good.text
    rid = good.json()["id"]
    assert client.get(f"/api/v1/resumes/{rid}", headers=hb).status_code == 404
    assert client.delete(f"/api/v1/resumes/{rid}", headers=ha).status_code == 204


def test_roles_supported():
    _register()
    t = _login()
    r = client.get("/api/v1/roles", headers=_auth(t["access_token"]))
    assert r.status_code == 200
    roles = r.json()["items"]
    assert any(x["role"] == "Backend Developer" for x in roles)


def test_no_sensitive_fields_in_responses():
    _register()
    t = _login()
    h = _auth(t["access_token"])
    me = str(client.get("/api/v1/auth/me", headers=h).json())
    assert "hashed_password" not in me and "token_hash" not in me
    iv = client.post("/api/v1/interviews", headers=h, json={"target_role": "Backend Developer", "question_count": 1})
    assert "hashed_password" not in str(iv.json())


def test_validation_errors():
    _register()
    t = _login()
    h = _auth(t["access_token"])
    r = client.post("/api/v1/interviews", headers=h, json={"target_role": "Backend Developer", "question_count": 0})
    assert r.status_code == 422
    r2 = client.post("/api/v1/interviews", headers=h, json={"target_role": "x", "question_count": 1})
    assert r2.status_code == 422
