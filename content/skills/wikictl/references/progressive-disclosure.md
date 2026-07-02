# Progressive Disclosure in wikictl

## What is Progressive Disclosure?

Progressive disclosure is an interaction design pattern that sequences information across multiple levels of detail. Users start with a high-level overview and drill into specifics only when needed.

## How wikictl Uses Progressive Disclosure

wikictl applies this pattern to manage context window constraints in AI agents:

### Level 1: Metadata Scan

```bash
wikictl list --json
```

Returns an array of lightweight objects containing only metadata:

```json
[
  {
    "name": "api-auth-decision",
    "description": "Chose JWT over session cookies for API authentication",
    "tags": ["architecture", "security", "decision"],
    "created_at": "2026-01-15T10:30:00+00:00",
    "updated_at": "2026-01-15T10:30:00+00:00"
  }
]
```

No body content is included. This allows the agent to scan the entire wiki index without consuming significant context.

### Level 2: Full Content Retrieval

```bash
wikictl read api-auth-decision
```

Returns the complete entry with YAML frontmatter and full markdown body. This is only done for entries identified as relevant in Level 1.

## Why This Matters for AI Agents

AI agents have finite context windows. A wiki with 50 entries might contain 50,000 tokens of body content. Loading all of it wastes context and degrades response quality.

With progressive disclosure:
1. The metadata scan might use ~2,000 tokens for 50 entries
2. The agent reads 2-3 relevant entries, using ~2,000 more tokens
3. Total: ~4,000 tokens instead of ~50,000

## Design Principles

- **Metadata must be informative**: The `description` field is the agent's primary signal for relevance. Write descriptions that clearly indicate what the entry contains.
- **Tags enable filtering**: Use `wikictl list --json --tag <tag>` to narrow the scan before evaluating metadata.
- **Minimize reads**: The agent should read the minimum number of entries needed for the current task.
- **Never guess names**: Always start with `list` to discover available entries. Entry names should not be assumed.
