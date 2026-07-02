# GitHub CLI Command Reference

Comprehensive command reference for GitHub CLI (`gh`). Use this as a lookup when you need the exact syntax for a specific command.

## Table of Contents

- [Authentication](#authentication)
- [Repositories](#repositories)
- [Issues](#issues)
- [Pull Requests](#pull-requests)
- [GitHub Actions](#github-actions)
- [Projects](#projects)
- [Releases](#releases)
- [Gists](#gists)
- [Codespaces](#codespaces)
- [Search](#search)
- [Labels](#labels)
- [API Requests](#api-requests)
- [Configuration](#configuration)
- [Extensions and Aliases](#extensions-and-aliases)
- [Global Flags](#global-flags)

---

## Authentication

```bash
# Interactive login
gh auth login
gh auth login --web
gh auth login --hostname enterprise.internal
gh auth login --with-token < token.txt
gh auth login --git-protocol ssh

# Status
gh auth status
gh auth status --show-token

# Switch account
gh auth switch --hostname github.com --user username

# Token
gh auth token

# Refresh scopes
gh auth refresh --scopes write:org,read:public_key
gh auth refresh --remove-scopes delete_repo

# Git credential helper
gh auth setup-git

# Logout
gh auth logout --hostname github.com --user username
```

## Repositories

### Create

```bash
gh repo create my-repo --public --description "Description" --clone
gh repo create my-repo --private
gh repo create org/my-repo --license mit --gitignore python
gh repo create my-repo --source=. --remote=upstream
```

### Clone

```bash
gh repo clone owner/repo
gh repo clone owner/repo my-directory
```

### List

```bash
gh repo list
gh repo list owner --limit 50 --public --source
gh repo list --json name,visibility,owner
```

### View

```bash
gh repo view
gh repo view owner/repo
gh repo view --json name,description,defaultBranchRef
gh repo view --web
```

### Edit

```bash
gh repo edit --description "New description"
gh repo edit --visibility private
gh repo edit --default-branch main
gh repo edit --enable-issues --disable-wiki
gh repo rename new-name
```

### Fork and Sync

```bash
gh repo fork owner/repo --clone --remote-name upstream
gh repo sync
gh repo sync --branch feature --force
```

### Other

```bash
gh repo set-default owner/repo
gh repo archive / gh repo unarchive
gh repo delete owner/repo --yes
gh repo deploy-key list / add / delete
```

## Issues

### Create

```bash
gh issue create
gh issue create --title "Title" --body "Body"
gh issue create --title "Title" --body-file issue.md
gh issue create --template "bug_report.yml"
gh issue create --label bug,high-priority --assignee user1,user2
gh issue create --milestone "v1.0"
gh issue create --repo owner/repo --title "Title"
gh issue create --web
```

### List

```bash
gh issue list
gh issue list --state all / --state closed
gh issue list --assignee @me
gh issue list --labels bug,enhancement
gh issue list --milestone "v1.0"
gh issue list --search "is:open label:bug"
gh issue list --limit 50 --sort created --order desc
gh issue list --json number,title,state,author
```

### View

```bash
gh issue view 123
gh issue view 123 --comments
gh issue view 123 --web
gh issue view 123 --json title,body,state,labels,comments
```

### Edit

```bash
gh issue edit 123 --title "New title" --body "New body"
gh issue edit 123 --add-label bug --remove-label stale
gh issue edit 123 --add-assignee user1 --remove-assignee user2
gh issue edit 123 --milestone "v1.0"
```

### Close / Reopen

```bash
gh issue close 123
gh issue close 123 --comment "Fixed in PR #456"
gh issue reopen 123
```

### Comment

```bash
gh issue comment 123 --body "Comment text"
```

### Other

```bash
gh issue status
gh issue pin 123 / gh issue unpin 123
gh issue lock 123 --reason off-topic / gh issue unlock 123
gh issue transfer 123 --repo owner/new-repo
gh issue delete 123 --yes
gh issue develop 123 --branch fix/issue-123 --base main
```

## Pull Requests

### Create

```bash
gh pr create
gh pr create --title "Title" --body "Body"
gh pr create --body-file .github/PULL_REQUEST_TEMPLATE.md
gh pr create --base main --head feature-branch
gh pr create --draft
gh pr create --assignee user1 --reviewer user2
gh pr create --label enhancement --milestone "v1.0"
gh pr create --repo owner/repo
gh pr create --web
```

### List

```bash
gh pr list
gh pr list --state all / --state merged / --state closed
gh pr list --head feature-branch --base main
gh pr list --author @me
gh pr list --labels bug,enhancement
gh pr list --search "is:open review:required"
gh pr list --limit 50 --sort created --order desc
gh pr list --json number,title,state,author,headRefName
```

### View

```bash
gh pr view 123
gh pr view 123 --comments
gh pr view 123 --web
gh pr view 123 --json title,body,state,commits,files
```

### Checkout

```bash
gh pr checkout 123
gh pr checkout 123 --branch name-123 --force
```

### Diff

```bash
gh pr diff 123
gh pr diff 123 --color always
gh pr diff 123 --name-only
```

### Merge

```bash
gh pr merge 123 --merge / --squash / --rebase
gh pr merge 123 --delete-branch
gh pr merge 123 --subject "Merge PR" --body "Description"
gh pr merge 123 --admin  # bypass branch protections
```

### Close / Reopen

```bash
gh pr close 123 --comment "Closing because..."
gh pr reopen 123
```

### Edit

```bash
gh pr edit 123 --title "New title" --body "New body"
gh pr edit 123 --add-label bug --remove-label stale
gh pr edit 123 --add-assignee user1 --add-reviewer user2
```

### Review

```bash
gh pr review 123 --approve --body "LGTM!"
gh pr review 123 --request-changes --body "Fix these issues"
gh pr review 123 --comment --body "Thoughts..."
```

### Other

```bash
gh pr ready 123
gh pr checks 123 --watch --interval 5
gh pr comment 123 --body "Comment"
gh pr update-branch 123
gh pr lock 123 --reason off-topic / gh pr unlock 123
gh pr revert 123 --branch revert-pr-123
gh pr status
```

## GitHub Actions

### Workflow Runs

```bash
gh run list
gh run list --workflow "ci.yml" --branch main --limit 20
gh run list --json databaseId,status,conclusion,headBranch
gh run view 123456789
gh run view 123456789 --log
gh run view 123456789 --job 987654321
gh run view 123456789 --web
gh run watch 123456789 --interval 5
gh run rerun 123456789
gh run rerun 123456789 --job 987654321
gh run cancel 123456789
gh run delete 123456789
gh run download 123456789 --name build --dir ./artifacts
```

### Workflows

```bash
gh workflow list
gh workflow view ci.yml / --yaml / --web
gh workflow enable ci.yml / gh workflow disable ci.yml
gh workflow run ci.yml
gh workflow run ci.yml --raw-field version="1.0.0" --ref develop
```

### Caches

```bash
gh cache list --branch main
gh cache delete 123456789
gh cache delete --all
```

### Secrets

```bash
gh secret list
gh secret set MY_SECRET
echo "$VALUE" | gh secret set MY_SECRET
gh secret set MY_SECRET --env production
gh secret set MY_SECRET --org orgname
gh secret delete MY_SECRET
```

### Variables

```bash
gh variable list
gh variable set MY_VAR "value"
gh variable set MY_VAR "value" --env production
gh variable get MY_VAR
gh variable delete MY_VAR
```

## Projects

```bash
gh project list --owner owner
gh project view 123 --format json
gh project create --title "Project" --org orgname
gh project edit 123 --title "New Title"
gh project delete 123
gh project close 123
gh project field-list 123
gh project field-create 123 --title "Status" --datatype single_select
gh project item-list 123
gh project item-create 123 --title "Task"
gh project item-add 123 --owner owner --repo repo --issue 456
gh project item-edit 123 --id 456 --title "Updated"
gh project item-delete 123 --id 456
gh project view 123 --web
```

## Releases

```bash
gh release list
gh release view v1.0.0 / --web
gh release create v1.0.0 --notes "Notes" --target main
gh release create v1.0.0 --notes-file notes.md --draft --prerelease
gh release create v1.0.0 --title "Version 1.0.0"
gh release upload v1.0.0 ./file.tar.gz
gh release download v1.0.0 --pattern "*.tar.gz" --dir ./downloads
gh release download v1.0.0 --archive zip
gh release edit v1.0.0 --notes "Updated notes"
gh release delete v1.0.0 --yes
```

## Gists

```bash
gh gist list
gh gist view abc123 --files
gh gist create script.py --desc "Description" --public
gh gist create file1.py file2.py
echo "content" | gh gist create
gh gist edit abc123
gh gist delete abc123
gh gist clone abc123
```

## Codespaces

```bash
gh codespace list
gh codespace create --repo owner/repo --branch develop --machine premiumLinux
gh codespace ssh
gh codespace code
gh codespace stop
gh codespace delete
gh codespace logs
gh codespace ports
gh codespace rebuild
gh codespace cp file.txt :/workspaces/file.txt
gh codespace cp :/workspaces/file.txt ./file.txt
```

## Search

```bash
gh search code "TODO" --repo owner/repo
gh search commits "fix bug"
gh search issues "label:bug state:open"
gh search prs "is:open review:required"
gh search repos "stars:>1000 language:python"
gh search repos "topic:api" --limit 50 --order desc --sort stars
gh search repos --json name,description,stargazers
```

## Labels

```bash
gh label list
gh label create bug --color "d73a4a" --description "Something isn't working"
gh label edit bug --name "bug-report" --color "ff0000"
gh label delete bug
gh label clone owner/repo
```

## API Requests

```bash
# GET (read-only)
gh api /user
gh api /repos/{owner}/{repo}
gh api /user/repos --paginate

# With jq filtering
gh api /user --jq '.login'

# POST (mutating — requires user approval)
gh api --method POST /repos/{owner}/{repo}/issues \
  -f title="Title" \
  -f body="Body"

# GraphQL
gh api graphql -f query='{ viewer { login } }'

# Headers
gh api /user --header "Accept: application/vnd.github.v3+json"

# Include response headers
gh api /user --include
```

**Important:** `gh api -f` does not support object values. Use multiple `-f` flags with hierarchical keys and string values.

## Configuration

```bash
gh config list
gh config get editor
gh config set editor vim
gh config set git_protocol ssh
gh config set prompt disabled
gh config clear-cache
```

### Environment Variables

| Variable             | Purpose                     |
| -------------------- | --------------------------- |
| `GH_TOKEN`           | Authentication token        |
| `GH_HOST`            | Default hostname            |
| `GH_PROMPT_DISABLED` | Disable interactive prompts |
| `GH_EDITOR`          | Custom editor               |
| `GH_PAGER`           | Custom pager                |
| `GH_REPO`            | Override default repository |

## Extensions and Aliases

### Extensions

```bash
gh extension list
gh extension search github
gh extension install owner/extension-repo
gh extension upgrade extension-name
gh extension remove extension-name
gh extension create my-extension
```

### Aliases

```bash
gh alias list
gh alias set prview 'pr view --web'
gh alias set co 'pr checkout' --shell
gh alias delete prview
```

## Global Flags

| Flag                       | Description                       |
| -------------------------- | --------------------------------- |
| `--help` / `-h`            | Show help                         |
| `--repo [HOST/]OWNER/REPO` | Select repository                 |
| `--hostname HOST`          | GitHub hostname                   |
| `--jq EXPRESSION`          | Filter JSON output                |
| `--json FIELDS`            | Output JSON with specified fields |
| `--template STRING`        | Format with Go template           |
| `--web`                    | Open in browser                   |
| `--paginate`               | Paginate API calls                |
| `--verbose` / `--debug`    | Verbose/debug output              |
