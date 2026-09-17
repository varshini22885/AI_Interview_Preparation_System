"""Stable error contract + domain->HTTP mapping (no secrets in bodies)."""

import uuid

from fastapi import Request
from fastapi.responses import JSONResponse


def error_body(code: str, message: str, request_id: str) -> dict:
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def domain_to_http(exc: Exception) -> tuple[int, str]:
    from app.ai.exceptions import AIConfigurationError, AIFallbackExhausted, AIProviderError, AIValidationError
    from app.auth.exceptions import EmailAlreadyRegistered, InvalidCredentials, InvalidRefreshToken, UserInactive
    from app.interviews.exceptions import (
        AnswerSubmissionRejected,
        DuplicateSubmission,
        InterviewAccessDenied,
        InterviewAlreadyCompleted,
        InterviewNotActive,
        InterviewNotFound,
        InterviewNotReady,
        InvalidAnswer,
        InvalidCurrentQuestion,
        InvalidInterviewConfig,
        InvalidInterviewTransition,
        ReportNotEligible,
        ResumeNotUsable,
    )

    if isinstance(exc, InterviewNotFound):
        return 404, "INTERVIEW_NOT_FOUND"
    if isinstance(exc, InterviewAccessDenied):
        return 404, "INTERVIEW_NOT_FOUND"
    if isinstance(exc, InvalidInterviewTransition):
        return 409, "INVALID_TRANSITION"
    if isinstance(exc, InterviewNotReady):
        return 409, "INTERVIEW_NOT_READY"
    if isinstance(exc, InterviewAlreadyCompleted):
        return 409, "ALREADY_COMPLETED"
    if isinstance(exc, InterviewNotActive):
        return 409, "INTERVIEW_NOT_ACTIVE"
    if isinstance(exc, InvalidCurrentQuestion):
        return 409, "INVALID_CURRENT_QUESTION"
    if isinstance(exc, DuplicateSubmission):
        return 409, "DUPLICATE_SUBMISSION"
    if isinstance(exc, InvalidAnswer):
        return 422, "INVALID_ANSWER"
    if isinstance(exc, AnswerSubmissionRejected):
        return 409, "ANSWER_REJECTED"
    if isinstance(exc, ResumeNotUsable):
        return 409, "RESUME_NOT_USABLE"
    if isinstance(exc, InvalidInterviewConfig):
        return 422, "INVALID_CONFIG"
    if isinstance(exc, ReportNotEligible):
        return 409, "REPORT_NOT_READY"
    if isinstance(exc, EmailAlreadyRegistered):
        return 409, "EMAIL_REGISTERED"
    if isinstance(exc, InvalidCredentials):
        return 401, "INVALID_CREDENTIALS"
    if isinstance(exc, InvalidRefreshToken):
        return 401, "INVALID_REFRESH"
    if isinstance(exc, UserInactive):
        return 403, "USER_INACTIVE"
    if isinstance(exc, AIConfigurationError):
        return 503, "AI_NOT_CONFIGURED"
    if isinstance(exc, (AIProviderError, AIValidationError, AIFallbackExhausted)):
        return 502, "AI_PROVIDER_ERROR"
    return 500, "INTERNAL_ERROR"


async def domain_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from app.ai.exceptions import AIError
    from app.auth.exceptions import AuthError
    from app.interviews.exceptions import InterviewDomainError

    if not isinstance(exc, (InterviewDomainError, AuthError, AIError)):
        raise exc
    status, code = domain_to_http(exc)
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    safe_message = str(exc) if status < 500 else "Internal error."
    if status >= 500:
        safe_message = "The service encountered an error."
    return JSONResponse(status_code=status, content=error_body(code, safe_message, request_id))
