# Database

PostgreSQL is the source of truth. SQLite is used only for local test/migration verification.

## Existing models (preserved)

### users
- PK `id` UUID (SQLAlchemy generic `Uuid`, native UUID on Postgres).
- `email` unique indexed, `full_name`, `hashed_password`.
- `is_active`, `is_superuser`, `created_at`, `updated_at`.
- Relationships: `refresh_tokens` (cascade delete-orphan), `resumes`, `interviews`.

### refresh_tokens
- PK `id` UUID; `user_id` FK `users.id` CASCADE indexed.
- `token_hash` unique indexed, `jti` unique indexed, `expires_at`, `revoked_at`, `replaced_by_jti`, `user_agent`, `ip_address`, `created_at`.

### resumes
- PK `id` UUID; `user_id` FK `users.id` CASCADE indexed.
- `filename`, `content_type`, `size_bytes`, `storage_key` unique, `extracted_text`, `parsed_at`, `created_at`.
- Relationships: `analyses` (cascade delete-orphan), `interviews` (added; SET NULL from interview side).

### resume_analyses
- PK `id` UUID; `resume_id` FK `resumes.id` CASCADE indexed.
- Preserved as-is (Text JSON-string columns): `role`, `target_role`, `summary`, `skills`, `years_experience`, `education`, `gaps`, `strengths`, `suggested_focus_areas`, `created_at`.

## New interview domain

### interviews
- PK `id` UUID; `user_id` FK `users.id` CASCADE; `resume_id` FK `resumes.id` SET NULL nullable.
- Config: `target_role`, `programming_language` nullable, `interview_type` (TECHNICAL/BEHAVIORAL/MIXED), `difficulty` (EASY/MEDIUM/HARD/EXPERT), `interviewer_persona` (FRIENDLY/PROFESSIONAL/STRICT), `total_questions` 1-50.
- State machine column `status` default CREATED. Allowed values: CREATED, PREPARING, READY, IN_PROGRESS, WAITING_FOR_ANSWER, EVALUATING, FOLLOW_UP_REQUIRED, NEXT_QUESTION, COMPLETED, REPORT_GENERATING, REPORT_READY, FAILED. Transitions enforced in service layer (future phase).
- Progress: `current_question_index >= 0`, `started_at`, `completed_at`, `created_at`, `updated_at`.
- Indexes: `(user_id, status)`, `(user_id, created_at)`, single on `status`, `user_id`, `resume_id`.
- Relationships: `questions` (ordered, cascade delete-orphan), `feedback` (one-to-one, cascade), `performance_report` (one-to-one, cascade).

### interview_questions
- PK `id` UUID; `interview_id` FK CASCADE; `order_index >= 0`; unique `(interview_id, order_index)`; index `(interview_id, order_index)`.
- `question_type` (TECHNICAL/BEHAVIORAL/FOLLOW_UP), `question_text`, `question_metadata` JSON (expected concepts, rubric, AI trace), `current_answer_id` UUID nullable (app-level pointer to latest `answers.id`, no circular FK), `created_at`.
- Relationships: `answers` (ordered by attempt, cascade), `follow_ups` (cascade).

### answers
- PK `id` UUID; `question_id` FK CASCADE; `attempt_number >= 1`; unique `(question_id, attempt_number)`; index `(question_id, attempt_number)`.
- `answer_text`, `time_taken_seconds` nullable, `created_at`.
- Relationship: `evaluation` one-to-one cascade.

### answer_evaluations
- PK `id` UUID; `answer_id` FK CASCADE unique (one evaluation per answer).
- Technical 0-10 with DB CHECKs: `correctness_score`, `relevance_score`, `completeness_score`, `technical_depth_score`, `technical_overall`.
- Communication 0-10 with DB CHECKs: `clarity_score`, `structure_score`, `conciseness_score`, `communication_overall`.
- Technical and communication kept separate to represent correct-but-unclear vs incorrect-but-clear.
- `evaluation_detail` JSON (missing concepts, breakdowns, AI metadata), `evaluated_by`, `created_at`.

### interview_follow_ups
- PK `id` UUID; `parent_question_id` FK CASCADE; `triggering_answer_id` FK `answers.id` SET NULL nullable.
- `follow_up_text`, `reason` nullable, `follow_up_metadata` JSON, `created_at`.

### interview_feedback
- PK `id` UUID; `interview_id` FK CASCADE unique (one per interview).
- `strengths`, `areas_for_improvement`, `detailed_feedback`, `feedback_detail` JSON, `created_at`.

### performance_reports
- PK `id` UUID; `interview_id` FK CASCADE unique (one per interview).
- `technical_score`, `communication_score`, `overall_score` 0-100 with CHECKs; `total_questions_answered >= 0`; `report_detail` JSON; `generated_at`; `created_at`.

## Migrations

- `241f969e16cb_initial_schema_with_interview_domain.py`: initial schema covering all existing + interview tables. Verified with `alembic upgrade head` on SQLite and `alembic check` semantics (SQLite file DB shows expected single-head behavior; Postgres verification pending real DATABASE_URL).
- Note: first autogenerate attempt produced `cfc12a11a371` with mixed `Uuid(native_uuid=False)` types causing FK mismatch with existing generic `Uuid`; normalized interview models to generic `Uuid` inference and regenerated as `241f969e16cb`.
- `ed695e15ff26_answer_idempotency_keys.py`: adds `answer_idempotency_keys` (user/interview/question FKs CASCADE, `idempotency_key` 128, `answer_id` FK CASCADE, `request_hash` sha256 hex, unique `(user_id, interview_id, idempotency_key)`). Verified `upgrade head` applies both revisions cleanly on fresh SQLite.

## Compatibility notes

- `User.interviews` forward ref to `Interview` resolved once `app.models.interview` imported (via `app.models` package import).
- `Resume.interviews` added with `back_populates="resume"`; delete of Resume SETs NULL on `interviews.resume_id` (verified by test).
- No User/Resume tables recreated or dropped; migration is additive initial schema (no prior migrations existed).
