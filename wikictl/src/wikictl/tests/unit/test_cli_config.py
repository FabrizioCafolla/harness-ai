"""Tests that guard the CLI default port against drifting from the harness-ai
config template that wires it into .mcp.json — the two are hand-maintained
in separate files and nothing else catches a desync between them."""

from __future__ import annotations

import json
import re
from pathlib import Path

from wikictl.cli import serve

_REPO_ROOT = Path(__file__).resolve().parents[5]
_MCP_TEMPLATE = _REPO_ROOT / "config" / "mcp.wikictl.json"


def _serve_port_default() -> int:
    for param in serve.params:
        if param.name == "port":
            return param.default
    raise AssertionError("serve command has no --port option")


def test_serve_port_default_matches_mcp_wikictl_template():
    default_port = _serve_port_default()

    mcp_config = json.loads(_MCP_TEMPLATE.read_text())
    url = mcp_config["mcpServers"]["wikictl"]["url"]
    match = re.search(r":(\d+)/", url)
    assert match, f"could not find a port in {url!r}"
    template_port = int(match.group(1))

    assert default_port == template_port, (
        f"serve --port default ({default_port}) != "
        f"config/mcp.wikictl.json port ({template_port})"
    )
