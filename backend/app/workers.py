"""Background work functions: question generation, evaluation, report.

Each function opens its own DB session, is broker-independent, and is
invoked by Celery tasks (production) or inline by the pipeline (local
dev/test fallback). Deterministic app logic; state transitions only via
the interview service/state machine.
"""

import uuid
import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.ai.evaluation_service import AnswerEvaluationService, EvaluationRequest
from app.ai.followup_service import FollowUpRequest, FollowUpService
from app.ai.question_service import QuestionGenerationService, QuestionRequest
from app.db.base import SessionLocal
from app.evaluations.scoring import report_scores
from app.interviews import service as svc
from app.models.interview import Answer, AnswerEvaluation, Interview, InterviewFollowUp, InterviewQuestion, InterviewStatus, PerformanceReport
from app.models.resume import Resume, ResumeAnalysis
from app.storage import get_storage


def _latest_resume_summary(db, interview: Interview) -> str:
    if interview.resume_id is None:
        return ""
    analysis = db.query(ResumeAnalysis).filter_by(resume_id=interview.resume_id).order_by(ResumeAnalysis.created_at.desc()).first()
    if analysis is None:
        return ""
    return (analysis.summary or "")[:4000]


def _extract_resume_text(data: bytes, filename: str) -> str:
    from io import BytesIO

    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if suffix == "pdf":
        from PyPDF2 import PdfReader

        return "\n".join(page.extract_text() or "" for page in PdfReader(BytesIO(data)).pages).strip()
    if suffix == "docx":
        from docx import Document

        return "\n".join(paragraph.text for paragraph in Document(BytesIO(data)).paragraphs).strip()
    raise ValueError("Unsupported resume format")


def process_resume_work(*, resume_id) -> None:
    db = SessionLocal()
    try:
        resume = db.get(Resume, _as_uuid(resume_id))
        if resume is None:
            raise ValueError("Resume not found")
        if resume.status == "READY":
            return
        resume.status = "PROCESSING"
        db.commit()
        text = _extract_resume_text(get_storage().read(key=resume.storage_key), resume.filename)
        if not text:
            raise ValueError("Resume contains no extractable text")
        settings = __import__("app.core.config", fromlist=["get_settings"]).get_settings()
        resume.extracted_text = text[: settings.AI_MAX_RESUME_CHARS]
        resume.parsed_at = datetime.now(timezone.utc)
        db.add(ResumeAnalysis(resume_id=resume.id, role="General", summary=resume.extracted_text, skills=json.dumps([])))
        resume.status = "READY"
        db.commit()
    except Exception:
        db.rollback()
        resume = db.get(Resume, _as_uuid(resume_id))
        if resume is not None:
            resume.status = "FAILED"
            db.commit()
        raise
    finally:
        db.close()


def _as_uuid(value):
    """Celery serializes kwargs to JSON: IDs arrive as strings."""
    if isinstance(value, uuid.UUID):
        return value
    return uuid.UUID(str(value))


def generate_questions_work(*, interview_id) -> None:
    from app.ai.provider import get_provider

    db = SessionLocal()
    try:
        interview = db.execute(select(Interview).where(Interview.id == _as_uuid(interview_id)).with_for_update()).scalar_one_or_none()
        if interview is None:
            return
        user_id = interview.user_id
        asked: list[str] = []
        gen = QuestionGenerationService(provider=get_provider())
        resume_summary = _latest_resume_summary(db, interview)
        count = int(interview.total_questions)
        for i in range(count):
            req = QuestionRequest(
                role=interview.target_role,
                language=interview.programming_language,
                interview_type=str(interview.interview_type),
                difficulty=str(interview.difficulty),
                persona=str(interview.interviewer_persona),
                resume_summary=resume_summary,
                asked_questions=asked,
                count=1,
            )
            gen_q = gen.generate(req)
            db.add(
                InterviewQuestion(
                    interview_id=interview.id,
                    order_index=i,
                    question_type=gen_q.output.question_type,
                    question_text=gen_q.output.question_text,
                    question_metadata={
                        "category": gen_q.output.category,
                        "skill": gen_q.output.skill,
                        "difficulty": gen_q.output.difficulty,
                        "expected_concepts": gen_q.output.expected_concepts,
                        "evaluation_rubric": gen_q.output.evaluation_rubric,
                        "follow_up_allowed": gen_q.output.follow_up_allowed,
                        "max_follow_ups": gen_q.output.max_follow_ups,
                        "source": gen_q.source,
                        "attempts": gen_q.attempts,
                    },
                )
            )
            asked.append(gen_q.output.question_text)
        db.commit()
        svc.mark_ready(db, user_id=user_id, interview_id=interview.id)
    except Exception:
        db.rollback()
        try:
            interview = db.get(Interview, _as_uuid(interview_id))
            if interview is not None and str(interview.status) != InterviewStatus.FAILED.value:
                svc.fail_interview(db, user_id=interview.user_id, interview_id=interview.id)
        except Exception:
            db.rollback()
        raise
    finally:
        db.close()


