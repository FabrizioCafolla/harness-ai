"""Data models for wiki entries."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

KEBAB_CASE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_name(name: str) -> str:
    """Validate that a name is kebab-case. Returns the name or raises ValueError."""
    if not KEBAB_CASE_RE.match(name):
        msg = f"Name must be kebab-case (lowercase letters, numbers, hyphens): got '{name}'"
        raise ValueError(msg)
    return name


@dataclass
class WikiEntry:
    """A wiki memory entry with metadata and body content."""

    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    body: str = ""
    section: str | None = None
    path: Path | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        validate_name(self.name)

    def wiki_url(self, wiki_dir: Path) -> str:
        """Return the /wiki/<path> URL for this entry."""
        if self.path is not None:
            try:
                return "/wiki/" + self.path.relative_to(wiki_dir).with_suffix("").as_posix()
            except ValueError:
                pass
        return f"/wiki/{self.name}"

    def to_metadata_dict(self, wiki_dir: Path | None = None) -> dict:
        """Return metadata-only dict (no body) for progressive disclosure."""
        d: dict = {
            "name": self.name,
            "description": self.description,
            "tags": self.tags,
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime)
                else str(self.created_at)
            ),
            "updated_at": (
                self.updated_at.isoformat()
                if isinstance(self.updated_at, datetime)
                else str(self.updated_at)
            ),
            "section": self.section,
        }
        if wiki_dir is not None:
            d["url"] = self.wiki_url(wiki_dir)
        return d


METADATA_FIRST_NOTE = (
    "Metadata-first workflow: scan entries with list/search (metadata only — name, "
    "description, tags, no body), judge relevance from `description` and `tags`, then "
    "read the body of only the entries you selected."
)


def metadata_schema() -> dict:
    """Return the wiki entry metadata contract.

    Single source of truth backing the `get_schema` MCP tool and the `wikictl schema`
    CLI command, so the two surfaces cannot diverge. Requires no wiki entries to exist.

    Each field carries its type, whether it is required, whether it is client-writable
    (`managed: "write"`) or auto-managed by the system (`managed: "auto"`), and its
    validation/usage rules.
    """
    return {
        "entry": "WikiEntry",
        "fields": [
            {
                "name": "name",
                "type": "string",
                "required": True,
                "managed": "write",
                "rules": (
                    "kebab-case (lowercase letters, numbers, hyphens); unique; the entry's "
                    "stable identifier and filename"
                ),
            },
            {
                "name": "description",
                "type": "string",
                "required": True,
                "managed": "write",
                "rules": (
                    "one-line summary; the relevance signal scanned during list/search "
                    "before any body is read"
                ),
            },
            {
                "name": "tags",
                "type": "list[string]",
                "required": False,
                "managed": "write",
                "rules": "optional labels for filtering and relevance; defaults to empty",
            },
            {
                "name": "section",
                "type": "string | null",
                "required": False,
                "managed": "write",
                "rules": "optional grouping label used in the generated index; defaults to null",
            },
            {
                "name": "body",
                "type": "string",
                "required": False,
                "managed": "write",
                "rules": "Markdown content; returned only by read_entry, never by list/search",
            },
            {
                "name": "created_at",
                "type": "string (ISO 8601)",
                "required": False,
                "managed": "auto",
                "rules": "set on creation; not writable by clients",
            },
            {
                "name": "updated_at",
                "type": "string (ISO 8601)",
                "required": False,
                "managed": "auto",
                "rules": "set on every write; not writable by clients",
            },
        ],
        "usage": METADATA_FIRST_NOTE,
    }
