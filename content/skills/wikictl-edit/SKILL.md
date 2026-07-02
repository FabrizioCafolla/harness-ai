# wikictl-edit: Update Existing Memories

## When to Edit vs Create

- **Edit** when new information supplements, corrects, or replaces content in an existing entry.
- **Create** (load `wikictl-create`) when the information is about a genuinely new topic with no existing entry.

Rule of thumb: if `wikictl list --json` shows an entry on the same topic, edit it. Do not create a second entry.

## Partial Update Semantics

The `edit` command uses partial updates. Only the fields you specify are changed:

| Flag | Behavior |
|------|----------|
| `--description` | Replaces the description |
| `--tags` | **Replaces the entire tag list** (not a merge) |
| `--body` | **Replaces the entire body** (not an append) |
| _(omitted)_ | Field remains unchanged |

The `name` and `created_at` fields are never changed. The `updated_at` timestamp is set automatically on every edit.

## Workflow

### Step 1: Find the Entry

Scan existing entries:

```bash
wikictl list --json
```

Identify the entry by name and description.

### Step 2: Read Before Editing

If you need to append to the body (rather than replace it), you must read the current content first:

```bash
wikictl read <name>
```

This gives you the existing body so you can merge the old and new content.

### Step 3: Apply the Edit

```bash
# Update description only
wikictl edit <name> --description "Updated summary"

# Update tags only (replaces entire tag list)
wikictl edit <name> --tags "new,tag,list"

# Update body (replaces entire body)
wikictl edit <name> --body "Completely new body content"

# Update multiple fields at once
wikictl edit <name> --description "New desc" --tags "a,b" --body "New content"
```

## Gotchas

- **Check existing entries before creating duplicates.** Always `list --json` first. If the topic already has an entry, edit it. Duplicates fragment knowledge and confuse future retrieval.
- **`--body` replaces, it does not append.** If you want to add a paragraph to an existing entry, you must `read` the current body first, combine old + new content, then pass the full result to `--body`.
- **`--tags` replaces the entire tag list.** If the entry has tags `a,b,c` and you run `--tags "d,e"`, the result is `d,e` -- not `a,b,c,d,e`. Include all desired tags in the flag.
- **Read before append.** Never assume you know the current body content. Always `wikictl read <name>` before constructing an appended body.
- **Keep the description current.** The description is the first thing agents see during progressive disclosure. If the scope of the entry changed, update the description to match.
- **Do not remove information unless it is wrong.** Prefer appending corrections (with context on what changed) over silently deleting content.

## Examples

**Correcting a decision entry:**

```bash
# Step 1: find and read
wikictl list --json
wikictl read auth-service-db-choice

# Step 2: edit with correction context
wikictl edit auth-service-db-choice \
  --body "## Auth Service Database\n\nChose PostgreSQL over MySQL.\n\n**Reason**: Row-level security for multi-tenancy.\n\n**Update (2025-04-15)**: Switched from PostgreSQL 15 to PostgreSQL 16 for improved JSONB performance. Original RLS rationale still applies."
```

**Appending new information to a procedure:**

```bash
# Step 1: read current content
wikictl read deploy-procedure
# Existing body: "## Deploy\n\n1. Run tests\n2. Build image\n3. Push to registry\n4. Apply k8s manifests"

# Step 2: edit with appended content
wikictl edit deploy-procedure \
  --body "## Deploy\n\n1. Run tests\n2. Build image\n3. Push to registry\n4. Apply k8s manifests\n5. Verify health checks (added 2025-04-20)\n\n## Rollback\n\nIf health checks fail, revert to the previous image tag with:\n\`\`\`bash\nkubectl rollout undo deployment/app\n\`\`\`"
```

**Updating tags after scope change:**

```bash
# Entry originally tagged "backend,python" but now covers both backend and frontend
wikictl edit api-conventions \
  --tags "backend,frontend,python,typescript,convention" \
  --description "API and data contract conventions covering both backend and frontend"
```

**Updating only the description:**

```bash
wikictl edit ci-runtime-requirements \
  --description "Required runtime versions for CI: Node 22 and Python 3.13"
```
