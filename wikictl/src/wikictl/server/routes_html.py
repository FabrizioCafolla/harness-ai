"""HTML routes for wikictl server."""

from __future__ import annotations

import os
import re
from pathlib import Path

import markdown_it as _mdit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from jinja2 import Environment, FileSystemLoader

from wikictl.models import WikiEntry

_MD_LINK_RE = re.compile(r'href="([^"#?]+)\.md"')

_ACRONYMS = {
    "Sre": "SRE",
    "Aws": "AWS",
    "Eks": "EKS",
    "Api": "API",
    "Cfp": "CFP",
    "Mcp": "MCP",
    "Iac": "IaC",
    "Ai": "AI",
    "Ml": "ML",
    "Tcp": "TCP",
    "Ip": "IP",
    "Ssl": "SSL",
    "Tls": "TLS",
    "Dns": "DNS",
    "Http": "HTTP",
    "K8S": "K8s",
}

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _md() -> _mdit.MarkdownIt:
    return _mdit.MarkdownIt("commonmark", {"typographer": True}).enable("table")


def _rewrite_links(html: str, page_path: str = "") -> str:
    """Rewrite .md hrefs to absolute /wiki/ URLs, resolving relative paths.

    page_path: wiki-relative path of the current page (e.g. "study/sre/module/lesson").
    """
    if page_path:
        parent = "/wiki/" + "/".join(page_path.split("/")[:-1])
        parent = parent.rstrip("/")
    else:
        parent = "/wiki"

    def _replace(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "/")):
            return m.group(0)
        return 'href="' + os.path.normpath(parent + "/" + href) + '"'

    return _MD_LINK_RE.sub(_replace, html)


def _subsection_display(raw: str) -> str:
    clean = re.sub(r"^\d+-", "", raw)
    words = clean.replace("-", " ").title().split()
    return " ".join(_ACRONYMS.get(w, w) for w in words)


def _build_sidebar_tree(entries: list[WikiEntry], wiki_dir: Path) -> list[dict]:
    """Build a nested tree of dicts for the collapsible sidebar."""

    class _N:
        __slots__ = ("display", "key", "sub", "leaves")

        def __init__(self, display: str, key: str):
            self.display = display
            self.key = key
            self.sub: dict[str, _N] = {}
            self.leaves: list[WikiEntry] = []

        def to_dict(self) -> dict:
            items: list[tuple[str, str, object]] = [
                (seg.lower(), "folder", node) for seg, node in self.sub.items()
            ] + [(e.name.lower(), "entry", e) for e in self.leaves]
            items.sort(key=lambda x: x[0])
            children = []
            for _, kind, obj in items:
                if kind == "folder":
                    d = obj.to_dict()  # type: ignore[union-attr]
                    if d["children"]:
                        children.append(d)
                else:
                    e: WikiEntry = obj  # type: ignore[assignment]
                    children.append(
                        {
                            "display": (e.description or e.name)[:52],
                            "key": f"e-{e.name}",
                            "url": e.wiki_url(wiki_dir),
                            "children": [],
                            "entry": e,
                        }
                    )
            return {
                "display": self.display,
                "key": self.key,
                "url": None,
                "children": children,
                "entry": None,
            }

    roots: dict[str, _N] = {}
    flat: list[WikiEntry] = []

    for entry in entries:
        if entry.path is None:
            flat.append(entry)
            continue
        try:
            rel = entry.path.relative_to(wiki_dir)
        except ValueError:
            flat.append(entry)
            continue
        parts = rel.parts
        if len(parts) < 2:
            flat.append(entry)
            continue
        seg0 = parts[0]
        if seg0 not in roots:
            roots[seg0] = _N(_subsection_display(seg0), seg0)
        node = roots[seg0]
        for seg in parts[1:-1]:
            if seg not in node.sub:
                node.sub[seg] = _N(_subsection_display(seg), f"{node.key}/{seg}")
            node = node.sub[seg]
        node.leaves.append(entry)

    result = [roots[k].to_dict() for k in sorted(roots)]

    if flat:
        by_sec: dict[str, list[WikiEntry]] = {}
        for e in flat:
            by_sec.setdefault(e.section or "Other", []).append(e)
        for sec in sorted(by_sec):
            children = [
                {
                    "display": (e.description or e.name)[:52],
                    "key": f"e-{e.name}",
                    "url": e.wiki_url(wiki_dir),
                    "children": [],
                    "entry": e,
                }
                for e in sorted(by_sec[sec], key=lambda e: e.name)
            ]
            result.append(
                {
                    "display": sec,
                    "key": sec.lower().replace(" ", "-"),
                    "url": None,
                    "children": children,
                    "entry": None,
                }
            )

    return result


