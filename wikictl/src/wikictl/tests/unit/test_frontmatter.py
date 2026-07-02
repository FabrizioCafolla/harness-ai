"""Unit tests for wikictl.frontmatter."""

from datetime import UTC, datetime
from pathlib import Path

from wikictl.frontmatter import parse_file, serialize_entry
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
