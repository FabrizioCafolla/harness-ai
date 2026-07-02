"""Tests for MCP tool logging."""

from __future__ import annotations

import asyncio
import io
import json
from pathlib import Path

from wikictl.logging import configure_logging
from wikictl.server.mcp import create_mcp_server


class TestMcpLogging:
    def test_mcp_tools_are_created(self, tmp_path: Path):
        """Verify MCP server creates tools (basic sanity)."""
        mcp = create_mcp_server(tmp_path)
        tools = asyncio.run(mcp.list_tools())
        names = [t.name for t in tools]
        assert "list_entries" in names
        assert "create_entry" in names

    def test_list_entries_logs(self, tmp_path: Path):
        """Verify list_entries tool emits log events."""
        buf = io.StringIO()
        configure_logging(level="INFO", fmt="json", output=buf)
        tmp_path.mkdir(exist_ok=True)

        mcp = create_mcp_server(tmp_path)
        tool = asyncio.run(mcp.get_tool("list_entries"))
        # Call the underlying function directly
        tool.fn()

        output = buf.getvalue()
        lines = [json.loads(line) for line in output.strip().split("\n") if line.strip()]
        events = [line["event"] for line in lines]
        assert "mcp_tool_start" in events
        assert "mcp_tool_complete" in events

    def test_create_entry_logs_with_params(self, tmp_path: Path):
        """Verify create_entry tool logs include params."""
        buf = io.StringIO()
        configure_logging(level="INFO", fmt="json", output=buf)
        tmp_path.mkdir(exist_ok=True)

        mcp = create_mcp_server(tmp_path)
        tool = asyncio.run(mcp.get_tool("create_entry"))
        tool.fn(name="test-entry", description="A test", tags=[], body="hello")

        output = buf.getvalue()
        lines = [json.loads(line) for line in output.strip().split("\n") if line.strip()]
        start_event = next(e for e in lines if e["event"] == "mcp_tool_start")
        assert start_event["tool"] == "create_entry"
        assert start_event["params"] == {"name": "test-entry"}

        complete_event = next(e for e in lines if e["event"] == "mcp_tool_complete")
        assert "duration_ms" in complete_event


class TestMcpSchemaAndProtocol:
    def test_get_schema_tool_registered(self, tmp_path: Path):
        mcp = create_mcp_server(tmp_path)
        names = [t.name for t in asyncio.run(mcp.list_tools())]
        assert "get_schema" in names

    def test_get_schema_on_empty_wiki(self, tmp_path: Path):
        """get_schema returns the full contract without any entries present."""
        tmp_path.mkdir(exist_ok=True)
        mcp = create_mcp_server(tmp_path)
        tool = asyncio.run(mcp.get_tool("get_schema"))
        contract = tool.fn()
        field_names = [f["name"] for f in contract["fields"]]
        assert "name" in field_names
        assert "description" in field_names
        assert "usage" in contract

    def test_instructions_describe_metadata_first(self, tmp_path: Path):
        mcp = create_mcp_server(tmp_path)
        instructions = mcp.instructions.lower()
        assert "list_entries" in instructions
        assert "search_entries" in instructions
        assert "read_entry" in instructions
        assert "description" in instructions and "tags" in instructions

    def test_listing_omits_body(self, tmp_path: Path):
        """list_entries and search_entries return metadata only, no body."""
        tmp_path.mkdir(exist_ok=True)
        mcp = create_mcp_server(tmp_path)
        create = asyncio.run(mcp.get_tool("create_entry"))
        create.fn(name="note-x", description="a note", tags=[], body="secret body")

        listed = asyncio.run(mcp.get_tool("list_entries")).fn()
        assert listed and all("body" not in e for e in listed)

        found = asyncio.run(mcp.get_tool("search_entries")).fn(q="note")
        assert found and all("body" not in e for e in found)

    def test_write_tools_have_no_chat_dependency(self, tmp_path: Path):
        """create_entry succeeds with no chatbot module present (decoupled cache)."""
        import importlib.util

        assert importlib.util.find_spec("wikictl.server.chat") is None

        tmp_path.mkdir(exist_ok=True)
        mcp = create_mcp_server(tmp_path)
        tool = asyncio.run(mcp.get_tool("create_entry"))
        result = tool.fn(name="decoupled", description="works without chat", tags=[], body="x")
        assert result["name"] == "decoupled"
