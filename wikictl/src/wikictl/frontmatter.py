"""YAML frontmatter parsing and serialization for wiki entries."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import frontmatter
import yaml

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


class MalformedEntryError(ValueError):
    """A file opens with a `---` block that is not parseable YAML.

    Subclasses ValueError so every existing `except ValueError` path keeps
    working, while carrying the offending path for a message a human can act on.
    """

    def __init__(self, path: Path, reason: str) -> None:
        self.path = path
        self.reason = reason
        super().__init__(f"{path}: the `---` header block is not valid YAML ({reason})")


def parse_file(path: Path) -> WikiEntry:
    """Parse a markdown file with YAML frontmatter into a WikiEntry.

    Raises MalformedEntryError (a ValueError) when the leading `---` block
    cannot be parsed, and KeyError when it parses but carries no `name` (i.e.
    the file simply is not a wiki entry).
    """
    try:
        post = frontmatter.load(str(path))
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f"line {mark.line + 1}, column {mark.column + 1}" if mark else "position unknown"
        problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
        raise MalformedEntryError(path, f"{problem} at {where}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise MalformedEntryError(path, str(exc)) from exc
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
