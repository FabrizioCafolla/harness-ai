"""JSON API routes for wikictl server."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException, Request


def wiki_signature(wiki_dir: Path) -> str:
    """A cheap token that changes whenever any wiki markdown file changes.

    Every mutation (create/edit/move/delete) rewrites index.md, so its mtime —
    plus the file count — is enough for clients to detect changes and refresh.
    """
    latest = 0.0
    count = 0
    for path in wiki_dir.rglob("*.md"):
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
        count += 1
    return f"{count}:{latest:.3f}"


def create_api_router() -> APIRouter:
    """Create the API router with JSON endpoints."""
    from wikictl.core import list_entries, read_entry

    router = APIRouter(prefix="/api")

    @router.get("/entries")
    def api_list_entries(request: Request):
        wiki_dir = request.app.state.wiki_dir
        entries = list_entries(wiki_dir)
        return [e.to_metadata_dict(wiki_dir) for e in entries]

    @router.get("/entries/{name}")
    def api_get_entry(name: str, request: Request):
        wiki_dir = request.app.state.wiki_dir
        try:
            entry = read_entry(wiki_dir, name)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Entry '{name}' not found")

        import markdown_it

        md = markdown_it.MarkdownIt("commonmark", {"typographer": True}).enable("table")
        data = entry.to_metadata_dict(wiki_dir)
        data["body"] = entry.body
        data["body_html"] = md.render(entry.body)
        return data

    @router.get("/version")
    def api_version(request: Request):
        """Wiki change token, polled by the browser to auto-refresh on changes."""
        return {"version": wiki_signature(request.app.state.wiki_dir)}

    @router.get("/tags")
    def api_list_tags(request: Request):
        wiki_dir = request.app.state.wiki_dir
        entries = list_entries(wiki_dir)
        tags = sorted({tag for entry in entries for tag in entry.tags})
        return tags

    @router.get("/search")
    def api_search(request: Request, tag: str | None = None, q: str | None = None):
        wiki_dir = request.app.state.wiki_dir
        entries = list_entries(wiki_dir, tag=tag)
        if q:
            q_lower = q.lower()
            entries = [
                e for e in entries if q_lower in e.name.lower() or q_lower in e.description.lower()
            ]
        return [e.to_metadata_dict(wiki_dir) for e in entries]

    return router
