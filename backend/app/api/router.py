"""Versioned router aggregation (no business logic)."""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.interviews import router as interviews_router
from app.api.resources import history_router, reports_router, resumes_router, roles_router, users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(resumes_router)
api_router.include_router(roles_router)
api_router.include_router(interviews_router)
api_router.include_router(reports_router)
api_router.include_router(history_router)
