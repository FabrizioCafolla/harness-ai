# wikictl

A file-based memory layer for AI agents. Manages a personal wiki as Markdown files with YAML frontmatter, browsable through a render-only web UI and queryable by agents over MCP. No cloud APIs, no API keys — the data is just Markdown on disk.

wikictl is provisioned into a workspace by the [harness-ai](https://github.com/FabrizioCafolla/harness-ai) devcontainer feature (`install.wikictl: true` in `.harness-ai/config.yaml`), which installs the CLI, registers the MCP server, and deploys the `wikictl-*` skills. It also works as a standalone install.

## Install

Standalone, as an isolated CLI:

```bash
uv tool install /path/to/wikictl              # CLI + serve extra
# or, editable for development:
uv pip install -e ".[dev,serve]"
```

`WIKICTL_DIR` selects the wiki root (defaults to `./wiki`).

## CLI

```bash
# Create / read / list
wikictl create -n project-setup -d "How the project was bootstrapped" -t "setup,architecture" -s Architecture
wikictl read project-setup
wikictl list                         # all entries (metadata only)
wikictl list --json
wikictl list --tag architecture

# Search and tags
wikictl search "bootstrap"           # text query over name + description
wikictl search "bootstrap" --tag setup
wikictl tags                         # sorted unique tags
wikictl tags --json

# Edit / move / delete
wikictl edit project-setup -d "Updated description" -s Setup
wikictl move project-setup study/ai-k8s
wikictl delete project-setup --force

# Metadata contract and index
wikictl schema                       # entry metadata contract (fields, rules)
wikictl schema --json
wikictl index                        # rebuild the index
```

## MCP server

`wikictl serve` exposes both the render-only web UI and an MCP server at `/mcp/`.

```bash
wikictl serve                        # default 127.0.0.1:9797
wikictl serve --port 3000 --host 0.0.0.0
```

| Tool                                                          | Purpose                                   |
| ------------------------------------------------------------ | ----------------------------------------- |
| `list_entries` / `search_entries` / `list_tags`              | discover entries by tag or keyword (metadata only) |
| `read_entry`                                                 | full content of one entry                 |
| `create_entry` / `edit_entry` / `move_entry` / `delete_entry` | manage entries                            |
| `get_schema`                                                 | the entry metadata contract (works on an empty wiki) |

**Metadata-first protocol.** Only `read_entry` returns an entry body. Clients scan with `list_entries`/`search_entries` (metadata only), evaluate relevance from `description` and `tags`, then `read_entry` only the entries they actually need. The protocol is encoded in the MCP server's `instructions` and in each tool's docstring, so clients without a loaded skill follow it too. `get_schema` returns the field names, types, required/optional flags, and validation rules (kebab-case `name`, `description` as the relevance signal) — enough to learn the contract before writing.

## Web UI

The web server renders the wiki as read-only HTML and exposes a JSON API. It does not write.

```bash
# HTML
curl http://127.0.0.1:9797/                       # full wiki tree
curl http://127.0.0.1:9797/wiki/project-setup     # single entry page

# JSON API
curl http://127.0.0.1:9797/api/entries                  # list (metadata)
curl http://127.0.0.1:9797/api/entries/project-setup    # full entry + rendered HTML
curl http://127.0.0.1:9797/api/tags                     # unique tags
curl http://127.0.0.1:9797/api/search?tag=architecture  # filter by tag
```

## Entry format

Each entry is a Markdown file with YAML frontmatter:

```markdown
---
name: project-setup
description: How the project was bootstrapped
tags: [setup, architecture]
section: Architecture
---

Body content in Markdown.
```

`name` is kebab-case and unique; `description` is the relevance signal agents read before deciding to load the body.
