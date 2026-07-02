# wikictl-read: Retrieve and Correlate Memories

## Workflow

Follow these steps in order. Do not skip steps.

### Step 1: Scan Available Memories

Always start with a metadata-only scan:

```bash
wikictl list --json
```

Sample output:

```json
[
  {
    "name": "auth-service-db-choice",
    "description": "Decision to use PostgreSQL for the auth service",
    "tags": ["decision", "architecture", "postgresql"],
    "created_at": "2025-03-15T10:00:00Z",
    "updated_at": "2025-03-15T10:00:00Z"
  },
  {
    "name": "deploy-procedure",
    "description": "Step-by-step deployment process for production",
    "tags": ["procedure", "devops", "production"],
    "created_at": "2025-03-10T08:30:00Z",
    "updated_at": "2025-04-01T14:00:00Z"
  }
]
```

This returns an array of objects with `name`, `description`, `tags`, `created_at`, `updated_at` -- no body content. This is lightweight and gives you the full index.

### Step 2: Evaluate Relevance

From the metadata, determine which entries are relevant to the current task:

- **Name**: Does the entry name relate to the topic?
- **Description**: Does the description suggest useful content?
- **Tags**: Do the tags overlap with the current domain/topic?

Select only the entries that are likely relevant. Do NOT read all entries.

### Step 3: Fetch Full Content

For each relevant entry:

```bash
wikictl read <name>
```

Example:

```bash
wikictl read auth-service-db-choice
```

This returns the full Markdown content including frontmatter.

### Step 4: Correlate Information

When multiple entries are relevant:

- Look for connections between entries based on shared tags.
- Note when entries reference similar topics from different angles.
- Identify contradictions between entries -- flag these to the user.
- Synthesize a coherent picture from multiple sources.

## Tag Filtering

If you know the domain area, use tag filtering to narrow the scan before reading:

```bash
wikictl list --json --tag architecture
wikictl list --json --tag decisions
wikictl list --json --tag python
```

Tag filtering reduces the metadata set before you even start evaluating relevance. Use it when the wiki has many entries.

## Multi-Entry Correlation

When a question spans multiple topics (e.g., "how does our auth setup relate to our deployment process?"):

1. `wikictl list --json` -- scan all metadata.
2. Identify entries from both domains (e.g., `auth-service-db-choice` and `deploy-procedure`).
3. Read both entries.
4. Synthesize the answer by connecting information across entries.
5. If entries contradict each other, present both perspectives and ask the user which is current.

## Gotchas

- **Don't read all entries.** Progressive disclosure exists for a reason. Reading every entry wastes context window. Evaluate metadata first, then read selectively.
- **Always start with `list --json`.** Never guess entry names. Names may not match your expectations. The list output is the source of truth.
- **Never guess entry names.** If you assume an entry is called `db-config` but it is actually `database-configuration`, the read will fail. Always list first.
- **If no entries exist, say so.** Do not fabricate memories. If the wiki is empty or has no relevant entries, tell the user clearly.
- **Conflicting information.** When memory conflicts with the user's current statement, present both and ask for clarification -- do not silently prefer one over the other.

## Examples

**User: "What do we know about our testing strategy?"**

```bash
# Step 1: scan
wikictl list --json
# Step 2: evaluate -- find entries tagged "testing" or with test-related names
# Step 3: read relevant entries
wikictl read testing-strategy
wikictl read e2e-test-conventions
# Step 4: synthesize and present
```

**User: "Do we have anything about Docker configuration?"**

```bash
# Step 1: narrow by tag
wikictl list --json --tag docker
# Step 2: if results found, read them; if empty, report "no entries found for docker"
wikictl read docker-compose-setup
```

**User: "What decisions have we made so far?"**

```bash
# Filter by the "decision" tag
wikictl list --json --tag decision
# Read each decision entry to present a summary
wikictl read auth-service-db-choice
wikictl read frontend-framework-selection
```
