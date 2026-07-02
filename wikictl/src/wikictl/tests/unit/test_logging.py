"""Tests for wikictl.logging module."""

from __future__ import annotations

import io
import json
import logging

from wikictl.logging import configure_logging, get_logger


class TestConfigureLogging:
    def test_default_level_is_warning(self):
        configure_logging()
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_level_setting(self):
        configure_logging(level="DEBUG")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_output_to_custom_stream(self):
        buf = io.StringIO()
        configure_logging(level="INFO", fmt="console", output=buf)
        logger = get_logger("test")
        logger.info("hello")
        output = buf.getvalue()
        assert "hello" in output

    def test_json_format(self):
        buf = io.StringIO()
        configure_logging(level="INFO", fmt="json", output=buf)
        logger = get_logger("test")
        logger.info("test_event", key="value")
        output = buf.getvalue()
        parsed = json.loads(output.strip())
        assert parsed["event"] == "test_event"
        assert parsed["key"] == "value"
        assert "timestamp" in parsed

    def test_output_goes_to_stderr_by_default(self):
        configure_logging(level="WARNING")
        root = logging.getLogger()
        handler = root.handlers[0]
        import sys

        assert handler.stream is sys.stderr

    def test_filters_below_level(self):
        buf = io.StringIO()
        configure_logging(level="WARNING", fmt="json", output=buf)
        logger = get_logger("test")
        logger.info("should_not_appear")
        assert buf.getvalue() == ""

    def test_wikictl_logger_level_set(self):
        configure_logging(level="DEBUG")
        wikictl_logger = logging.getLogger("wikictl")
        assert wikictl_logger.level == logging.DEBUG


class TestGetLogger:
    def test_returns_bound_logger(self):
        configure_logging()
        logger = get_logger("mymodule")
        assert hasattr(logger, "info")
        assert hasattr(logger, "bind")

    def test_default_name(self):
        configure_logging()
        logger = get_logger()
        # Just ensure it doesn't raise
        assert logger is not None
