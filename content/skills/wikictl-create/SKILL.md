# wikictl-create: Store New Memories

## When to Create a Memory

Create a memory entry when you encounter:

- **Decisions**: Architecture choices, technology selections, design patterns adopted
- **Preferences**: User's coding style, tool preferences, naming conventions
- **Context**: Project-specific knowledge, domain terminology, team conventions
- **Lessons**: Bugs found and their root causes, solutions that worked, approaches that failed
- **Procedures**: Environment setup details, deployment steps, access patterns

Do NOT create entries for:

- Ephemeral information (temporary file paths, session-specific debug data)
- Information already documented in the codebase (README, CONTRIBUTING, inline docs)
- Trivially retrievable information (standard library docs, common patterns)
- Duplicate content -- if an entry on the same topic exists, use `wikictl-edit` instead

## Workflow

### Step 1: Check for Duplicates

Before creating, always scan existing entries:

```bash
wikictl list --json
```

Review the names, descriptions, and tags. If a related entry already exists, load the `wikictl-edit` skill and update that entry instead of creating a new one.

### Step 2: Choose a Good Name

Rules:

- **kebab-case only**: `project-architecture`, `deploy-procedure`, `user-preferences`
- **Be specific**: `react-state-management` not `frontend-notes`
- **Use the topic as the name**: not a date, session ID, or sequence number
- **Keep it short**: 2-4 words is ideal

### Step 3: Write Descriptive Metadata

- **Description**: One sentence summarizing what this entry contains. This is the primary text the agent sees during progressive disclosure, so make it precise and informative.
- **Tags**: Choose tags from a consistent vocabulary to help future retrieval.

### Tag Vocabulary

Use these categories to keep tags consistent across entries:

| Category | Example tags |
|----------|-------------|
| Domain | `architecture`, `security`, `performance`, `testing`, `observability` |
| Technology | `python`, `react`, `terraform`, `docker`, `postgresql` |
| Type | `decision`, `preference`, `procedure`, `lesson`, `convention` |
| Scope | `frontend`, `backend`, `infra`, `ci-cd`, `data` |

Use 2-4 tags per entry. Avoid inventing one-off tags that will never be reused.

### Step 4: Create the Entry

```bash
wikictl create \
  --name "descriptive-kebab-name" \
  --description "One sentence summary for progressive disclosure" \
  --tags "domain,tech,type" \
  --body "Full markdown content with all the details worth remembering"
```

## Body Content Guidelines

- Write in Markdown.
- Be concise but complete -- include the reasoning, not just the conclusion.
- For **decisions**: state what was decided, why, and what alternatives were considered.
- For **procedures**: include step-by-step instructions and prerequisites.
- For **preferences**: include the preference and any known exceptions.
- For **lessons**: include the problem, root cause, solution, and how to avoid recurrence.

## Gotchas

- **kebab-case names only.** Spaces, underscores, and camelCase will cause issues. Always use `kebab-case`.
- **Check for duplicates first.** If you skip the `list --json` step and create a duplicate, you fragment knowledge across entries. Always check.
- **Meaningful tags matter.** Tags like `misc`, `stuff`, or `notes` are useless for retrieval. Pick tags that a future query would actually filter on.
- **Don't over-create.** Not everything is worth a memory entry. If the information is unlikely to be needed in a future session, skip it.
- **Description is critical.** The description is the only thing visible during `list`. A vague description like "some notes" makes the entry invisible to future progressive disclosure scans.

## Examples

**User says "remember that we chose PostgreSQL over MySQL for the auth service because of row-level security"**

```bash
wikictl list --json  # check for existing DB-related entries
wikictl create \
  --name "auth-service-db-choice" \
  --description "Decision to use PostgreSQL over MySQL for the auth service" \
  --tags "decision,architecture,postgresql" \
  --body "## Auth Service Database\n\nChose PostgreSQL over MySQL.\n\n**Reason**: PostgreSQL supports row-level security (RLS) natively, which is required for the multi-tenant auth model.\n\n**Alternatives considered**: MySQL (no native RLS), CockroachDB (operational complexity too high for team size)."
```

**User says "note that our CI pipeline requires Node 20 and Python 3.12"**

```bash
wikictl list --json  # check for existing CI entries
wikictl create \
  --name "ci-runtime-requirements" \
  --description "Required runtime versions for the CI pipeline" \
  --tags "convention,ci-cd" \
  --body "## CI Runtime Requirements\n\n- Node.js: v20 (LTS)\n- Python: 3.12\n\nThese are pinned in the CI config and must match local dev environments."
```

**User says "save that we prefer composition over inheritance in this project"**

```bash
wikictl list --json  # check for existing coding-convention entries
wikictl create \
  --name "composition-over-inheritance" \
  --description "Project convention preferring composition over class inheritance" \
  --tags "preference,convention,architecture" \
  --body "## Composition Over Inheritance\n\nThis project prefers composition over inheritance for code reuse. Use dependency injection and interface composition instead of deep class hierarchies.\n\n**Exception**: When extending framework-provided base classes (e.g., Django views), inheritance is acceptable."
```
