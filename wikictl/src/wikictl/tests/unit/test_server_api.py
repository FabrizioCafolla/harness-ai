"""Unit tests for wikictl server API endpoints."""

from pathlib import Path

from starlette.testclient import TestClient

from wikictl.core import create_entry
from wikictl.server import create_app


def _client(wiki_dir: Path) -> TestClient:
    app = create_app(wiki_dir)
    return TestClient(app)


class TestApiVersion:
    def test_version_changes_after_mutation(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        v1 = client.get("/api/version").json()["version"]
        create_entry(tmp_path, "new-entry", "desc")
        v2 = client.get("/api/version").json()["version"]
        assert v1 != v2


class TestApiEntries:
    def test_list_entries_empty(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/entries")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_entries(self, tmp_path: Path):
        create_entry(tmp_path, "note-a", "A note", ["tag1"])
        create_entry(tmp_path, "note-b", "B note")
        client = _client(tmp_path)
        resp = client.get("/api/entries")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["name"] == "note-a"
        assert "body" not in data[0]

    def test_get_entry(self, tmp_path: Path):
        create_entry(tmp_path, "my-entry", "desc", body="# Hello")
        client = _client(tmp_path)
        resp = client.get("/api/entries/my-entry")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-entry"
        assert data["body"] == "# Hello"
        assert "<h1>" in data["body_html"]

    def test_get_entry_not_found(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/entries/nope")
        assert resp.status_code == 404

    def test_list_tags(self, tmp_path: Path):
        create_entry(tmp_path, "a", "d", ["python", "docs"])
        create_entry(tmp_path, "b", "d", ["python", "cli"])
        client = _client(tmp_path)
        resp = client.get("/api/tags")
        assert resp.status_code == 200
        assert resp.json() == ["cli", "docs", "python"]

    def test_search_by_tag(self, tmp_path: Path):
        create_entry(tmp_path, "tagged", "d", ["python"])
        create_entry(tmp_path, "other", "d", ["go"])
        client = _client(tmp_path)
        resp = client.get("/api/search", params={"tag": "python"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["name"] == "tagged"

    def test_entries_include_url(self, tmp_path: Path):
        create_entry(tmp_path, "has-url", "d")
        client = _client(tmp_path)
        resp = client.get("/api/entries")
        data = resp.json()
        assert "url" in data[0]
        assert data[0]["url"] == "/wiki/has-url"

    def test_get_entry_includes_url(self, tmp_path: Path):
        create_entry(tmp_path, "my-wiki", "desc")
        client = _client(tmp_path)
        resp = client.get("/api/entries/my-wiki")
        data = resp.json()
        assert data["url"] == "/wiki/my-wiki"


class TestChatEndpointRemoved:
    def test_post_chat_returns_404(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.post("/api/chat", json={"message": "hi"})
        assert resp.status_code == 404

    def test_chat_status_returns_404(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/api/chat/status")
        assert resp.status_code == 404
