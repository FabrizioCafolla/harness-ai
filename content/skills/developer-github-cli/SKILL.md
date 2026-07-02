# GitHub CLI (gh)

Best practices for GitHub CLI (`gh`) — focused on issues, pull requests, and day-to-day repository operations from the command line.

For the full command reference, read `references/commands.md` in this skill directory.

## Critical Guardrail: User Approval Before Creation

**Any command that creates, modifies, or deletes a resource on GitHub requires explicit user approval before execution.** This includes but is not limited to:

- `gh issue create`
- `gh pr create`
- `gh pr merge`
- `gh pr close`
- `gh issue close`
- `gh release create`
- `gh repo create` / `gh repo delete`
- `gh label create` / `gh label delete`
- `gh pr review --approve` / `--request-changes`
- `gh api --method POST/PUT/PATCH/DELETE`

The reason is simple: these operations publish to a shared, public system. A wrong issue title, a PR against the wrong branch, or a premature merge cannot always be cleanly undone. The cost of asking is zero; the cost of a mistake can be significant.

### Approval workflow

1. **Prepare the full command** with all flags and body content
2. **Present it to the user** in a code block, clearly showing what will be created/changed
3. **Wait for explicit confirmation** — do not interpret silence or vague responses as approval
4. **Execute only after the user says yes** (or equivalent: "go ahead", "do it", "ok", "looks good")

If the user says "create an issue for X", that is the _request to draft_, not the approval to execute. Always show the draft first.

### Example approval flow

```
User: "Create an issue for the broken login page"

Agent response:
Here's the issue I'll create:

  gh issue create \
    --title "Bug: Login page broken" \
    --body "## Description\n\nThe login page is not rendering correctly.\n\n## Steps to reproduce\n\n1. Navigate to /login\n2. ...\n\n## Expected behavior\n\n..." \
    --label bug

Want me to go ahead?
```

## Issue Creation Workflow

### Step 1: Detect issue templates

Before composing an issue, check whether the repository has issue templates:

```bash
# Check for issue templates
ls .github/ISSUE_TEMPLATE/ 2>/dev/null
# Also check for the legacy single-file template
ls .github/ISSUE_TEMPLATE.md 2>/dev/null
```

Issue templates can be:

- **YAML forms** (`.github/ISSUE_TEMPLATE/*.yml`) — structured forms with fields; extract the field names and use them to build the `--body`
- **Markdown templates** (`.github/ISSUE_TEMPLATE/*.md`) — have YAML frontmatter (`name`, `about`, `labels`, `assignees`) followed by a markdown body with sections to fill in
- **Legacy single file** (`.github/ISSUE_TEMPLATE.md`) — a single markdown template

### Step 2: Compose the issue

**When templates exist:** Read the template that best matches the user's intent. Extract the structure (headings, sections, required fields) and fill in the content from the user's description. Preserve the template structure — do not skip sections, mark them as "N/A" if not applicable.

```bash
# If using a specific template (YAML form or markdown)
gh issue create --template "bug_report.yml" \
  --title "Bug: ..." \
  --body "filled-in content following template structure"
```

**When no templates exist:** Compose well-structured markdown with appropriate sections:

```bash
gh issue create \
  --title "Clear, descriptive title" \
  --body "## Description

Concise problem or feature statement.

## Context

Why this matters, what triggered it.

## Acceptance criteria

- [ ] Criterion 1
- [ ] Criterion 2"
```

### Step 3: Add metadata

Apply labels, assignees, milestones, and projects when the user specifies them or when they can be clearly inferred:

```bash
gh issue create \
  --title "..." \
  --body "..." \
  --label "bug,high-priority" \
  --assignee "@me" \
  --milestone "v2.0"
```

Use `gh label list` to verify labels exist before adding them. Do not invent labels.

### Step 4: Present and wait for approval

Show the complete command to the user. Wait for explicit approval. Then execute.

## Pull Request Creation Workflow

### Step 1: Detect PR templates

```bash
# Check for PR template (multiple possible locations)
ls .github/PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls .github/PULL_REQUEST_TEMPLATE/ 2>/dev/null
ls docs/PULL_REQUEST_TEMPLATE.md 2>/dev/null
ls PULL_REQUEST_TEMPLATE.md 2>/dev/null
```

### Step 2: Compose the PR

**When a template exists:** Read it, preserve its structure, and fill in each section based on the actual changes. If the template has checklists, check off items that are done and leave unchecked items as-is.

