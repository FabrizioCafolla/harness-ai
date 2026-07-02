"""Centralized logging configuration for wikictl."""

from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(
    level: str = "WARNING",
    fmt: str = "console",
    output: object | None = None,
) -> None:
    """Configure structlog for the application.

    Args:
        level: Log level name (DEBUG, INFO, WARNING, ERROR).
        fmt: Output format - "json" for JSON lines, "console" for human-readable.
        output: Stream to write logs to. Defaults to stderr.
    """
    output = output or sys.stderr
    level_num = getattr(logging, level.upper(), logging.WARNING)

    if fmt == "json":
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )

    handler = logging.StreamHandler(output)
    # Use a simple formatter since structlog handles rendering
    handler.setFormatter(logging.Formatter("%(message)s"))

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(level_num)

    # Also set wikictl logger explicitly
    wikictl_logger = logging.getLogger("wikictl")
    wikictl_logger.setLevel(level_num)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog bound logger.

    Args:
        name: Logger name, typically module name. Defaults to "wikictl".
    """
    return structlog.get_logger(name or "wikictl")
