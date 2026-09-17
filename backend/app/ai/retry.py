"""Retry helper: bounded attempts, no unbounded AI calls."""

import time

from app.ai.exceptions import AIRetryExhausted, AIValidationError


def run_with_retries(operation: str, fn, *, max_attempts: int):
    last: Exception | None = None
    attempts = max(1, int(max_attempts))
    for attempt in range(1, attempts + 1):
        try:
            result = fn()
            return result, attempt
        except AIValidationError as exc:
            last = exc
            if attempt >= attempts:
                break
            time.sleep(0)
    raise AIRetryExhausted(operation, attempts) from last
