# Interview State Machine

Server-authoritative lifecycle. Frontend state is never trusted.
All transitions go through `transition_interview()` which checks
actor, ownership, current state, and the legal map below.

## States

CREATED: interview row exists, config immutable, no questions assumed.
PREPARING: question generation may run (future phase). No AI yet.
READY: persisted questions exist; can start.
IN_PROGRESS: transient; immediately moves to WAITING_FOR_ANSWER on start.
WAITING_FOR_ANSWER: current question determined by `current_question_index`.
EVALUATING: answer saved; evaluation worker runs (future phase).
FOLLOW_UP_REQUIRED: evaluation decided a follow-up is needed.
NEXT_QUESTION: ready to advance `current_question_index`.
COMPLETED: `completed_at` set server-side.
REPORT_GENERATING / REPORT_READY: report lifecycle hooks only.
FAILED: terminal failure; no automatic retry.

## Legal transitions

- CREATED -> PREPARING, FAILED
- PREPARING -> READY, FAILED
- READY -> IN_PROGRESS, FAILED
- IN_PROGRESS -> WAITING_FOR_ANSWER, COMPLETED, FAILED
- WAITING_FOR_ANSWER -> EVALUATING, FAILED
- EVALUATING -> FOLLOW_UP_REQUIRED, NEXT_QUESTION, COMPLETED, FAILED
- FOLLOW_UP_REQUIRED -> WAITING_FOR_ANSWER, FAILED
- NEXT_QUESTION -> WAITING_FOR_ANSWER, COMPLETED, FAILED
- COMPLETED -> REPORT_GENERATING, FAILED
- REPORT_GENERATING -> REPORT_READY, FAILED
- REPORT_READY -> (none)
- FAILED -> (none; retry requires explicit new design)

Illegal examples (tested): READY->REPORT_READY, COMPLETED->IN_PROGRESS,
REPORT_READY->IN_PROGRESS, CREATED->IN_PROGRESS.

## Ownership

`get_user_interview` / `get_locked_interview` raise `InterviewNotFound`
for missing OR foreign resources (no existence oracle).
`transition_interview` re-checks `interview.user_id == actor_user_id`.

## Answer lifecycle

WAITING_FOR_ANSWER --submit_answer--> EVALUATING --advance--> FOLLOW_UP/NEXT
--move_to_next--> WAITING (or COMPLETED if no more questions).
Attempt numbers are server-computed `max+1`; client values ignored.
`current_answer_id` has no FK (circular); service validates
answer.question_id == question.id on every update.

## Idempotency

Table `answer_idempotency_keys` unique (user_id, interview_id, key).
Stores request_hash = sha256(question_id|text|time_taken).
Same key + same hash -> return original answer, no new row.
Same key + different hash -> DuplicateSubmission.
Race: IntegrityError -> rollback -> re-read winner row.

## Concurrency

Critical ops lock the interview row (`SELECT ... FOR UPDATE` on PG;
SQLite serializes in tests). State is re-read inside the transaction.
No distributed locks.

## Pause / resume

No PAUSED state exists. `pause_interview()` raises and documents:
client should stop timers locally; resume = `get_current_question`.
Adding a pause state would require migration + transition design.

## Transactions

create/begin/ready/start/submit/advance/move/finish/report ops each
commit atomically; failures rollback. State + timestamps + current
pointer update in the same transaction.
