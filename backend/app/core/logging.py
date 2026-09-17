"""Structured logging: stdlib fallback when structlog is unavailable."""

import logging
import sys

try:
    import structlog

    _HAS_STRUCTLOG = True
except Exception:  # pragma: no cover - optional dependency
    _HAS_STRUCTLOG = False


if _HAS_STRUCTLOG:

    def setup_logging(debug: bool = False) -> None:
        level = logging.DEBUG if debug else logging.INFO
        logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level)
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.add_log_level,
                structlog.processors.StackInfoRenderer(),
                structlog.dev.set_exc_info,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.make_filtering_bound_logger(level),
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
            cache_logger_on_first_use=True,
        )
        for noisy in ("uvicorn.access", "httpx", "httpcore", "botocore"):
            logging.getLogger(noisy).setLevel(logging.WARNING)


    def get_logger(name: str = "app"):
        return structlog.get_logger(name)

else:

    def setup_logging(debug: bool = False) -> None:
        logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, level=logging.DEBUG if debug else logging.INFO)


    def get_logger(name: str = "app"):
        return logging.getLogger(name)