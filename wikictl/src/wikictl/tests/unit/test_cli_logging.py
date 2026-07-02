"""Tests for CLI logging integration."""

from __future__ import annotations

import logging

from click.testing import CliRunner

from wikictl.cli import cli


class TestCliVerbosity:
    def test_default_level_is_warning(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "list"])
        # Just check it runs without error
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_verbose_sets_info(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--wiki-dir", str(tmp_path), "list"])
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.INFO

    def test_double_verbose_sets_debug(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["-vv", "--wiki-dir", str(tmp_path), "list"])
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_quiet_sets_error(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--quiet", "--wiki-dir", str(tmp_path), "list"])
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.ERROR

    def test_env_var_override(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WIKICTL_LOG_LEVEL", "DEBUG")
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "list"])
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_cli_flag_overrides_env_var(self, tmp_path, monkeypatch):
        monkeypatch.setenv("WIKICTL_LOG_LEVEL", "ERROR")
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--wiki-dir", str(tmp_path), "list"])
        assert result.exit_code == 0
        root = logging.getLogger()
        assert root.level == logging.INFO
