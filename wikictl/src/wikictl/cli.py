"""CLI interface for wikictl."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from wikictl.core import (
    create_entry,
    delete_entry,
    edit_entry,
    list_entries,
    move_entry,
    read_entry,
    rebuild_index,
    resolve_wiki_dir,
)
from wikictl.frontmatter import serialize_entry
from wikictl.logging import configure_logging, get_logger
from wikictl.models import metadata_schema


@click.group()
@click.version_option(package_name="wikictl")
@click.option(
    "--wiki-dir",
    default=None,
    envvar="WIKICTL_DIR",
    help="Wiki directory path. Overrides WIKICTL_DIR env var. Default: ./wiki/",
)
@click.option("--verbose", "-v", count=True, help="Increase log verbosity (-vv for DEBUG)")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output except errors")
@click.pass_context
def cli(ctx: click.Context, wiki_dir: str | None, verbose: int, quiet: bool) -> None:
    """wikictl - A file-based memory layer for AI agents."""
    ctx.ensure_object(dict)
    ctx.obj["wiki_dir"] = resolve_wiki_dir(wiki_dir)

    # Determine log level: CLI flags > env var > default (WARNING)
    if quiet:
        level = "ERROR"
    elif verbose >= 2:
        level = "DEBUG"
    elif verbose == 1:
        level = "INFO"
    else:
        level = os.environ.get("WIKICTL_LOG_LEVEL", "WARNING").upper()

    configure_logging(level=level, fmt="console")


@cli.command()
@click.option("--name", "-n", required=True, help="Entry name (kebab-case)")
@click.option("--description", "-d", required=True, help="Short description")
@click.option("--tags", "-t", default="", help="Comma-separated tags")
@click.option("--body", "-b", default="", help="Body content in markdown")
@click.option("--section", "-s", default=None, help="Section for index grouping")
@click.pass_context
def create(
    ctx: click.Context, name: str, description: str, tags: str, body: str, section: str | None
) -> None:
    """Create a new wiki entry."""
    wiki_dir = ctx.obj["wiki_dir"]
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    body = body.encode("raw_unicode_escape").decode("unicode_escape") if body else body

    log = get_logger("wikictl.cli")
    try:
        entry = create_entry(wiki_dir, name, description, tag_list, body, section=section)
    except ValueError as e:
        log.error("entry_create_failed", entry_name=name, error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except FileExistsError as e:
        log.error("entry_create_failed", entry_name=name, error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    log.info("entry_created", entry_name=entry.name)
    click.echo(f"Created entry: {entry.name}")


@cli.command()
@click.argument("name")
@click.pass_context
def read(ctx: click.Context, name: str) -> None:
    """Read a wiki entry by name."""
    wiki_dir = ctx.obj["wiki_dir"]
    log = get_logger("wikictl.cli")

    try:
        entry = read_entry(wiki_dir, name)
    except FileNotFoundError as e:
        log.error("entry_not_found", entry_name=name)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    log.info("entry_read", entry_name=name)
    click.echo(serialize_entry(entry))


@cli.command("list")
@click.option("--tag", "-t", default=None, help="Filter by tag")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def list_cmd(ctx: click.Context, tag: str | None, as_json: bool) -> None:
    """List wiki entries (metadata only)."""
    wiki_dir = ctx.obj["wiki_dir"]
    entries = list_entries(wiki_dir, tag=tag)

    if as_json:
        data = [e.to_metadata_dict() for e in entries]
        click.echo(json.dumps(data, indent=2))
        return

    if not entries:
        click.echo("No entries found.")
        return

    for entry in entries:
        tags_str = ", ".join(entry.tags) if entry.tags else ""
        click.echo(f"  {entry.name}")
        click.echo(f"    {entry.description}")
        if tags_str:
            click.echo(f"    tags: {tags_str}")
        click.echo()


@cli.command()
@click.argument("query")
@click.option("--tag", "-t", default=None, help="Filter by tag")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def search(ctx: click.Context, query: str, tag: str | None, as_json: bool) -> None:
    """Search entries (metadata only) by text over name and description."""
    wiki_dir = ctx.obj["wiki_dir"]
    entries = list_entries(wiki_dir, tag=tag)
    q_lower = query.lower()
    entries = [e for e in entries if q_lower in e.name.lower() or q_lower in e.description.lower()]

    if as_json:
        click.echo(json.dumps([e.to_metadata_dict() for e in entries], indent=2))
        return

    if not entries:
        click.echo("No matching entries.")
        return

    for entry in entries:
        tags_str = ", ".join(entry.tags) if entry.tags else ""
        click.echo(f"  {entry.name}")
        click.echo(f"    {entry.description}")
        if tags_str:
            click.echo(f"    tags: {tags_str}")
        click.echo()


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
@click.pass_context
def tags(ctx: click.Context, as_json: bool) -> None:
    """List unique tags across all entries, sorted alphabetically."""
    wiki_dir = ctx.obj["wiki_dir"]
    entries = list_entries(wiki_dir)
    all_tags = sorted({tag for entry in entries for tag in entry.tags})

    if as_json:
        click.echo(json.dumps(all_tags, indent=2))
        return

    if not all_tags:
        click.echo("No tags found.")
        return

    for tag in all_tags:
        click.echo(tag)


@cli.command()
@click.argument("name")
@click.argument("folder")
@click.pass_context
def move(ctx: click.Context, name: str, folder: str) -> None:
    """Move an entry into a wiki sub-folder (empty FOLDER moves it to the root)."""
    wiki_dir = ctx.obj["wiki_dir"]
    log = get_logger("wikictl.cli")

    try:
        entry = move_entry(wiki_dir, name, folder)
    except FileNotFoundError as e:
        log.error("entry_not_found", entry_name=name)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except (ValueError, FileExistsError) as e:
        log.error("entry_move_failed", entry_name=name, error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    log.info("entry_moved", entry_name=name, folder=folder)
    click.echo(f"Moved entry: {entry.name}")


@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def schema(as_json: bool) -> None:
    """Print the wiki entry metadata contract (same as the get_schema MCP tool)."""
    contract = metadata_schema()

    if as_json:
        click.echo(json.dumps(contract, indent=2))
        return

    for f in contract["fields"]:
        req = "required" if f["required"] else "optional"
        click.echo(f"  {f['name']} ({f['type']}, {req}, {f['managed']})")
        click.echo(f"    {f['rules']}")
        click.echo()
    click.echo(contract["usage"])


@cli.command()
@click.argument("name")
@click.option("--description", "-d", default=None, help="New description")
@click.option("--tags", "-t", default=None, help="New comma-separated tags")
@click.option("--body", "-b", default=None, help="New body content")
@click.option("--section", "-s", default=None, help="New section for index grouping")
@click.pass_context
def edit(
    ctx: click.Context,
    name: str,
    description: str | None,
    tags: str | None,
    body: str | None,
    section: str | None,
) -> None:
    """Edit an existing wiki entry."""
    wiki_dir = ctx.obj["wiki_dir"]
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags is not None else None
    body = body.encode("raw_unicode_escape").decode("unicode_escape") if body is not None else body
    log = get_logger("wikictl.cli")

    try:
        kwargs: dict = {"description": description, "tags": tag_list, "body": body}
        if ctx.get_parameter_source("section") == click.core.ParameterSource.COMMANDLINE:
            kwargs["section"] = section
        entry = edit_entry(wiki_dir, name, **kwargs)
    except FileNotFoundError as e:
        log.error("entry_not_found", entry_name=name)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        log.error("entry_edit_failed", entry_name=name, error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    log.info("entry_updated", entry_name=entry.name)
    click.echo(f"Updated entry: {entry.name}")


@cli.command()
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def delete(ctx: click.Context, name: str, force: bool) -> None:
    """Delete a wiki entry."""
    wiki_dir = ctx.obj["wiki_dir"]

    if not force:
        if not click.confirm(f"Delete entry '{name}'?"):
            click.echo("Cancelled.")
            return

    log = get_logger("wikictl.cli")
    try:
        delete_entry(wiki_dir, name)
    except FileNotFoundError as e:
        log.error("entry_not_found", entry_name=name)
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)
    except ValueError as e:
        log.error("entry_delete_failed", entry_name=name, error=str(e))
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    log.info("entry_deleted", entry_name=name)
    click.echo(f"Deleted entry: {name}")


@cli.command()
@click.pass_context
def index(ctx: click.Context) -> None:
    """Regenerate the wiki index.md file."""
    wiki_dir = ctx.obj["wiki_dir"]
    path = rebuild_index(wiki_dir)
    click.echo(f"Index regenerated: {path}")


def _check_serve_deps() -> None:
    """Check that optional serve dependencies are installed."""
    missing = []
    for mod in ("fastapi", "uvicorn", "jinja2", "markdown_it"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        click.echo(
            f"Error: Missing serve dependencies: {', '.join(missing)}\n"
            "Install them with: pip install wikictl[serve]",
            err=True,
        )
        sys.exit(1)


@cli.command()
@click.option("--port", "-p", default=9797, help="Port to listen on (default: 9797)")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind to (default: 127.0.0.1)")
@click.pass_context
def serve(ctx: click.Context, port: int, host: str) -> None:
    """Start a read-only web server for browsing the wiki."""
    _check_serve_deps()

    import uvicorn

    from wikictl.server import create_app

    wiki_dir = ctx.obj["wiki_dir"]
    rebuild_index(wiki_dir)

    app = create_app(wiki_dir)
    click.echo(f"Serving wiki from {wiki_dir} at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)
