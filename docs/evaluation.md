# Evaluation

## Methodology

Input: role, question, rubric, expected concepts, answer (truncated to
`AI_MAX_ANSWER_CHARS`), persona (wording only). Output: validated
`EvaluationOutput` (4 tech dims + 3 comm dims 0-10, strengths,
improvements, factual/communication feedback, missing/incorrect
concepts, confidence). AI MUST NOT emit overall scores; application
computes `technical_overall=round(mean(4 tech))`,
`communication_overall=round(mean(3 comm))` (half-up) in
`app/evaluations/scoring.py`. Reports: dim*10 averages, overall =
round((tech+comm)/2). Single source; no duplicated formulas.

## Separation

Tech (correctness/relevance/completeness/depth) vs comm
(clarity/structure/conciseness) stored separately: correct-but-unclear
differs from incorrect-but-clear (tested). Equivalent wording gets
credit; harmless phrasing not penalized. No personality/accent/gender
judgments; style disagreement != factual error.

## Follow-ups

Evidence-justified only (missing/incorrect/ambiguous/shallow).
Filler reasons rejected; duplicates rejected; budget
`max_follow_ups` enforced (exhausted -> required=false).
Persona wording may differ; factual rubric identical across personas
(tested FRIENDLY vs STRICT equality).

## Injection/security

Resume/answer = UNTRUSTED DATA in prompts; guardrails forbid following
embedded instructions, revealing prompts/keys, inventing facts.
Tests cover injection strings in answer context.
