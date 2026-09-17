# API

Base URL: `/api/v1` (config `API_V1_PREFIX`). All mutating/auth endpoints
require `Authorization: Bearer <access_token>` except auth register/login/refresh.

## Authentication

`POST /auth/register` (201) `{email, full_name, password}` -> user (no secrets).
`POST /auth/login` (200) -> `{access_token, refresh_token, token_type, expires_in}`.
`POST /auth/refresh` (200) rotates + revokes the old refresh token (`refresh_token` in body).
`POST /auth/logout` (204) revokes the refresh token.
`GET /auth/me` (200) current user.
Password hashing: PBKDF2-SHA256 (hashlib, stdlib-first; passlib/bcrypt optional).
Access tokens: HS256 JWT, 15 min (`ACCESS_TOKEN_EXPIRE_MINUTES`).
Refresh: opaque 48-char URL-safe token, hashed (sha256) in `refresh_tokens`, 7 days.

## Error contract

```json
{"error": {"code": "INTERVIEW_NOT_FOUND", "message": "Interview was not found.", "request_id": "ae4d..."}}
```
Codes/status: 401 UNAUTHENTICATED/INVALID_CREDENTIALS, 403 USER_INACTIVE,
404 INTERVIEW_NOT_FOUND/RESUME_NOT_FOUND/REPORT_NOT_FOUND, 409 INVALID_TRANSITION
/INTERVIEW_NOT_READY/ALREADY_COMPLETED/INTERVIEW_NOT_ACTIVE/ANSWER_REJECTED
/DUPLICATE_SUBMISSION/REPORT_NOT_READY, 422 VALIDATION_ERROR/INVALID_ANSWER,
502 AI_PROVIDER_ERROR, 503 AI_NOT_CONFIGURED. Every response carries
`X-Request-ID` (validated or server-generated).

## Interviews

- `POST /interviews` (201) create; body `{resume_id?, target_role, programming_language?, interview_type, difficulty, interviewer_persona, question_count}`. Returns summary; status is `PREPARING` (created then preparation seam), never falsely READY.
- `GET /interviews?page=&page_size=` paginated summary list (user-scoped).
- `GET /interviews/{id}` detail (status/config/started/completed/report_available).
- `POST /interviews/{id}/start` (200) `READY->IN_PROGRESS->WAITING_FOR_ANSWER`, sets started_at + current question. 409 if not READY.
- `GET /interviews/{id}/current` returns `{interview_id, status, order_index, total_questions, question_id, question_type, question_text, answer_allowed}`. Rubric/metadata NOT exposed to keep criteria hidden.
- `POST /interviews/{id}/answers` (202) body `{question_id, answer_text, idempotency_key?}`; requires `Idempotency-Key` header (preferred) or body key. Service determines current question, attempt number, duplicates; transitions WAITING_FOR_ANSWER -> EVALUATING. 202 returns accepted state; retry with same key+payload returns the same `answer_id` with `is_duplicate: true`. 409 + `DUPLICATE_SUBMISSION` for same key + different payload.
- `POST /interviews/{id}/pause` (409 INTERVIEW_NOT_ACTIVE) -> pause is intentionally unsupported (no PAUSED state in the state machine).
- `POST /interviews/{id}/resume` returns current position/question from authoritative DB state.
- `POST /interviews/{id}/finish` (200) transitions active interview to COMPLETED server-side (manual=True records operator-initiated finish).

## Async evaluation flow (documented boundary)

POST answer -> persist Answer -> EVALUATING -> queue `ai.evaluate_answer` Celery task
-> worker runs AnswerEvaluationService (AIProvider -> validate -> scoring) ->
persists AnswerEvaluation -> FollowUpService -> `advance_after_evaluation`.
The API returns 202 immediately; the worker is NOT faked. Celery broker/result
backend come from `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` (Redis). In
environments without the worker, the interview remains in EVALUATING until a
worker (or an explicit future re-drive) advances it.

## Reports / History

- `GET /reports/{interview_id}`: only returns a persisted report when status is REPORT_READY; otherwise 409 (COMPLETED/REPORT_GENERATING) or 404. Never generates a report on GET.
- `GET /history?page=&page_size=&role=&interview_type=&difficulty=` paginated user history with `overall_score` when report exists. No N+1: one report lookup per row of the page.

## Resumes / Roles

- `POST /resumes` multipart upload. Extensions `.pdf,.doc,.docx`, max `MAX_UPLOAD_SIZE_MB` (422 on violation). Stored via storage interface (local `.uploads` dev backend; S3 when `S3_*` configured). File data never in PostgreSQL.
- `GET /resumes?page=&page_size=`; `GET /resumes/{id}`; `DELETE /resumes/{id}` (204).
- `GET /roles` returns supported roles + type/difficulty/language capability aligned with question-generation/bank support.

## Ownership / pagination / rate limiting

- Server derives owner from token; client-sent user_id is ignored. Foreign or missing resources return the same 404 to prevent existence oracle.
- Pagination is `{items, page, page_size, total}` with `page_size` max 100.
- Rate limiting: `RATE_LIMIT_*` env config; route seam `rate_limit_guard` documented here. Production should attach Redis-backed slowapi limiter per config; no unreliable in-memory limiter for multi-instance deployments is used.