"""E2E tests for wikictl CLI."""

import json

from click.testing import CliRunner

from wikictl.cli import cli


def invoke(runner: CliRunner, args: list[str], **kwargs):
    return runner.invoke(cli, args, catch_exceptions=False, **kwargs)


class TestFullWorkflow:
    """5.1: create -> list -> read -> edit -> list -> delete -> list"""

    def test_full_lifecycle(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)

        # Create
        result = invoke(
            runner,
            [
                "--wiki-dir",
                wiki,
                "create",
                "-n",
                "my-note",
                "-d",
                "A note",
                "-t",
                "test,dev",
                "-b",
                "Hello world",
            ],
        )
        assert result.exit_code == 0
        assert "Created entry: my-note" in result.output

        # List
        result = invoke(runner, ["--wiki-dir", wiki, "list"])
        assert result.exit_code == 0
        assert "my-note" in result.output
        assert "A note" in result.output

        # Read
        result = invoke(runner, ["--wiki-dir", wiki, "read", "my-note"])
        assert result.exit_code == 0
        assert "Hello world" in result.output
        assert "name: my-note" in result.output

        # Edit
        result = invoke(
            runner,
            [
                "--wiki-dir",
                wiki,
                "edit",
                "my-note",
                "-d",
                "Updated note",
                "-b",
                "New content",
            ],
        )
        assert result.exit_code == 0
        assert "Updated entry: my-note" in result.output

        # List again (verify update)
        result = invoke(runner, ["--wiki-dir", wiki, "list"])
        assert "my-note" in result.output
        assert "Updated note" in result.output

        # Delete
        result = invoke(runner, ["--wiki-dir", wiki, "delete", "my-note", "--force"])
        assert result.exit_code == 0
        assert "Deleted entry: my-note" in result.output

        # List (empty)
        result = invoke(runner, ["--wiki-dir", wiki, "list"])
        assert "No entries found" in result.output


class TestWikiDirResolution:
    """5.2: --wiki-dir flag and WIKICTL_DIR env var resolution"""

    def test_wiki_dir_flag(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path / "custom")
        result = invoke(runner, ["--wiki-dir", wiki, "create", "-n", "test", "-d", "d"])
        assert result.exit_code == 0
        assert (tmp_path / "custom" / "test.md").exists()

    def test_env_var(self, tmp_path, monkeypatch):
        runner = CliRunner()
        wiki = str(tmp_path / "env-wiki")
        monkeypatch.setenv("WIKICTL_DIR", wiki)
        result = invoke(runner, ["create", "-n", "test", "-d", "d"])
        assert result.exit_code == 0
        assert (tmp_path / "env-wiki" / "test.md").exists()


