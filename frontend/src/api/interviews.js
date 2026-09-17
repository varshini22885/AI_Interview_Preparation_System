import { api } from "./client";

/** POST /interviews -> InterviewSummary (status PREPARING) */
export function createInterview(payload) {
  return api.post("/interviews", payload);
}

/** GET /interviews?page&page_size -> page of InterviewSummary */
export function listInterviews(page = 1, pageSize = 20) {
  return api.get(`/interviews?page=${page}&page_size=${pageSize}`);
}

/** GET /interviews/{id} -> InterviewDetail (incl. started_at, report_available) */
export function getInterview(id) {
  return api.get(`/interviews/${id}`);
}

/** GET /interviews/{id}/current -> server-authoritative current question */
export function getCurrentQuestion(id) {
  return api.get(`/interviews/${id}/current`);
}

/** POST /interviews/{id}/start -> InterviewSummary */
export function startInterview(id) {
  return api.post(`/interviews/${id}/start`);
}

/**
 * POST /interviews/{id}/answers (202).
 * The Idempotency-Key header makes retries of the SAME logical
 * submission return the original result instead of a new Answer.
 */
export function submitAnswer(id, { questionId, answerText, idempotencyKey }) {
  return api.post(
    `/interviews/${id}/answers`,
    { question_id: questionId, answer_text: answerText },
    { headers: { "Idempotency-Key": idempotencyKey } },
  );
}

/** POST /interviews/{id}/pause -> 409 (unsupported by design). */
export function pauseInterview(id) {
  return api.post(`/interviews/${id}/pause`);
}

/** POST /interviews/{id}/resume */
export function resumeInterview(id) {
  return api.post(`/interviews/${id}/resume`);
}

/** POST /interviews/{id}/finish -> InterviewSummary (COMPLETED) */
export function finishInterview(id) {
  return api.post(`/interviews/${id}/finish`);
}

/** GET /interviews/{id}/evaluations -> persisted per-answer evaluations */
export function getEvaluations(id) {
  return api.get(`/interviews/${id}/evaluations`);
}

/** GET /interviews/{id}/transcript -> ordered questions/answers/follow-ups */
export function getTranscript(id) {
  return api.get(`/interviews/${id}/transcript`);
}