**When no template exists:** Use a clear structure:

```bash
gh pr create \
  --title "type(scope): concise description" \
  --body "## What

Summary of the change.

## Why

Motivation and context.

## How

Implementation approach.

## Testing

How this was tested.

## Checklist

- [ ] Tests pass
- [ ] Documentation updated" \
  --base main
```

### Step 3: Set PR metadata

```bash
gh pr create \
  --title "..." \
  --body "..." \
  --base main \
  --label "enhancement" \
  --reviewer "teammate1,teammate2" \
  --assignee "@me" \
  --draft  # use when work is not ready for review
```

Key flags to consider:

- `--draft` — use when the PR is work-in-progress
- `--base` — always specify explicitly to avoid mistakes; confirm with the user if unsure
- `--reviewer` — add only when the user requests it or the project convention is clear
- `--milestone` — add when applicable

### Step 4: Present and wait for approval

Show the complete command. Wait for explicit confirmation. Execute only after approval.

## Read Operations (No Approval Needed)

These commands are safe to run without asking — they only read data:

```bash
# Issues
gh issue list                         # open issues
gh issue list --state all             # all issues
gh issue list --label bug             # filter by label
gh issue list --assignee @me          # my issues
gh issue view 123                     # view issue details
gh issue view 123 --comments          # with comments
gh issue status                       # summary of assigned/mentioned/recent

# Pull requests
gh pr list                            # open PRs
gh pr list --author @me               # my PRs
gh pr status                          # summary
gh pr view 123                        # view PR details
gh pr view 123 --comments             # with comments
gh pr checks 123                      # CI status
gh pr diff 123                        # view diff

# Search
gh search issues "label:bug state:open"
gh search prs "is:open review:required"

# Repository
gh repo view                          # repo details
gh repo view --json name,description

# Workflow runs
gh run list                           # recent runs
gh run view 123456                    # run details

# Labels
gh label list                         # available labels
```

## Other Mutation Operations

The following also require user approval — present the command first, then wait:

### Merging PRs

```bash
# Always show the merge strategy to the user
gh pr merge 123 --squash --delete-branch
# Options: --merge, --squash, --rebase
```

Confirm the merge strategy with the user. Different projects have different conventions.

### Closing issues/PRs

```bash
gh issue close 123 --comment "Resolved in #456"
gh pr close 123 --comment "Superseded by #789"
```

### Reviewing PRs

```bash
gh pr review 123 --approve --body "LGTM"
gh pr review 123 --request-changes --body "See inline comments"
```

### Releases

```bash
gh release create v1.0.0 \
  --title "Version 1.0.0" \
  --notes-file CHANGELOG.md \
  --target main
```

## JSON Output and Scripting

Use `--json` and `--jq` for structured data extraction:

```bash
# Get specific fields
gh issue list --json number,title,labels --jq '.[] | [.number, .title] | @tsv'

# Filter results
gh pr list --json number,title,headRefName --jq '.[] | select(.headRefName | startswith("fix/"))'

# Count open issues by label
gh issue list --json labels --jq '[.[].labels[].name] | group_by(.) | map({label: .[0], count: length})'
```

## API Requests

For operations not covered by built-in commands, use `gh api`:

```bash
# GET request (safe, no approval needed)
gh api /repos/{owner}/{repo}/topics

# POST/PUT/PATCH/DELETE (requires user approval)
gh api --method POST /repos/{owner}/{repo}/issues \
  -f title="Issue title" \
  -f body="Issue body"
```

**Important:** `gh api -f` does not support object values. Use multiple `-f` flags with string values instead.

## Best Practices

1. **Always verify before mutating** — use list/view/status commands to understand the current state before proposing changes
2. **Use `--repo owner/repo`** when operating outside the current repository's directory
3. **Prefer `--json` over text parsing** — structured output is more reliable than parsing human-readable tables
4. **Check template existence** before every issue/PR creation — templates change over time
5. **Set `gh repo set-default`** in multi-remote setups to avoid confusion about which remote gets the issue/PR
6. **Use `--draft` for PRs** that need early feedback but aren't ready for merge
7. **Quote body content carefully** — for multi-line bodies, prefer `--body-file` with a temp file over inline strings with escaped newlines

## References

- Official manual: https://cli.github.com/manual/
- GitHub CLI docs: https://docs.github.com/en/github-cli
