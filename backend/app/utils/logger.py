"""Structured logging configuration using structlog."""

import logging
import sys

import structlog

from ..config import settings


def setup_logging() -> None:
    """Configure structlog with JSON output and stdlib integration."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(settings.log_level.upper())

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(settings.log_level.upper())
        root_logger.addHandler(handler)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound with the given name."""
    return structlog.get_logger(name)
