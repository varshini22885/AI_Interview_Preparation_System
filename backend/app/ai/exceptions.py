"""AI domain exceptions (framework-independent, no SDK imports)."""


class AIError(Exception):
    pass


class AIConfigurationError(AIError):
    pass


class AIProviderError(AIError):
    pass


class AIValidationError(AIError):
    pass


class AIRetryExhausted(AIError):
    def __init__(self, operation: str, attempts: int) -> None:
        super().__init__(f"{operation} failed after {attempts} attempts")
        self.operation = operation
        self.attempts = attempts


class AIQuestionRejected(AIError):
    pass


class AIFallbackExhausted(AIError):
    pass