def evaluate_answer_work(*, interview_id, question_id, answer_id) -> None:
    from app.ai.provider import get_provider

    db = SessionLocal()
    try:
        interview = db.execute(select(Interview).where(Interview.id == _as_uuid(interview_id)).with_for_update()).scalar_one_or_none()
        question = db.get(InterviewQuestion, _as_uuid(question_id))
        answer = db.get(Answer, _as_uuid(answer_id))
        if interview is None or question is None or answer is None:
            raise ValueError("Evaluation entity is missing")
        if question.interview_id != interview.id or answer.question_id != question.id:
            raise ValueError("Evaluation entity relationship is invalid")
        if interview.status != InterviewStatus.EVALUATING.value or question.current_answer_id != answer.id:
            return
        db.refresh(interview)
        db.refresh(question)
        db.refresh(answer)
        if db.query(AnswerEvaluation).filter_by(answer_id=answer.id).one_or_none() is not None:
            return
        user_id = interview.user_id
        meta = question.question_metadata or {}
        provider = get_provider()

        request = EvaluationRequest(
            role=interview.target_role,
            question_text=question.question_text,
            rubric=str(meta.get("evaluation_rubric", "")),
            expected_concepts=list(meta.get("expected_concepts", []) or []),
            answer_text=answer.answer_text,
            persona=str(interview.interviewer_persona),
        )
        result = AnswerEvaluationService(provider=provider).evaluate(request)
        d = result.output

        evaluation = AnswerEvaluation(
                answer_id=answer.id,
                correctness_score=d.technical.correctness,
                relevance_score=d.technical.relevance,
                completeness_score=d.technical.completeness,
                technical_depth_score=d.technical.technical_depth,
                technical_overall=result.technical_overall,
                clarity_score=d.communication.clarity,
                structure_score=d.communication.structure,
                conciseness_score=d.communication.conciseness,
                communication_overall=result.communication_overall,
                evaluation_detail={
                    "strengths": d.strengths,
                    "improvements": d.improvements,
                    "factual_feedback": d.factual_feedback,
                    "communication_feedback": d.communication_feedback,
                    "missing_concepts": d.missing_concepts,
                    "incorrect_concepts": d.incorrect_concepts,
                    "confidence": d.confidence,
                    "ai": {"provider": result.provider, "model": result.model, "attempts": result.attempts},
                },
                evaluated_by=f"{result.provider}/{result.model}",
            )
        db.add(evaluation)

        can_follow = bool(meta.get("follow_up_allowed", True))
        max_follow_ups = int(meta.get("max_follow_ups", 1) or 1)
        prior = [f.follow_up_text for f in (question.follow_ups or [])]
        decision = FollowUpService(provider=provider).decide(
            FollowUpRequest(
                question_text=question.question_text,
                answer_text=answer.answer_text,
                missing_concepts=list(d.missing_concepts),
                incorrect_concepts=list(d.incorrect_concepts),
                difficulty=str(interview.difficulty),
                persona=str(interview.interviewer_persona),
                prior_follow_ups=prior,
                max_follow_ups=max_follow_ups,
            )
        )
        needs_follow_up = bool(can_follow and decision.output.follow_up_required)
        if needs_follow_up and not db.query(InterviewFollowUp).filter_by(parent_question_id=question.id, triggering_answer_id=answer.id).one_or_none():
            db.add(
                InterviewFollowUp(
                    parent_question_id=question.id,
                    triggering_answer_id=answer.id,
                    follow_up_text=decision.output.question_text,
                    reason=decision.output.reason,
                    follow_up_metadata={"target_concept": decision.output.target_concept, "difficulty": decision.output.difficulty},
                )
            )
        db.flush()
        svc.advance_after_evaluation(db, user_id=user_id, interview_id=interview.id, needs_follow_up=needs_follow_up)
        if not needs_follow_up:
            svc.move_to_next_question(db, user_id=user_id, interview_id=interview.id)
        db.commit()
        final = db.get(Interview, interview.id)
        if final is not None and str(final.status) == InterviewStatus.COMPLETED.value:
            from app.interviews.pipeline import enqueue_report_generation

            enqueue_report_generation(interview_id=interview.id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def generate_report_work(*, interview_id) -> None:
    from app.ai.provider import get_provider

    db = SessionLocal()
    try:
        iv_id = _as_uuid(interview_id)
        interview = db.get(Interview, iv_id)
        if interview is None:
            return
        if interview.performance_report is not None:
            return
        if str(interview.status) != InterviewStatus.COMPLETED.value:
            return
        try:
            svc.begin_report(db, user_id=interview.user_id, interview_id=iv_id)
        except Exception:
            db.rollback()
            if db.get(Interview, iv_id).performance_report is not None:
                return
            raise
        questions = db.query(InterviewQuestion).filter_by(interview_id=interview.id).all()
        qids = [q.id for q in questions]
        rows = (db.query(AnswerEvaluation).join(Answer).filter(Answer.question_id.in_(qids)).all()) if qids else []
        if not rows:
            raise ValueError("No evaluations to build report")
        from app.ai.schemas import CommunicationScores, EvaluationOutput, TechnicalScores

        # Reuse the PERSISTED evaluation detail when rebuilding the scoring
        # inputs; these objects are throwaway (never persisted) and exist
        # only to feed the deterministic report_scores() formula.
        outputs = []
        for r in rows:
            detail = r.evaluation_detail or {}
            outputs.append(
                EvaluationOutput(
                    technical=TechnicalScores(correctness=r.correctness_score, relevance=r.relevance_score, completeness=r.completeness_score, technical_depth=r.technical_depth_score),
                    communication=CommunicationScores(clarity=r.clarity_score, structure=r.structure_score, conciseness=r.conciseness_score),
                    strengths=str(detail.get("strengths") or "(not recorded)"),
                    improvements=str(detail.get("improvements") or "(not recorded)"),
                    factual_feedback=str(detail.get("factual_feedback") or "(not recorded)"),
                    communication_feedback=str(detail.get("communication_feedback") or "(not recorded)"),
                    confidence=float(detail.get("confidence") or 0.0),
                )
            )
        tech, comm, overall = report_scores(outputs)
        from app.ai.prompts import build_feedback_prompt, build_report_prompt
        from app.ai.schemas import FeedbackOutput, ReportOutput

        provider = get_provider()
        strengths = "\n".join(str((r.evaluation_detail or {}).get("strengths") or "") for r in rows)
        weaknesses = "\n".join(str((r.evaluation_detail or {}).get("improvements") or "") for r in rows)
        report_result = provider.generate_performance_report(
            build_report_prompt(role=interview.target_role, tech=tech, comm=comm),
            schema=ReportOutput,
        )
        feedback_result = provider.generate_interview_feedback(
            build_feedback_prompt(role=interview.target_role, strengths_notes=strengths, weakness_notes=weaknesses),
            schema=FeedbackOutput,
        )
        report_output = ReportOutput.model_validate(report_result.data)
        feedback_output = FeedbackOutput.model_validate(feedback_result.data)
        db.add(
            PerformanceReport(
                interview_id=interview.id,
                technical_score=tech,
                communication_score=comm,
                overall_score=overall,
                total_questions_answered=len(rows),
                report_detail={
                    "summary": report_output.summary,
                    "ai": {"provider": report_result.meta.provider, "model": report_result.meta.model},
                },
                generated_at=datetime.now(timezone.utc),
            )
        )
        db.add(
            __import__("app.models.interview", fromlist=["InterviewFeedback"]).InterviewFeedback(
                interview_id=interview.id,
                strengths=feedback_output.strengths,
                areas_for_improvement=feedback_output.areas_for_improvement,
                detailed_feedback=feedback_output.detailed_feedback,
                feedback_detail={"provider": feedback_result.meta.provider, "model": feedback_result.meta.model},
            )
        )
        svc.complete_report(db, user_id=interview.user_id, interview_id=iv_id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()