# Question Generation

Input: role, language, type, difficulty, persona, resume summary
(truncated to `AI_MAX_RESUME_CHARS`), asked list, count 1-5.

## Enforcement (deterministic, not LLM-trusted)

Role/type/difficulty match; language relevance for TECHNICAL
(language token must appear in skill/category/text); non-duplication
(normalized exact/substring); skill coverage via distinct bank/AI skills;
resume grounding without inventing facts; no prohibited content
(`ignore previous instructions`, `system prompt`, `api key`);
no embedded answers; concepts + rubric required.

## Flow

build prompt -> provider.generate_question -> validate ->
retry (bounded) -> on exhaustion use `QuestionBank.find_one`
respecting role/language/type/difficulty/exclusions.
No valid fallback -> `AIFallbackExhausted` (never filler like
"What is your favorite programming language?").

## Difficulty/persona

EASY: fundamentals/definitions; MEDIUM: application/trade-offs;
HARD: system reasoning/edge cases/optimization/architecture;
EXPERT: novel constrained design. Persona changes wording only
(Friendly encouraging; Professional neutral; Strict probing, never abusive).

## DB boundary

Future persistence uses `InterviewQuestion(question_metadata={
expected_concepts, rubric, source, attempts})` via interview service
`mark_ready` seam. AI layer never transitions interview state.
Celery `ai.generate_questions` is the async seam (no fake success).
