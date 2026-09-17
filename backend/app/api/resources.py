"""Users, resumes, roles, reports, history routers (thin)."""

import uuid

from fastapi import APIRouter, Depends, Query, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_request_id, rate_limit_guard
from app.db.base import get_db

users_router = APIRouter(prefix="/users", tags=["Users"])
resumes_router = APIRouter(prefix="/resumes", tags=["Resumes"])
roles_router = APIRouter(prefix="/roles", tags=["Roles"])
reports_router = APIRouter(prefix="/reports", tags=["Reports"])
history_router = APIRouter(prefix="/history", tags=["History"])


@users_router.get("/me", summary="My profile")
def my_profile(user=Depends(get_current_user)):
    return {"id": str(user.id), "email": user.email, "full_name": user.full_name, "is_active": user.is_active, "created_at": user.created_at.isoformat() if user.created_at else None}


@resumes_router.post("", status_code=201, summary="Upload resume")
def upload_resume(request: Request, file: UploadFile, db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    import uuid as _uuid

    from sqlalchemy.exc import IntegrityError

    from app.core.config import get_settings
    from app.models.resume import Resume
    from app.storage import get_storage

    rate_limit_guard(request, "upload")
    settings = get_settings()
    name = file.filename or "resume"
    ext = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext not in settings.ALLOWED_UPLOAD_EXTENSIONS:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"error": {"code": "INVALID_FILE", "message": "Unsupported file type."}})
    data = file.file.read()
    if len(data) > settings.MAX_UPLOAD_SIZE_BYTES:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail={"error": {"code": "FILE_TOO_LARGE", "message": "File exceeds size limit."}})
    key = f"{user.id}/{_uuid.uuid4().hex}{ext or '.pdf'}"
    stored = get_storage().save(key=key, data=data, content_type=file.content_type or "application/octet-stream")
    row = Resume(user_id=user.id, filename=name[:512], content_type=stored.content_type[:128], size_bytes=stored.size_bytes, storage_key=stored.storage_key)
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        from fastapi import HTTPException

        raise HTTPException(status_code=409, detail={"error": {"code": "RESUME_CONFLICT", "message": "Resume could not be stored."}})
    db.refresh(row)
    if not settings.DATABASE_URL.startswith("sqlite"):
        from app.interviews.pipeline import enqueue_resume_processing

        enqueue_resume_processing(resume_id=row.id)
    return {"id": str(row.id), "filename": row.filename, "content_type": row.content_type, "size_bytes": row.size_bytes, "status": row.status, "created_at": row.created_at.isoformat() if row.created_at else None, "parsed_at": row.parsed_at.isoformat() if row.parsed_at else None}


