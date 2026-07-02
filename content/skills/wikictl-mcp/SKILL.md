# wikictl-mcp: Wiki Access via MCP Protocol

Use this skill when the wikictl server is running and you have an MCP client configured. This provides the same capabilities as the CLI skills (wikictl-read, wikictl-create, wikictl-edit) but through MCP tools over the network.

## Connection

The MCP endpoint is available at:

```
http://<host>:<port>/mcp
```

Default: `http://127.0.0.1:9797/mcp` (local) or `http://localhost:9797/mcp` (Docker).

## Available Tools

### Read Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `list_entries` | `tag?` (string) | Array of entry metadata (name, description, tags, created_at, updated_at, section) |
| `read_entry` | `name` (string, required) | Entry metadata + body |
| `search_entries` | `q?` (string), `tag?` (string) | Array of matching entry metadata |
| `list_tags` | _(none)_ | Sorted array of all unique tag strings |

### Write Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `create_entry` | `name` (required), `description` (required), `tags?` (list), `body?` (string), `section?` (string) | Created entry metadata |
| `edit_entry` | `name` (required), `description?`, `tags?`, `body?`, `section?` | Updated entry metadata |
| `delete_entry` | `name` (required) | Confirmation object |

## Workflow: Progressive Disclosure

Same principle as CLI — always list before read:

1. **Call `list_entries`** to get metadata for all entries (no body content)
2. **Evaluate relevance** from names, descriptions, and tags
3. **Call `read_entry`** only for entries you actually need
4. **Correlate** information across multiple entries if needed

Never call `read_entry` for all entries. The progressive disclosure pattern exists to stay within context limits.

## Workflow: Creating Entries

1. **Call `list_entries`** to check for duplicates
2. If no existing entry on the topic, call `create_entry` with:
   - `name`: kebab-case, 2-4 words, topic-based
   - `description`: one sentence for progressive disclosure
   - `tags`: 2-4 consistent tags (see tag vocabulary below)
   - `body`: full markdown content
   - `section`: optional grouping for index

## Workflow: Editing Entries

1. **Call `list_entries`** to find the entry
2. **Call `read_entry`** to get current content (especially if appending to body)
3. **Call `edit_entry`** with only the fields you want to change
   - `tags` replaces the entire list (not a merge)
   - `body` replaces the entire body (not an append)
   - Omitted fields remain unchanged

## Tag Vocabulary

| Category | Example tags |
|----------|-------------|
| Domain | `architecture`, `security`, `performance`, `testing` |
| Technology | `python`, `react`, `terraform`, `docker`, `postgresql` |
| Type | `decision`, `preference`, `procedure`, `lesson`, `convention` |
| Scope | `frontend`, `backend`, `infra`, `ci-cd`, `data` |

## Gotchas

- **Always list before read.** Never guess entry names.
- **`edit_entry` replaces fields, not merges.** Read current body before appending.
- **`create_entry` fails on duplicates.** Check with `list_entries` first.
- **`delete_entry` is permanent.** No confirmation prompt via MCP.
- **Names must be kebab-case.** Lowercase letters, numbers, hyphens only.
- **No auth by default.** Anyone who can reach the server can CRUD the wiki.

## Examples

**Find information about deployment:**

```
1. list_entries(tag="devops")
2. Evaluate results — find "deploy-procedure" looks relevant
3. read_entry(name="deploy-procedure")
4. Present findings to user
```

**Remember a decision:**

```
1. list_entries()  — check no existing entry on this topic
2. create_entry(
     name="auth-db-choice",
     description="Decision to use PostgreSQL for auth service",
     tags=["decision", "architecture", "postgresql"],
     body="## Auth Database\n\nChose PostgreSQL for row-level security..."
   )
```

**Update an existing entry:**

```
1. list_entries()  — find "ci-runtime-requirements"
2. read_entry(name="ci-runtime-requirements")  — get current body
3. edit_entry(
     name="ci-runtime-requirements",
     body="<old body + new content appended>"
   )
```
