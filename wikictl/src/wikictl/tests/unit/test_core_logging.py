"""Tests for core module logging."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from wikictl.core import create_entry, delete_entry, edit_entry, read_entry
from wikictl.logging import configure_logging


class TestCoreLogging:
    def _setup_logging(self) -> io.StringIO:
        buf = io.StringIO()
        configure_logging(level="DEBUG", fmt="json", output=buf)
        return buf

    def _events(self, buf: io.StringIO) -> list[dict]:
        return [json.loads(line) for line in buf.getvalue().strip().split("\n") if line.strip()]

    def test_create_entry_logs(self, tmp_path: Path):
        buf = self._setup_logging()
        create_entry(tmp_path, "my-note", "A note", ["test"], "body")
        events = self._events(buf)
        event_names = [e["event"] for e in events]
        assert "entry_created" in event_names
        created = next(e for e in events if e["event"] == "entry_created")
        assert created["entry_name"] == "my-note"

    def test_read_entry_logs(self, tmp_path: Path):
        create_entry(tmp_path, "my-note", "A note")
        buf = self._setup_logging()
        read_entry(tmp_path, "my-note")
        events = self._events(buf)
        event_names = [e["event"] for e in events]
        assert "entry_read" in event_names

    def test_read_entry_not_found_logs_error(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        buf = self._setup_logging()
        with pytest.raises(FileNotFoundError):
            read_entry(tmp_path, "nonexistent")
        events = self._events(buf)
        error_events = [e for e in events if e["event"] == "entry_not_found"]
        assert len(error_events) == 1
        assert error_events[0]["entry_name"] == "nonexistent"

    def test_edit_entry_logs(self, tmp_path: Path):
        create_entry(tmp_path, "my-note", "A note")
        buf = self._setup_logging()
        edit_entry(tmp_path, "my-note", description="Updated")
        events = self._events(buf)
        event_names = [e["event"] for e in events]
        assert "entry_updated" in event_names

    def test_delete_entry_logs(self, tmp_path: Path):
        create_entry(tmp_path, "my-note", "A note")
        buf = self._setup_logging()
        delete_entry(tmp_path, "my-note")
        events = self._events(buf)
        event_names = [e["event"] for e in events]
        assert "entry_deleted" in event_names
