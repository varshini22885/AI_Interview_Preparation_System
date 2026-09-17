# Scoring

## Current schema (unchanged)

AnswerEvaluation: 9 integer dimensions, each 0-10 with DB CHECKs.
- Technical: correctness, relevance, completeness, technical_depth + technical_overall.
- Communication: clarity, structure, conciseness + communication_overall.
PerformanceReport: technical_score, communication_score, overall_score,
each 0-100 with DB CHECKs, plus total_questions_answered.

## Normalization strategy (for future evaluation service)

- Single dimension: normalized = dimension_0_10 * 10 (0-100).
- Technical aggregate per answer: average of the 4 technical dimensions
  * 10, rounded half-up to int. `technical_overall` stored 0-10 SHOULD equal
  round(mean(correctness, relevance, completeness, depth)) — enforce in
  the evaluation service with Pydantic + business-rule validation, never
  trust raw LLM numbers.
- Communication aggregate per answer: average of clarity/structure/
  conciseness * 10. `communication_overall` likewise derived.
- Interview-level report: average of per-answer aggregates across
  answered questions (weight equally unless a future weighted policy is
  documented). overall = round((technical + communication) / 2) unless a
  future policy states otherwise.
- Overall formula is deterministic application logic. The LLM may propose
  dimension scores (validated structured output) but MUST NOT define the
  final formula, weights, or state transitions.

## Separation guarantee

Technical and communication axes are stored separately so
"correct but unclear" (tech 9, comm 3) differs from
"wrong but polished" (tech 3, comm 8). Reports keep both axes plus
the derived overall; never collapse to a single score upstream.
