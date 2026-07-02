"""Unit tests for wikictl.core."""

from pathlib import Path

import pytest

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


class TestMoveEntry:
    def test_move_into_subfolder(self, tmp_path: Path):
        create_entry(tmp_path, "test-note", "A note", body="x")
        entry = move_entry(tmp_path, "test-note", "study/ai-k8s")
        assert entry.path == tmp_path / "study" / "ai-k8s" / "test-note.md"
        assert not (tmp_path / "test-note.md").exists()
        # Still resolvable by name (recursive lookup)
        assert read_entry(tmp_path, "test-note").description == "A note"

    def test_move_back_to_root(self, tmp_path: Path):
        create_entry(tmp_path, "n", "d")
        move_entry(tmp_path, "n", "sub")
        entry = move_entry(tmp_path, "n", "")
        assert entry.path == tmp_path / "n.md"

    def test_move_rejects_escape(self, tmp_path: Path):
        create_entry(tmp_path, "n", "d")
        with pytest.raises(ValueError):
            move_entry(tmp_path, "n", "../outside")

    def test_move_missing_entry(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        with pytest.raises(FileNotFoundError):
            move_entry(tmp_path, "nope", "sub")


class TestResolveWikiDir:
    def test_cli_flag_takes_precedence(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("WIKICTL_DIR", "/env/path")
        result = resolve_wiki_dir("/cli/path")
        assert result == Path("/cli/path")

    def test_env_var_fallback(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("WIKICTL_DIR", "/env/path")
        result = resolve_wiki_dir(None)
        assert result == Path("/env/path")

    def test_default(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("WIKICTL_DIR", raising=False)
        result = resolve_wiki_dir(None)
        assert result == Path("wiki")


class TestCreateEntry:
    def test_success(self, tmp_path: Path):
        entry = create_entry(tmp_path, "my-note", "A note", ["test"], "body")
        assert entry.name == "my-note"
        assert (tmp_path / "my-note.md").exists()

    def test_duplicate_raises(self, tmp_path: Path):
        create_entry(tmp_path, "dup", "first")
        with pytest.raises(FileExistsError, match="already exists"):
            create_entry(tmp_path, "dup", "second")

    def test_invalid_name_raises(self, tmp_path: Path):
        with pytest.raises(ValueError, match="kebab-case"):
            create_entry(tmp_path, "Bad Name", "desc")

    def test_creates_directory(self, tmp_path: Path):
        wiki_dir = tmp_path / "nested" / "wiki"
        create_entry(wiki_dir, "test", "desc")
        assert (wiki_dir / "test.md").exists()


class TestReadEntry:
    def test_success(self, tmp_path: Path):
        create_entry(tmp_path, "readable", "desc", body="content")
        entry = read_entry(tmp_path, "readable")
        assert entry.name == "readable"
        assert entry.body == "content"

    def test_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="not found"):
            read_entry(tmp_path, "nope")


class TestListEntries:
    def test_list_all(self, tmp_path: Path):
        create_entry(tmp_path, "b-note", "B")
        create_entry(tmp_path, "a-note", "A")
        entries = list_entries(tmp_path)
        assert len(entries) == 2
        assert entries[0].name == "a-note"  # sorted

    def test_filter_by_tag(self, tmp_path: Path):
        create_entry(tmp_path, "tagged", "desc", ["python"])
        create_entry(tmp_path, "untagged", "desc", ["go"])
        entries = list_entries(tmp_path, tag="python")
        assert len(entries) == 1
        assert entries[0].name == "tagged"

    def test_empty_directory(self, tmp_path: Path):
        assert list_entries(tmp_path) == []

    def test_nonexistent_directory(self, tmp_path: Path):
        assert list_entries(tmp_path / "nope") == []


class TestEditEntry:
    def test_update_description(self, tmp_path: Path):
        create_entry(tmp_path, "editable", "old desc")
        entry = edit_entry(tmp_path, "editable", description="new desc")
        assert entry.description == "new desc"

        reloaded = read_entry(tmp_path, "editable")
        assert reloaded.description == "new desc"

    def test_update_body(self, tmp_path: Path):
        create_entry(tmp_path, "editable", "desc", body="old")
        entry = edit_entry(tmp_path, "editable", body="new body")
        assert entry.body == "new body"

    def test_partial_update_preserves_other_fields(self, tmp_path: Path):
        create_entry(tmp_path, "partial", "desc", ["tag1"], "body")
        original = read_entry(tmp_path, "partial")

        edit_entry(tmp_path, "partial", description="updated")
        edited = read_entry(tmp_path, "partial")

        assert edited.description == "updated"
        assert edited.tags == ["tag1"]
        assert edited.body == "body"
        assert edited.created_at == original.created_at
        assert edited.updated_at > original.updated_at

    def test_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            edit_entry(tmp_path, "nope", description="x")


class TestDeleteEntry:
    def test_success(self, tmp_path: Path):
        create_entry(tmp_path, "deletable", "desc")
        delete_entry(tmp_path, "deletable")
        assert not (tmp_path / "deletable.md").exists()

    def test_not_found(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            delete_entry(tmp_path, "nope")


class TestIndexNameProtection:
    def test_create_index_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="reserved name"):
            create_entry(tmp_path, "index", "desc")

    def test_edit_index_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="reserved name"):
            edit_entry(tmp_path, "index", description="x")

    def test_delete_index_rejected(self, tmp_path: Path):
        with pytest.raises(ValueError, match="reserved name"):
            delete_entry(tmp_path, "index")


class TestRebuildIndex:
    def test_sections_grouping_and_ordering(self, tmp_path: Path):
        create_entry(tmp_path, "cli-ref", "CLI reference", section="CLI")
        create_entry(tmp_path, "arch-overview", "Architecture overview", section="Architecture")
        create_entry(tmp_path, "misc-note", "A misc note")

        content = (tmp_path / "index.md").read_text()
        # Architecture before CLI (alphabetical), Uncategorized last
        arch_pos = content.index("## Architecture")
        cli_pos = content.index("## CLI")
        uncat_pos = content.index("## Uncategorized")
        assert arch_pos < cli_pos < uncat_pos

    def test_entries_without_section(self, tmp_path: Path):
        create_entry(tmp_path, "note-a", "Note A")
        create_entry(tmp_path, "note-b", "Note B")

        content = (tmp_path / "index.md").read_text()
        assert "## Uncategorized" in content
        assert "[note-a]" in content
        assert "[note-b]" in content

    def test_empty_wiki(self, tmp_path: Path):
        tmp_path.mkdir(exist_ok=True)
        rebuild_index(tmp_path)
        content = (tmp_path / "index.md").read_text()
        assert "# Wiki Index" in content
        assert "##" not in content.replace("# Wiki Index", "")

    def test_rebuild_after_delete(self, tmp_path: Path):
        create_entry(tmp_path, "keep", "Keep this")
        create_entry(tmp_path, "remove", "Remove this")
        delete_entry(tmp_path, "remove")

        content = (tmp_path / "index.md").read_text()
        assert "[keep]" in content
        assert "[remove]" not in content

    def test_index_not_listed_in_entries(self, tmp_path: Path):
        create_entry(tmp_path, "entry-a", "An entry")
        entries = list_entries(tmp_path)
        names = [e.name for e in entries]
        assert "index" not in names
