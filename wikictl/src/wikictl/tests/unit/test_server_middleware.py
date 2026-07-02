"""Tests for server request logging middleware."""

from __future__ import annotations

from pathlib import Path

from starlette.testclient import TestClient

from wikictl.server import create_app


def _client(wiki_dir: Path) -> TestClient:
    app = create_app(wiki_dir)
    return TestClient(app)


class TestRequestLoggingMiddleware:
    def test_response_has_request_id_header(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/entries")
        assert "x-request-id" in resp.headers
        # Should be a valid UUID-like string
        assert len(resp.headers["x-request-id"]) > 0

    def test_client_provided_request_id_is_used(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/entries", headers={"X-Request-ID": "my-custom-id-123"})
        assert resp.headers["x-request-id"] == "my-custom-id-123"

    def test_generated_request_id_is_uuid(self, tmp_path: Path):
        import uuid

        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/entries")
        # Should parse as valid UUID
        uuid.UUID(resp.headers["x-request-id"])
