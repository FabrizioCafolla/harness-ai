"""MCP server exposing wiki CRUD operations via fastmcp."""

from __future__ import annotations

import time
import uuid
from pathlib import Path

import structlog
from fastmcp import FastMCP


def _log_start(log, tool: str, params: dict) -> tuple[str, float]:
    """Log tool start and return invocation_id and start time."""
    invocation_id = str(uuid.uuid4())[:8]
    log.info("mcp_tool_start", tool=tool, params=params, invocation_id=invocation_id)
    return invocation_id, time.perf_counter()


def _log_complete(log, tool: str, invocation_id: str, start: float) -> None:
    """Log tool completion with duration."""
    duration_ms = round((time.perf_counter() - start) * 1000)
    log.info(
        "mcp_tool_complete",
        tool=tool,
        status="ok",
        duration_ms=duration_ms,
        invocation_id=invocation_id,
    )


def create_mcp_server(wiki_dir: Path) -> FastMCP:
    """Create a FastMCP server with wiki CRUD tools."""
    mcp = FastMCP(
        "wikictl",
        instructions=(
            "File-based wiki memory layer for AI agents. Follow the metadata-first "
            "workflow: scan with `list_entries` or `search_entries` (these return "
            "metadata only — name, description, tags — never the body), judge relevance "
            "from each entry's `description` and `tags`, then call `read_entry` only for "
            "the entries you actually need. Call `get_schema` to learn the entry metadata "
            "contract before writing. Write tools: create_entry, edit_entry, move_entry, "
            "delete_entry."
        ),
    )
    log = structlog.get_logger("wikictl.mcp")

    @mcp.tool()
    def get_schema() -> dict:
        """Return the wiki entry metadata contract (fields, types, required/optional,
        validation rules, write-controlled vs auto-managed). Needs no entries to exist.
        Call this before creating or editing entries."""
        from wikictl.models import metadata_schema

        inv_id, start = _log_start(log, "get_schema", {})
        result = metadata_schema()
        _log_complete(log, "get_schema", inv_id, start)
        return result

    @mcp.tool()
    def list_entries(tag: str | None = None) -> list[dict]:
        """Scan entries: returns metadata only (name, description, tags, section) — no
        body. Step 1 of the metadata-first workflow; read bodies with read_entry after
        selecting by description/tags. Optionally filter by tag."""
        from wikictl.core import list_entries as _list_entries

        inv_id, start = _log_start(log, "list_entries", {"tag": tag})
        entries = _list_entries(wiki_dir, tag=tag)
        result = [e.to_metadata_dict(wiki_dir) for e in entries]
        _log_complete(log, "list_entries", inv_id, start)
        return result

    @mcp.tool()
    def read_entry(name: str) -> dict:
        """Read one entry by name, including its full body. Call this only after
        selecting an entry from list_entries/search_entries by its description/tags."""
        from wikictl.core import read_entry as _read_entry

        inv_id, start = _log_start(log, "read_entry", {"name": name})
        entry = _read_entry(wiki_dir, name)
        data = entry.to_metadata_dict(wiki_dir)
        data["body"] = entry.body
        _log_complete(log, "read_entry", inv_id, start)
        return data

    @mcp.tool()
    def search_entries(q: str | None = None, tag: str | None = None) -> list[dict]:
        """Scan entries matching a text query (over name + description) and/or tag:
        returns metadata only — no body. Step 1 of the metadata-first workflow; read
        bodies with read_entry after selecting by description/tags."""
        from wikictl.core import list_entries as _list_entries

        inv_id, start = _log_start(log, "search_entries", {"q": q, "tag": tag})
        entries = _list_entries(wiki_dir, tag=tag)
        if q:
            q_lower = q.lower()
            entries = [
                e for e in entries if q_lower in e.name.lower() or q_lower in e.description.lower()
            ]
        result = [e.to_metadata_dict(wiki_dir) for e in entries]
        _log_complete(log, "search_entries", inv_id, start)
        return result

    @mcp.tool()
    def list_tags() -> list[str]:
        """List all unique tags across entries, sorted. Use tags to narrow a scan via
        the `tag` filter on list_entries/search_entries."""
        from wikictl.core import list_entries as _list_entries

        inv_id, start = _log_start(log, "list_tags", {})
        entries = _list_entries(wiki_dir)
        result = sorted({tag for entry in entries for tag in entry.tags})
        _log_complete(log, "list_tags", inv_id, start)
        return result

    @mcp.tool()
    def create_entry(
        name: str,
        description: str,
        tags: list[str] | None = None,
        body: str = "",
        section: str | None = None,
    ) -> dict:
        """Create a new wiki entry."""
        from wikictl.core import create_entry as _create_entry

        inv_id, start = _log_start(log, "create_entry", {"name": name})
        entry = _create_entry(wiki_dir, name, description, tags, body, section=section)
        _log_complete(log, "create_entry", inv_id, start)
        return entry.to_metadata_dict(wiki_dir)

    @mcp.tool()
    def edit_entry(
        name: str,
        description: str | None = None,
        tags: list[str] | None = None,
        body: str | None = None,
        section: str | None = None,
    ) -> dict:
        """Edit an existing wiki entry. Only provided fields are updated."""
        from wikictl.core import edit_entry as _edit_entry

        inv_id, start = _log_start(log, "edit_entry", {"name": name})
        entry = _edit_entry(wiki_dir, name, description=description, tags=tags, body=body)
        _log_complete(log, "edit_entry", inv_id, start)
        return entry.to_metadata_dict(wiki_dir)

    @mcp.tool()
    def move_entry(name: str, folder: str) -> dict:
        """Move an entry into a wiki sub-folder (e.g. "study/ai-k8s"); empty = root."""
        from wikictl.core import move_entry as _move_entry

        inv_id, start = _log_start(log, "move_entry", {"name": name, "folder": folder})
        entry = _move_entry(wiki_dir, name, folder)
        _log_complete(log, "move_entry", inv_id, start)
        return entry.to_metadata_dict(wiki_dir)

    @mcp.tool()
    def delete_entry(name: str) -> dict:
        """Delete a wiki entry by name."""
        from wikictl.core import delete_entry as _delete_entry

        inv_id, start = _log_start(log, "delete_entry", {"name": name})
        _delete_entry(wiki_dir, name)
        _log_complete(log, "delete_entry", inv_id, start)
        return {"deleted": name}

    return mcp
