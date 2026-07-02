"""Unit tests for wikictl.models."""

import pytest

from wikictl.models import WikiEntry, metadata_schema, validate_name


class TestValidateName:
    def test_valid_kebab_case(self):
        assert validate_name("my-note") == "my-note"
        assert validate_name("a") == "a"
        assert validate_name("note-123") == "note-123"
        assert validate_name("my-long-name") == "my-long-name"

    def test_invalid_names(self):
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("My Note")
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("UPPER")
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("has_underscore")
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("")
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("-leading")
        with pytest.raises(ValueError, match="kebab-case"):
            validate_name("trailing-")


class TestWikiEntry:
    def test_creation_with_defaults(self):
        entry = WikiEntry(name="test", description="A test")
        assert entry.name == "test"
        assert entry.description == "A test"
        assert entry.tags == []
        assert entry.body == ""
        assert entry.created_at is not None
        assert entry.updated_at is not None

    def test_creation_with_all_fields(self):
        entry = WikiEntry(
            name="my-note",
            description="desc",
            tags=["a", "b"],
            body="content",
        )
        assert entry.tags == ["a", "b"]
        assert entry.body == "content"

    def test_invalid_name_raises(self):
        with pytest.raises(ValueError):
            WikiEntry(name="Bad Name", description="d")

    def test_to_metadata_dict(self):
        entry = WikiEntry(name="test", description="desc", tags=["x"])
        meta = entry.to_metadata_dict()
        assert meta["name"] == "test"
        assert meta["description"] == "desc"
        assert meta["tags"] == ["x"]
        assert "body" not in meta
        assert "created_at" in meta
        assert "updated_at" in meta
        assert meta["section"] is None

    def test_section_field_default(self):
        entry = WikiEntry(name="test", description="desc")
        assert entry.section is None

    def test_section_field_set(self):
        entry = WikiEntry(name="test", description="desc", section="Architecture")
        assert entry.section == "Architecture"

    def test_to_metadata_dict_with_section(self):
        entry = WikiEntry(name="test", description="desc", section="CLI")
        meta = entry.to_metadata_dict()
        assert meta["section"] == "CLI"


class TestMetadataSchema:
    def test_contract_has_all_fields(self):
        contract = metadata_schema()
        names = [f["name"] for f in contract["fields"]]
        assert names == [
            "name",
            "description",
            "tags",
            "section",
            "body",
            "created_at",
            "updated_at",
        ]

    def test_each_field_has_contract_keys(self):
        for f in metadata_schema()["fields"]:
            assert set(f) == {"name", "type", "required", "managed", "rules"}

    def test_required_and_managed_flags(self):
        by_name = {f["name"]: f for f in metadata_schema()["fields"]}
        assert by_name["name"]["required"] is True
        assert by_name["description"]["required"] is True
        assert by_name["tags"]["required"] is False
        assert by_name["created_at"]["managed"] == "auto"
        assert by_name["updated_at"]["managed"] == "auto"
        assert by_name["name"]["managed"] == "write"

    def test_name_validation_rule_mentions_kebab(self):
        by_name = {f["name"]: f for f in metadata_schema()["fields"]}
        assert "kebab-case" in by_name["name"]["rules"]

    def test_usage_describes_metadata_first(self):
        usage = metadata_schema()["usage"].lower()
        assert "description" in usage
        assert "tags" in usage
        assert "body" in usage