def _build_breadcrumbs(path: str, entry: WikiEntry) -> list[dict]:
    """Derive breadcrumbs from the same folder/section path used to build
    the sidebar (see _build_sidebar_tree) — no separate hierarchy source.

    Folder segments link to that folder's anchor in the sidebar (rendered on
    every page, entry pages included) via id="tree-<key>" — there's no
    dedicated folder page to link to instead, and the sidebar is always
    present, so scrolling to it there is the closest equivalent."""
    folder_segments = path.split("/")[:-1]
    crumbs = [{"display": "Home", "url": "/"}]
    if folder_segments:
        cumulative_key = ""
        for seg in folder_segments:
            cumulative_key = seg if not cumulative_key else f"{cumulative_key}/{seg}"
            anchor = "tree-" + cumulative_key.replace("/", "-")
            crumbs.append({"display": _subsection_display(seg), "url": f"#{anchor}"})
    elif entry.section:
        anchor = "tree-" + entry.section.lower().replace(" ", "-")
        crumbs.append({"display": entry.section, "url": f"#{anchor}"})
    crumbs.append({"display": entry.description or entry.name, "url": None})
    return crumbs


def _format_date(value) -> str:
    from datetime import datetime as dt

    if isinstance(value, dt):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, str):
        try:
            return dt.fromisoformat(value.replace("Z", "+00:00")).strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            pass
    return str(value)


def create_html_router() -> APIRouter:
    from wikictl.core import list_entries, read_entry

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=True, auto_reload=False
    )
    env.filters["format_date"] = _format_date

    router = APIRouter()

    def _render(template_name: str, request: Request, active_url: str = "", **kwargs) -> str:
        wiki_dir = request.app.state.wiki_dir
        sidebar_tree = _build_sidebar_tree(list_entries(wiki_dir), wiki_dir)
        return env.get_template(template_name).render(
            request=request,
            sidebar_tree=sidebar_tree,
            active_url=active_url,
            **kwargs,
        )

    @router.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return HTMLResponse(_render("index.html", request))

    @router.get("/wiki/{path:path}", response_class=HTMLResponse)
    def wiki_entry_page(path: str, request: Request):
        from wikictl.frontmatter import parse_file

        wiki_dir = request.app.state.wiki_dir
        file_path = wiki_dir / (path + ".md")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"'{path}' not found")

        entry = parse_file(file_path)
        body_html = _rewrite_links(_md().render(entry.body), page_path=path)
        breadcrumbs = _build_breadcrumbs(path, entry)
        return HTMLResponse(
            _render(
                "entry.html",
                request,
                active_url=f"/wiki/{path}",
                entry=entry,
                body_html=body_html,
                breadcrumbs=breadcrumbs,
            )
        )

    @router.get("/mcp-info", response_class=HTMLResponse)
    def mcp_info(request: Request):
        import asyncio

        mcp_server = request.app.state.mcp_server
        tools = asyncio.run(mcp_server.list_tools())
        resources = asyncio.run(mcp_server.list_resources())
        tool_data = [
            {"name": t.name, "description": t.description or "", "parameters": t.parameters}
            for t in tools
        ]
        resource_data = [
            {"uri": str(r.uri), "name": r.name, "description": getattr(r, "description", "")}
            for r in resources
        ]
        return HTMLResponse(
            _render("mcp_info.html", request, tools=tool_data, resources=resource_data)
        )

    # --- Redirects ---

    @router.get("/entry/{name}")
    def entry_legacy_redirect(name: str, request: Request):
        wiki_dir = request.app.state.wiki_dir
        try:
            entry = read_entry(wiki_dir, name)
            return RedirectResponse(url=entry.wiki_url(wiki_dir), status_code=301)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail=f"Entry '{name}' not found")

    @router.get("/entries")
    def entries_redirect():
        return RedirectResponse(url="/", status_code=301)

    @router.get("/{name}.md")
    def redirect_md_link(name: str):
        return RedirectResponse(url=f"/wiki/{name}", status_code=301)

    return router
