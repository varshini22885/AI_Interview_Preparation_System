# AI Architecture

Provider-independent. Business code depends on `AIProvider` protocol,
never on `openai`/`anthropic` SDKs. SDK imports are lazy inside
`app/ai/providers/vendor.py`; missing SDK raises `AIConfigurationError`.

## Layout

- `app/ai/provider.py`: `AIProvider` protocol (generate_question,
  evaluate_answer, generate_follow_up, generate_interview_feedback,
  generate_performance_report) + `AIResult(data, meta)` + `get_provider()`.
- `app/ai/schemas.py`: strict Pydantic outputs for every op.
- `app/ai/prompts.py`: versioned builders with SYSTEM/ROLE/TASK/CONTEXT/
  CONSTRAINTS/OUTPUT SCHEMA + `GUARDRAILS` injection defense.
- `app/ai/providers/vendor.py`: OpenAI (`response_format json_object`) /
  Anthropic (JSON instruction) with structured metadata, no secret logging.
- `app/ai/providers/test_provider.py`: deterministic test double only.
- `app/ai/question_service.py`, `evaluation_service.py`,
  `followup_service.py`: validation + retry + fallback orchestration.
- `app/ai/question_bank.py`: curated fallback, constraint-respecting.
- `app/ai/retry.py`: bounded retries, `AIRetryExhausted`.
- `app/ai/tasks.py`: Celery task boundaries (seams only, no fake success).
- `app/evaluations/scoring.py`: deterministic formulas (single source).

## Configuration

`AI_PROVIDER` in {openai, anthropic, test}; `AI_MODEL` override;
per-vendor keys/models; `AI_TEMPERATURE` (0.2); `AI_TIMEOUT_SECONDS`;
`AI_MAX_RETRIES`; `AI_MAX_RESUME_CHARS` (4000); `AI_MAX_ANSWER_CHARS`
(12000); `AI_MAX_OUTPUT_TOKENS` (1500). Missing key -> operation raises
`AIConfigurationError`; startup may report status but never fakes AI.
`test` provider forbidden in production.

## Pipeline

LLM -> JSON parse -> Pydantic -> business rules -> typed result.
Malformed -> bounded retry -> bank fallback (questions) or raise.
Never invent missing scores/concepts; never zero-fill.

## Privacy/logging

Metadata only: provider/model/operation/latency/success/retries/token
counts. Never log keys, full resume/answers, or full prompts.
Resume context truncated; only current question/evaluation sent.
