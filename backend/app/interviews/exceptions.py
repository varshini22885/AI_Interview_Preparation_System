"""Domain-specific exceptions for the interview service layer.

Framework-independent: no FastAPI/HTTP imports here. The future
HTTP API layer will map these to status codes.
"""


class InterviewDomainError(Exception):
    """Base class for all interview domain errors."""


class InterviewNotFound(InterviewDomainError):
    """Raised when an interview cannot be returned.

    Used for both genuinely-missing and cross-user resources so
    callers cannot probe for another user's interview existence.
    """


class InterviewAccessDenied(InterviewDomainError):
    """Explicit denial (internal use); public API prefers InterviewNotFound."""


class InvalidInterviewTransition(InterviewDomainError):
    def __init__(self, current: str, target: str) -> None:
        super().__init__(f"Illegal transition {current!r} -> {target!r}")
        self.current = current
        self.target = target


class InterviewNotReady(InterviewDomainError):
    pass


class InterviewAlreadyCompleted(InterviewDomainError):
    pass


class InterviewNotActive(InterviewDomainError):
    pass


class InvalidCurrentQuestion(InterviewDomainError):
    pass


class AnswerSubmissionRejected(InterviewDomainError):
    pass


class DuplicateSubmission(AnswerSubmissionRejected):
    """Same idempotency key resubmitted with a *different* payload."""

    def __init__(self, message: str = "Duplicate submission with different payload") -> None:
        super().__init__(message)


class InvalidAnswer(AnswerSubmissionRejected):
    pass


class InvalidInterviewConfig(InterviewDomainError):
    pass


class ResumeNotUsable(InterviewDomainError):
    pass


class ReportNotEligible(InterviewDomainError):
    pass
