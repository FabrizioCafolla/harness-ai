"""Core business logic for wiki entry management."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import structlog

from wikictl.frontmatter import parse_file, serialize_entry
from wikictl.models import WikiEntry, validate_name

RESERVED_NAMES = frozenset({"index"})

log = structlog.get_logger("wikictl.core")


def _check_reserved_name(name: str) -> None:
    """Raise ValueError if name is reserved."""
    if name in RESERVED_NAMES:
        msg = f"'{name}' is a reserved name and cannot be created, edited, or deleted manually"
        raise ValueError(msg)


def resolve_wiki_dir(cli_flag: str | None = None) -> Path:
    """Resolve wiki directory: CLI flag > env var > ./wiki/ default."""
    if cli_flag:
        return Path(cli_flag)
    env_dir = os.environ.get("WIKICTL_DIR")
    if env_dir:
        return Path(env_dir)
    return Path("wiki")


def _entry_path(wiki_dir: Path, name: str) -> Path:
    return wiki_dir / f"{name}.md"


def _find_entry_path(wiki_dir: Path, name: str) -> Path:
    """Find an entry file by name, searching flat first then recursively."""
    flat = wiki_dir / f"{name}.md"
    if flat.exists():
        return flat
    matches = list(wiki_dir.rglob(f"{name}.md"))
    if not matches:
        raise FileNotFoundError(f"Entry '{name}' not found under {wiki_dir}")
    return matches[0]


_SENTINEL = object()


def rebuild_index(wiki_dir: Path) -> Path:
    """Regenerate index.md from all entries, grouped by section alphabetically.

    Entries without a section go under "Uncategorized" at the end.
    Returns the path to the generated index.md.
    """
    entries = list_entries(wiki_dir)

    sections: dict[str, list[WikiEntry]] = {}
    uncategorized: list[WikiEntry] = []

    for entry in entries:
        if entry.section:
            sections.setdefault(entry.section, []).append(entry)
        else:
            uncategorized.append(entry)

    lines = ["# Wiki Index", ""]

    for section_name in sorted(sections):
        lines.append(f"## {section_name}")
        lines.append("")
        for entry in sorted(sections[section_name], key=lambda e: e.name):
            tags = f" `{', '.join(entry.tags)}`" if entry.tags else ""
            rel = entry.path.relative_to(wiki_dir) if entry.path else Path(f"{entry.name}.md")
            lines.append(f"- [{entry.name}]({rel}) - {entry.description}{tags}")
        lines.append("")

    if uncategorized:
        lines.append("## Uncategorized")
        lines.append("")
        for entry in sorted(uncategorized, key=lambda e: e.name):
            tags = f" `{', '.join(entry.tags)}`" if entry.tags else ""
            rel = entry.path.relative_to(wiki_dir) if entry.path else Path(f"{entry.name}.md")
            lines.append(f"- [{entry.name}]({rel}) - {entry.description}{tags}")
        lines.append("")

    index_path = wiki_dir / "index.md"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text("\n".join(lines), encoding="utf-8")
    log.debug("index_rebuilt", path=str(index_path))
    return index_path


def create_entry(
    wiki_dir: Path,
    name: str,
    description: str,
    tags: list[str] | None = None,
    body: str = "",
    section: str | None = None,
) -> WikiEntry:
    """Create a new wiki entry. Raises FileExistsError if name taken, ValueError if invalid."""
    validate_name(name)
    _check_reserved_name(name)
    wiki_dir.mkdir(parents=True, exist_ok=True)

    path = _entry_path(wiki_dir, name)
    if path.exists():
        msg = f"Entry '{name}' already exists at {path}"
        raise FileExistsError(msg)

    now = datetime.now(UTC)
    entry = WikiEntry(
        name=name,
        description=description,
        tags=tags or [],
        created_at=now,
        updated_at=now,
        body=body,
        section=section,
    )

    path.write_text(serialize_entry(entry), encoding="utf-8")
    rebuild_index(wiki_dir)
    log.info("entry_created", entry_name=name)
    return entry


def read_entry(wiki_dir: Path, name: str) -> WikiEntry:
    """Read a wiki entry by name. Raises FileNotFoundError if not found."""
    try:
        path = _find_entry_path(wiki_dir, name)
    except FileNotFoundError:
        log.error("entry_not_found", entry_name=name)
        msg = f"Entry '{name}' not found at {wiki_dir}"
        raise FileNotFoundError(msg)
    log.debug("entry_read", entry_name=name)
    return parse_file(path)


def list_entries(wiki_dir: Path, tag: str | None = None) -> list[WikiEntry]:
    """List all wiki entries, optionally filtered by tag. Returns entries sorted by name."""
    if not wiki_dir.exists():
        return []

    entries = []
    for path in sorted(wiki_dir.rglob("*.md")):
        if path.stem in RESERVED_NAMES:
            continue
        try:
            entry = parse_file(path)
        except (KeyError, ValueError):
            continue  # skip malformed files
        if tag and tag not in entry.tags:
            continue
        entries.append(entry)

    return entries


def edit_entry(
    wiki_dir: Path,
    name: str,
    description: str | None = None,
    tags: list[str] | None = None,
    body: str | None = None,
    section: str | None = _SENTINEL,
) -> WikiEntry:
    """Edit an existing wiki entry. Only provided fields are updated. Raises FileNotFoundError."""
    _check_reserved_name(name)
    entry = read_entry(wiki_dir, name)

    if description is not None:
        entry.description = description
    if tags is not None:
        entry.tags = tags
    if body is not None:
        entry.body = body
    if section is not _SENTINEL:
        entry.section = section

    entry.updated_at = datetime.now(UTC)

    path = entry.path or _entry_path(wiki_dir, name)
    path.write_text(serialize_entry(entry), encoding="utf-8")
    rebuild_index(wiki_dir)
    log.info("entry_updated", entry_name=name)
    return entry


def move_entry(wiki_dir: Path, name: str, folder: str) -> WikiEntry:
    """Move an entry's file into a sub-folder of the wiki (e.g. "study/ai-k8s").

    Pass an empty folder to move the entry back to the wiki root. Rebuilds the
    index. Raises FileNotFoundError if the entry is missing, ValueError for an
    invalid folder, FileExistsError if the destination is already taken.
    """
    _check_reserved_name(name)
    src = _find_entry_path(wiki_dir, name)

    rel = Path(folder.strip("/")) if folder else Path()
    if rel.is_absolute() or ".." in rel.parts:
        msg = f"Invalid folder: {folder!r}"
        raise ValueError(msg)

    wiki_root = wiki_dir.resolve()
    dest_dir = (wiki_dir / rel).resolve()
    if dest_dir != wiki_root and wiki_root not in dest_dir.parents:
        msg = f"Folder escapes the wiki directory: {folder!r}"
        raise ValueError(msg)

    dest = dest_dir / f"{name}.md"
    if dest == src:
        return parse_file(src)
    if dest.exists():
        msg = f"Entry '{name}' already exists at {dest}"
        raise FileExistsError(msg)

    dest_dir.mkdir(parents=True, exist_ok=True)
    src.rename(dest)
    rebuild_index(wiki_dir)
    log.info("entry_moved", entry_name=name, folder=str(rel) or ".")
    return parse_file(dest)


def delete_entry(wiki_dir: Path, name: str) -> None:
    """Delete a wiki entry. Raises FileNotFoundError if not found."""
    _check_reserved_name(name)
    try:
        path = _find_entry_path(wiki_dir, name)
    except FileNotFoundError:
        log.error("entry_not_found", entry_name=name)
        msg = f"Entry '{name}' not found at {wiki_dir}"
        raise FileNotFoundError(msg)
    path.unlink()
    rebuild_index(wiki_dir)
    log.info("entry_deleted", entry_name=name)
