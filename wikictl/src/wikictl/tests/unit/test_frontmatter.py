"""Unit tests for wikictl.frontmatter."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from wikictl.frontmatter import MalformedEntryError, parse_file, serialize_entry
from wikictl.models import WikiEntry


class TestSerializeAndParse:
    def test_roundtrip(self, tmp_path: Path):
        entry = WikiEntry(
            name="test-entry",
            description="A test entry",
            tags=["python", "test"],
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
            body="# Hello\n\nThis is content.",
        )

        path = tmp_path / "test-entry.md"
        path.write_text(serialize_entry(entry), encoding="utf-8")

        parsed = parse_file(path)
        assert parsed.name == entry.name
        assert parsed.description == entry.description
        assert parsed.tags == entry.tags
        assert parsed.body == entry.body

    def test_empty_body(self, tmp_path: Path):
        entry = WikiEntry(name="empty", description="no body")
        path = tmp_path / "empty.md"
        path.write_text(serialize_entry(entry), encoding="utf-8")

        parsed = parse_file(path)
        assert parsed.name == "empty"
        assert parsed.body == ""

    def test_special_chars_in_tags(self, tmp_path: Path):
        entry = WikiEntry(
            name="special",
            description="desc",
            tags=["c++", "c#", "node.js"],
        )
        path = tmp_path / "special.md"
        path.write_text(serialize_entry(entry), encoding="utf-8")

        parsed = parse_file(path)
        assert parsed.tags == ["c++", "c#", "node.js"]

    def test_serialize_format(self):
        entry = WikiEntry(
            name="test",
            description="desc",
            tags=["a"],
            created_at=datetime(2026, 5, 13, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, tzinfo=UTC),
            body="content",
        )
        text = serialize_entry(entry)
        assert text.startswith("---\n")
        assert "name: test" in text
        assert "content" in text

    def test_roundtrip_with_section(self, tmp_path: Path):
        entry = WikiEntry(
            name="sectioned",
            description="desc",
            section="Architecture",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        path = tmp_path / "sectioned.md"
        path.write_text(serialize_entry(entry), encoding="utf-8")

        parsed = parse_file(path)
        assert parsed.section == "Architecture"

    def test_roundtrip_without_section(self, tmp_path: Path):
        entry = WikiEntry(
            name="no-section",
            description="desc",
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 1, tzinfo=UTC),
        )
        path = tmp_path / "no-section.md"
        path.write_text(serialize_entry(entry), encoding="utf-8")

        parsed = parse_file(path)
        assert parsed.section is None

    def test_serialize_omits_section_when_none(self):
        entry = WikiEntry(
            name="test",
            description="desc",
            created_at=datetime(2026, 5, 13, tzinfo=UTC),
            updated_at=datetime(2026, 5, 13, tzinfo=UTC),
        )
        text = serialize_entry(entry)
        assert "section" not in text


class TestMalformedHeader:
    """A `---` block that is not YAML must fail loudly and namefully, not as a
    raw yaml.ScannerError from three libraries down."""

    def test_unquoted_colon_in_value(self, tmp_path: Path):
        # The real shape that broke `wikictl serve`: an email header block whose
        # value carries a second ':'.
        bad = tmp_path / "email.md"
        bad.write_text("---\nOggetto: Ciao\nNota: sito offline: dominio scaduto\n---\n\nbody\n")
        with pytest.raises(MalformedEntryError) as exc:
            parse_file(bad)
        assert str(bad) in str(exc.value)
        assert "line 3" in str(exc.value)
        assert exc.value.path == bad

    def test_is_a_value_error(self, tmp_path: Path):
        bad = tmp_path / "bad.md"
        bad.write_text("---\na: b: c\n---\n")
        assert isinstance(MalformedEntryError(bad, "x"), ValueError)

    def test_valid_yaml_without_name_still_raises_key_error(self, tmp_path: Path):
        # Parses fine, simply is not an entry: must stay a KeyError so callers
        # can tell "not an entry" apart from "broken file".
        not_entry = tmp_path / "plain.md"
        not_entry.write_text('---\ntitle: "just a doc"\n---\n\nbody\n')
        with pytest.raises(KeyError):
            parse_file(not_entry)
