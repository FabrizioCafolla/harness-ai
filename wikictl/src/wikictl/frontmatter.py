"""YAML frontmatter parsing and serialization for wiki entries."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import frontmatter

from wikictl.models import WikiEntry


def _parse_datetime(value: str | datetime) -> datetime:
    """Convert a string or datetime to a timezone-aware datetime."""
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
    elif isinstance(value, datetime):
        dt = value
    else:
        return datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _format_datetime(value: str | datetime) -> str:
    """Format a datetime or string to ISO 8601 string."""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def parse_file(path: Path) -> WikiEntry:
    """Parse a markdown file with YAML frontmatter into a WikiEntry."""
    post = frontmatter.load(str(path))
    meta = post.metadata

    created_at = _parse_datetime(meta.get("created_at", datetime.now(UTC)))
    updated_at = _parse_datetime(meta.get("updated_at", datetime.now(UTC)))

    return WikiEntry(
        name=meta["name"],
        description=meta.get("description", ""),
        tags=meta.get("tags", []),
        created_at=created_at,
        updated_at=updated_at,
        body=post.content,
        section=meta.get("section"),
        path=path,
    )


def serialize_entry(entry: WikiEntry) -> str:
    """Serialize a WikiEntry to a markdown string with YAML frontmatter."""
    post = frontmatter.Post(
        content=entry.body,
        name=entry.name,
        description=entry.description,
        tags=entry.tags,
        created_at=_format_datetime(entry.created_at),
        updated_at=_format_datetime(entry.updated_at),
        **({"section": entry.section} if entry.section is not None else {}),
    )
    return frontmatter.dumps(post) + "\n"
