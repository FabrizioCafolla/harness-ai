"""Web server for wikictl wiki browsing."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from wikictl.logging import configure_logging
from wikictl.server.middleware import RequestLoggingMiddleware
from wikictl.server.routes_api import create_api_router
from wikictl.server.routes_html import create_html_router


def create_app(wiki_dir: Path) -> FastAPI:
    """Create a FastAPI application serving the wiki at wiki_dir."""
    from wikictl.server.mcp import create_mcp_server

    # Configure logging for the server
    log_format = os.environ.get("WIKICTL_LOG_FORMAT", "console")
    configure_logging(level="INFO", fmt=log_format)

    # Create MCP server and its ASGI app
    mcp = create_mcp_server(wiki_dir)
    mcp_app = mcp.http_app(path="/")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        async with mcp_app.lifespan(mcp_app):
            yield

    app = FastAPI(title="wikictl", description="Wiki browser", lifespan=lifespan)
    app.state.wiki_dir = wiki_dir

    app.add_middleware(RequestLoggingMiddleware)

    app.include_router(create_api_router())
    app.include_router(create_html_router())

    # Mount MCP server
    app.mount("/mcp", mcp_app)

    # Store MCP server reference for info endpoint
    app.state.mcp_server = mcp

    return app


def create_app_from_env() -> FastAPI:
    """Create the FastAPI app reading wiki dir from WIKICTL_DIR env var.

    Used by Gunicorn as the app factory.
    """
    wiki_dir = Path(os.environ.get("WIKICTL_DIR", "wiki"))
    return create_app(wiki_dir)
