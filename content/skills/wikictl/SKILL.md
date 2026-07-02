# wikictl - AI Memory System

wikictl is a file-based memory layer for AI agents. It manages a `wiki/` directory of Markdown files with YAML frontmatter metadata. No RAG, no vector DB, no embeddings — just files on disk that agents can list, read, create, and edit through a CLI or MCP server.

## Core Concept: Metadata-First

The system uses metadata-first progressive disclosure to stay within context limits:

1. **Metadata level**: `wikictl list --json` or `wikictl search <query>` return only metadata (name, description, tags, timestamps) — no body content.
2. **Content level**: `wikictl read <name>` returns the full content of a specific entry.

Always start with `list` or `search` to understand what is available, then `read` only the entries you need. Never load all entries into context at once.

## When to Use Memory

| Intent | Skill to Load | Description |
|--------|---------------|-------------|
| Find, retrieve, recall information | `wikictl-read` | Query existing knowledge |
| Save, remember, persist new information | `wikictl-create` | Store a new memory entry |
| Update, correct, append to existing information | `wikictl-edit` | Modify an existing entry |
| Interact via MCP when the server is running | `wikictl-mcp` | Use MCP tools instead of CLI |

## CLI Reference

| Command | Description |
|---------|-------------|
| `wikictl list` | List all entries (metadata only) |
| `wikictl list --json` | List as JSON array |
| `wikictl list --tag <tag>` | Filter entries by tag |
| `wikictl search <query>` | Text search over name and description (metadata only) |
| `wikictl search <query> --tag <tag>` | Combined text + tag filter |
| `wikictl tags` | List unique tags across all entries |
| `wikictl read <name>` | Read full content of one entry |
| `wikictl create -n <name> -d "<desc>" -t "<tags>" -b "<body>"` | Create a new entry |
| `wikictl edit <name> [-d desc] [-t tags] [-b body] [-s section]` | Edit an existing entry |
| `wikictl move <name> <folder>` | Move entry to a sub-folder |
| `wikictl delete <name> --force` | Delete an entry (requires `--force`) |
| `wikictl schema` | Print the entry metadata contract |
| `wikictl index` | Rebuild the `wiki/index.md` file |

## Skill Routing Table

| User says... | Route to | Reason |
|--------------|----------|--------|
| "remember X" / "save this" / "note that we decided Y" | `wikictl-create` | New information to persist |
| "what do we know about Y" / "recall Z" / "check memory" | `wikictl-read` | Retrieving existing knowledge |
| "update the note about Z" / "add to the memory about V" | `wikictl-edit` | Modifying existing knowledge |
| "forget X" / "delete the entry about Y" | Direct CLI: `wikictl delete <name> --force` | Destruction — no sub-skill needed |
| "use MCP tools" / MCP client is available | `wikictl-mcp` | Prefer MCP over CLI when connected |

## Configuration

Wiki directory resolution (order of precedence):

1. `--wiki-dir <path>` CLI flag
2. `WIKICTL_DIR` environment variable
3. `./wiki/` relative to the current working directory (default)

## Gotchas

- **Always list before read.** Never guess entry names — run `wikictl list --json` or `wikictl search <query>` first, then `read` by exact name.
- **Don't read all entries.** Read only what is relevant. Use `search` to narrow down before reading.
- **Use `--json` for agent workflows.** Agents should always use `--json` for reliable parsing.
- **`delete` requires `--force`.** Mandatory to prevent accidental data loss.

## Examples

**User says "remember that we chose PostgreSQL over MySQL for the auth service"**
→ Load `wikictl-create`. The agent needs to persist a new decision.

**User says "what do we know about our deployment process?"**
→ Load `wikictl-read`. The agent needs to scan and retrieve existing entries.

**User says "update the architecture entry — we switched from monolith to microservices"**
→ Load `wikictl-edit`. The agent needs to modify an existing entry.