@resumes_router.get("", summary="List my resumes")
def list_resumes(request: Request, page: int = Query(ge=1, default=1), page_size: int = Query(ge=1, le=100, default=20), db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    from sqlalchemy import func, select

    from app.models.resume import Resume

    total = db.scalar(select(func.count()).select_from(Resume).where(Resume.user_id == user.id)) or 0
    rows = db.execute(select(Resume).where(Resume.user_id == user.id).order_by(Resume.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return {"items": [{"id": str(r.id), "filename": r.filename, "content_type": r.content_type, "size_bytes": r.size_bytes, "status": r.status, "created_at": r.created_at.isoformat() if r.created_at else None, "parsed_at": r.parsed_at.isoformat() if r.parsed_at else None} for r in rows], "page": page, "page_size": page_size, "total": total}


@resumes_router.get("/{resume_id}", summary="Resume detail")
def get_resume(resume_id: uuid.UUID, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    from fastapi import HTTPException

    from app.models.resume import Resume

    row = db.get(Resume, resume_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail={"error": {"code": "RESUME_NOT_FOUND", "message": "Resume was not found."}})
    return {"id": str(row.id), "filename": row.filename, "content_type": row.content_type, "size_bytes": row.size_bytes, "status": row.status, "created_at": row.created_at.isoformat() if row.created_at else None, "parsed_at": row.parsed_at.isoformat() if row.parsed_at else None}


@resumes_router.delete("/{resume_id}", status_code=204, summary="Delete resume")
def delete_resume(resume_id: uuid.UUID, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    from fastapi import HTTPException

    from app.models.resume import Resume
    from app.storage import get_storage

    row = db.get(Resume, resume_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail={"error": {"code": "RESUME_NOT_FOUND", "message": "Resume was not found."}})
    get_storage().delete(key=row.storage_key)
    db.delete(row)
    db.commit()
    return None


@roles_router.get("", summary="Supported roles")
def list_roles():
    return {"items": [
        {"role": "Backend Developer", "interview_types": ["TECHNICAL", "BEHAVIORAL", "MIXED"], "difficulties": ["EASY", "MEDIUM", "HARD"], "languages": ["Python", "Java", "Go"]},
        {"role": "Frontend Developer", "interview_types": ["TECHNICAL", "BEHAVIORAL", "MIXED"], "difficulties": ["EASY", "MEDIUM", "HARD"], "languages": ["JavaScript", "TypeScript"]},
        {"role": "Full Stack Developer", "interview_types": ["TECHNICAL", "BEHAVIORAL", "MIXED"], "difficulties": ["EASY", "MEDIUM", "HARD"], "languages": ["Python", "JavaScript"]},
        {"role": "Data Analyst", "interview_types": ["TECHNICAL", "BEHAVIORAL", "MIXED"], "difficulties": ["EASY", "MEDIUM"], "languages": ["Python", "SQL"]},
    ]}


@reports_router.get("/{interview_id}", summary="Persisted report only")
def get_report(interview_id: uuid.UUID, request: Request, db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    from fastapi import HTTPException

    from app.interviews import service as svc
    from app.models.interview import InterviewStatus, PerformanceReport

    iv = svc.get_user_interview(db, interview_id, user.id)
    status = str(iv.status)
    if status != InterviewStatus.REPORT_READY.value:
        raise HTTPException(status_code=409 if status in (InterviewStatus.COMPLETED.value, InterviewStatus.REPORT_GENERATING.value) else 404, detail={"error": {"code": "REPORT_NOT_READY", "message": f"Report unavailable while interview is {status}."}})
    row = db.query(PerformanceReport).filter_by(interview_id=iv.id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"error": {"code": "REPORT_NOT_FOUND", "message": "Report was not found."}})
    from app.models.interview import InterviewFeedback

    feedback = db.query(InterviewFeedback).filter_by(interview_id=iv.id).one_or_none()
    return {"interview_id": str(iv.id), "status": status, "technical_score": row.technical_score, "communication_score": row.communication_score, "overall_score": row.overall_score, "total_questions_answered": row.total_questions_answered, "strengths": feedback.strengths if feedback else None, "areas_for_improvement": feedback.areas_for_improvement if feedback else None}


@history_router.get("", summary="Interview history")
def history(request: Request, page: int = Query(ge=1, default=1), page_size: int = Query(ge=1, le=100, default=20), role: str | None = Query(default=None, max_length=255), interview_type: str | None = Query(default=None, pattern="^(TECHNICAL|BEHAVIORAL|MIXED)$"), difficulty: str | None = Query(default=None, pattern="^(EASY|MEDIUM|HARD|EXPERT)$"), db: Session = Depends(get_db), user=Depends(get_current_user), _rid: str = Depends(get_request_id)):
    from sqlalchemy import func, select

    from app.models.interview import Interview, PerformanceReport

    stmt = select(Interview).where(Interview.user_id == user.id)
    count_stmt = select(func.count()).select_from(Interview).where(Interview.user_id == user.id)
    if role:
        stmt = stmt.where(Interview.target_role == role)
        count_stmt = count_stmt.where(Interview.target_role == role)
    if interview_type:
        stmt = stmt.where(Interview.interview_type == interview_type)
        count_stmt = count_stmt.where(Interview.interview_type == interview_type)
    if difficulty:
        stmt = stmt.where(Interview.difficulty == difficulty)
        count_stmt = count_stmt.where(Interview.difficulty == difficulty)
    total = db.scalar(count_stmt) or 0
    rows = db.execute(stmt.order_by(Interview.created_at.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = []
    for iv in rows:
        rep = db.query(PerformanceReport).filter_by(interview_id=iv.id).one_or_none()
        items.append({"id": str(iv.id), "status": str(iv.status), "target_role": iv.target_role, "interview_type": str(iv.interview_type), "difficulty": str(iv.difficulty), "total_questions": iv.total_questions, "completed_at": iv.completed_at.isoformat() if iv.completed_at else None, "overall_score": rep.overall_score if rep else None})
    return {"items": items, "page": page, "page_size": page_size, "total": total}

