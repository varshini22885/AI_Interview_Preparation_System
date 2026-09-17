# Backend Architecture

FastAPI owns REST and WebSocket transport. SQLAlchemy and PostgreSQL own all durable business state. Celery tasks consume primitive IDs from Redis and open fresh database sessions. The interview state machine and interview service are the only state-transition owners.

Answer evaluation persists one `AnswerEvaluation` per answer, uses deterministic application scoring, persists an evidence-based follow-up when required, and advances the interview. Completed interviews enqueue report generation. Reports persist deterministic scores plus validated provider narrative and feedback.

Realtime sessions are ownership records for reconnectable WebSocket transport only. They do not replace interview state. Final transcripts use the existing answer/idempotency service. Partial transcript, raw audio, and face frames are not persisted.

PostgreSQL and Redis are external runtime dependencies in production. The included Compose file provides an optional local Postgres/Redis stack for development; replace the database URL with Supabase PostgreSQL and configure S3-compatible Supabase Storage for hosted use.
