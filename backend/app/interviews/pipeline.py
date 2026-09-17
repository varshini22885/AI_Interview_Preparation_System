"""Task dispatch: Celery in production, documented inline fallback in dev/test.

Production deployments MUST run Celery workers against
CELERY_BROKER_URL. When no broker/celery is available the tasks run
inline (local development and automated tests only); this is documented
and never silent in production (production raises instead of inlining).
"""

import uuid as _uuid


def run_task(task_name: str, **kwargs) -> None:
    """Dispatch a background work item.

    PostgreSQL deployments queue through Celery. SQLite is reserved for the
    isolated test suite and uses the existing deterministic inline path.
    """
    from app.core.config import get_settings

    settings = get_settings()
    if settings.APP_ENV == "production" or not settings.DATABASE_URL.startswith("sqlite"):
        from app.ai import tasks as ai_tasks

        if ai_tasks._celery is None:
            raise RuntimeError(f"Celery not configured; cannot dispatch {task_name}")
        try:
            ai_tasks._celery.send_task(task_name, kwargs=kwargs)
        except Exception as exc:
            raise RuntimeError(f"Failed to dispatch {task_name}") from exc
        return
    worker = _WORKERS.get(task_name)
    if worker is None:
        raise ValueError(f"Unknown task {task_name}")
    worker(**kwargs)


from app.workers import evaluate_answer_work, generate_questions_work, generate_report_work  # noqa: E402
from app.workers import process_resume_work  # noqa: E402

_WORKERS = {
    "ai.generate_questions": generate_questions_work,
    "ai.evaluate_answer": evaluate_answer_work,
    "ai.generate_report": generate_report_work,
    "resume.process_resume": process_resume_work,
}


def enqueue_question_generation(*, interview_id) -> None:
    run_task("ai.generate_questions", interview_id=str(interview_id))


def enqueue_answer_evaluation(*, answer_id) -> None:
    from app.db.base import SessionLocal
    from app.models.interview import Answer

    db = SessionLocal()
    try:
        answer = db.get(Answer, answer_id)
        if answer is None:
            raise ValueError("Answer not found")
        run_task(
            "ai.evaluate_answer",
            interview_id=str(answer.question.interview_id),
            question_id=str(answer.question_id),
            answer_id=str(answer.id),
        )
    finally:
        db.close()


def enqueue_report_generation(*, interview_id) -> None:
    run_task("ai.generate_report", interview_id=str(interview_id))


def enqueue_resume_processing(*, resume_id) -> None:
    run_task("resume.process_resume", resume_id=str(resume_id))