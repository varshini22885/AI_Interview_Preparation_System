"""Server-authoritative interview state machine: pure transition rules."""

from app.models.interview import InterviewStatus

C = InterviewStatus.CREATED
P = InterviewStatus.PREPARING
R = InterviewStatus.READY
IP = InterviewStatus.IN_PROGRESS
W = InterviewStatus.WAITING_FOR_ANSWER
E = InterviewStatus.EVALUATING
F = InterviewStatus.FOLLOW_UP_REQUIRED
N = InterviewStatus.NEXT_QUESTION
DONE = InterviewStatus.COMPLETED
RG = InterviewStatus.REPORT_GENERATING
RR = InterviewStatus.REPORT_READY
FAIL = InterviewStatus.FAILED

ALLOWED_TRANSITIONS: dict[InterviewStatus, frozenset[InterviewStatus]] = {
    C: frozenset({P, FAIL}),
    P: frozenset({R, FAIL}),
    R: frozenset({IP, FAIL}),
    IP: frozenset({W, DONE, FAIL}),
    # WAITING_FOR_ANSWER -> COMPLETED: explicit manual finish by the
    # owner (finish_interview(manual=True)); the server remains the
    # only component allowed to complete an interview.
    W: frozenset({E, DONE, FAIL}),
    E: frozenset({F, N, DONE, FAIL}),
    # Active interview states below may also be manually completed
    # (owner explicitly ends the interview). Abandoning mid-follow-up
    # or mid-evaluation is a deliberate, owner-authorized completion,
    # not an arbitrary jump: it is only reachable via the service.
    F: frozenset({W, DONE, FAIL}),
    N: frozenset({W, DONE, FAIL}),
    DONE: frozenset({RG, FAIL}),
    RG: frozenset({RR, FAIL}),
    RR: frozenset(),
    FAIL: frozenset(),
}


def _coerce(status: InterviewStatus | str) -> InterviewStatus:
    if isinstance(status, InterviewStatus):
        return status
    return InterviewStatus(str(status))


def is_transition_allowed(current: InterviewStatus | str, target: InterviewStatus | str) -> bool:
    return _coerce(target) in ALLOWED_TRANSITIONS[_coerce(current)]


def validate_transition(current: InterviewStatus | str, target: InterviewStatus | str) -> None:
    from app.interviews.exceptions import InvalidInterviewTransition

    cur, tgt = _coerce(current), _coerce(target)
    if tgt not in ALLOWED_TRANSITIONS[cur]:
        raise InvalidInterviewTransition(cur.value, tgt.value)