class TestJsonOutput:
    """5.3: --json output format for list command"""

    def test_json_list(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "note-a", "-d", "A", "-t", "x"])
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "note-b", "-d", "B"])

        result = invoke(runner, ["--wiki-dir", wiki, "list", "--json"])
        assert result.exit_code == 0

        data = json.loads(result.output)
        assert len(data) == 2
        assert data[0]["name"] == "note-a"
        assert data[0]["tags"] == ["x"]
        assert "body" not in data[0]  # progressive disclosure

    def test_json_empty(self, tmp_path):
        runner = CliRunner()
        result = invoke(runner, ["--wiki-dir", str(tmp_path), "list", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == []


class TestSearchCommand:
    """search: text query over name + description, --tag, --json"""

    def _seed(self, runner, wiki):
        invoke(
            runner,
            ["--wiki-dir", wiki, "create", "-n", "deploy-aws", "-d", "How to deploy", "-t", "ops"],
        )
        invoke(
            runner,
            [
                "--wiki-dir",
                wiki,
                "create",
                "-n",
                "auth-flow",
                "-d",
                "Login design",
                "-t",
                "decision",
            ],
        )

    def test_search_by_text(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        self._seed(runner, wiki)
        result = invoke(runner, ["--wiki-dir", wiki, "search", "deploy"])
        assert result.exit_code == 0
        assert "deploy-aws" in result.output
        assert "auth-flow" not in result.output

    def test_search_text_and_tag(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        self._seed(runner, wiki)
        result = invoke(runner, ["--wiki-dir", wiki, "search", "login", "--tag", "decision"])
        assert result.exit_code == 0
        assert "auth-flow" in result.output
        assert "deploy-aws" not in result.output

    def test_search_json(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        self._seed(runner, wiki)
        result = invoke(runner, ["--wiki-dir", wiki, "search", "login", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "auth-flow"
        assert "body" not in data[0]

    def test_search_no_match(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        self._seed(runner, wiki)
        result = invoke(runner, ["--wiki-dir", wiki, "search", "zzz"])
        assert result.exit_code == 0
        assert "No matching entries" in result.output


class TestTagsCommand:
    """tags: sorted unique tags, --json"""

    def test_tags_sorted(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "a", "-d", "d", "-t", "zeta,alpha"])
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "b", "-d", "d", "-t", "alpha,mu"])
        result = invoke(runner, ["--wiki-dir", wiki, "tags"])
        assert result.exit_code == 0
        assert result.output.split() == ["alpha", "mu", "zeta"]

    def test_tags_json(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "a", "-d", "d", "-t", "x,y"])
        result = invoke(runner, ["--wiki-dir", wiki, "tags", "--json"])
        assert result.exit_code == 0
        assert json.loads(result.output) == ["x", "y"]


class TestMoveCommand:
    """move: relocate an entry into a sub-folder"""

    def test_move_into_subfolder(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "my-note", "-d", "A note"])
        result = invoke(runner, ["--wiki-dir", wiki, "move", "my-note", "study/sre"])
        assert result.exit_code == 0
        assert "Moved entry: my-note" in result.output
        assert (tmp_path / "study" / "sre" / "my-note.md").exists()
        assert not (tmp_path / "my-note.md").exists()

    def test_move_nonexistent(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "move", "nope", "study/sre"])
        assert result.exit_code != 0
        assert "not found" in result.output


class TestSchemaCommand:
    """schema: metadata contract, --json"""

    def test_schema_json(self, tmp_path):
        runner = CliRunner()
        result = invoke(runner, ["--wiki-dir", str(tmp_path), "schema", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        field_names = [f["name"] for f in data["fields"]]
        assert "name" in field_names
        assert "description" in field_names
        assert "usage" in data

    def test_schema_human(self, tmp_path):
        runner = CliRunner()
        result = invoke(runner, ["--wiki-dir", str(tmp_path), "schema"])
        assert result.exit_code == 0
        assert "name" in result.output
        assert "kebab-case" in result.output


class TestErrorCases:
    """5.4: duplicate create, read/edit/delete nonexistent, invalid name"""

    def test_duplicate_create(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "dup", "-d", "d"])
        result = runner.invoke(cli, ["--wiki-dir", wiki, "create", "-n", "dup", "-d", "d"])
        assert result.exit_code != 0
        assert "already exists" in result.output

    def test_read_nonexistent(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "read", "nope"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_edit_nonexistent(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "edit", "nope", "-d", "x"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_delete_nonexistent(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["--wiki-dir", str(tmp_path), "delete", "nope", "--force"])
        assert result.exit_code != 0
        assert "not found" in result.output

    def test_invalid_name(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--wiki-dir", str(tmp_path), "create", "-n", "Bad Name", "-d", "d"],
        )
        assert result.exit_code != 0
        assert "kebab-case" in result.output


class TestIndexCommand:
    """E2E tests for wikictl index command and --section flag."""

    def test_index_command(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "note-a", "-d", "A note"])

        result = invoke(runner, ["--wiki-dir", wiki, "index"])
        assert result.exit_code == 0
        assert "Index regenerated" in result.output
        assert (tmp_path / "index.md").exists()

    def test_section_flag_on_create(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(
            runner,
            [
                "--wiki-dir",
                wiki,
                "create",
                "-n",
                "arch-doc",
                "-d",
                "Architecture doc",
                "-s",
                "Architecture",
            ],
        )

        content = (tmp_path / "index.md").read_text()
        assert "## Architecture" in content
        assert "[arch-doc]" in content

    def test_section_flag_on_edit(self, tmp_path):
        runner = CliRunner()
        wiki = str(tmp_path)
        invoke(runner, ["--wiki-dir", wiki, "create", "-n", "my-doc", "-d", "A doc"])
        invoke(runner, ["--wiki-dir", wiki, "edit", "my-doc", "-s", "CLI"])

        content = (tmp_path / "index.md").read_text()
        assert "## CLI" in content

    def test_create_index_rejected(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--wiki-dir", str(tmp_path), "create", "-n", "index", "-d", "d"],
        )
        assert result.exit_code != 0
        assert "reserved name" in result.output

    def test_delete_index_rejected(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--wiki-dir", str(tmp_path), "delete", "index", "--force"],
        )
        assert result.exit_code != 0
        assert "reserved name" in result.output
