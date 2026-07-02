"""Unit tests for wikictl server HTML endpoints."""

from pathlib import Path

from starlette.testclient import TestClient

from wikictl.core import create_entry, rebuild_index
from wikictl.server import create_app


def _client(wiki_dir: Path) -> TestClient:
    app = create_app(wiki_dir)
    return TestClient(app)


class TestHtmlEndpoints:
    def test_home_page(self, tmp_path: Path):
        create_entry(tmp_path, "note-a", "A note", section="Docs")
        client = _client(tmp_path)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Docs" in resp.text
        assert "note-a" in resp.text

    def test_home_page_no_entries(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Index" in resp.text

    def test_entry_page(self, tmp_path: Path):
        create_entry(tmp_path, "my-entry", "A description", body="# Content")
        client = _client(tmp_path)
        resp = client.get("/wiki/my-entry")
        assert resp.status_code == 200
        assert "my-entry" in resp.text
        assert "Content" in resp.text

    def test_chat_page_removed(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/chat")
        assert resp.status_code == 404

    def test_no_chat_link_in_nav(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'href="/chat"' not in resp.text

    def test_entry_not_found(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/wiki/nope")
        assert resp.status_code == 404

    def test_entries_redirects_to_home(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        client = _client(tmp_path)
        resp = client.get("/entries", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == "/"

    def test_sidebar_shows_entries(self, tmp_path: Path):
        create_entry(tmp_path, "entry-a", "Desc A", ["tag1"], section="CLI")
        create_entry(tmp_path, "entry-b", "Desc B", section="Architecture")
        client = _client(tmp_path)
        resp = client.get("/")
        assert resp.status_code == 200
        # Sidebar contains both entries
        assert "entry-a" in resp.text
        assert "entry-b" in resp.text
        # Section headings present
        assert "CLI" in resp.text
        assert "Architecture" in resp.text

    def test_home_links_rewritten(self, tmp_path: Path):
        create_entry(tmp_path, "my-note", "A note")
        rebuild_index(tmp_path)
        client = _client(tmp_path)
        resp = client.get("/")
        assert resp.status_code == 200
        assert 'href="/wiki/my-note"' in resp.text
        assert 'href="my-note.md"' not in resp.text

    def test_md_redirect(self, tmp_path: Path):
        create_entry(tmp_path, "some-entry", "desc")
        client = _client(tmp_path)
        resp = client.get("/some-entry.md", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == "/wiki/some-entry"

    def test_entry_legacy_redirect(self, tmp_path: Path):
        create_entry(tmp_path, "old-entry", "desc")
        client = _client(tmp_path)
        resp = client.get("/entry/old-entry", follow_redirects=False)
        assert resp.status_code == 301
        assert resp.headers["location"] == "/wiki/old-entry"

    def test_active_entry_highlighted(self, tmp_path: Path):
        create_entry(tmp_path, "active-one", "desc")
        client = _client(tmp_path)
        resp = client.get("/wiki/active-one")
        assert resp.status_code == 200
        assert "active" in resp.text
