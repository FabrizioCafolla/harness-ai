# GitHub Actions Conventions

Best practices for GitHub Actions workflows, including security, performance, and maintainability.
Based on [GitHub Actions Documentation](https://docs.github.com/en/actions) and [Security hardening for GitHub Actions](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions).

## Workflow Structure

> Ref: [Workflow syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true # Cancel outdated PR runs, not main

jobs:
  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15 # Always set prevents hung jobs burning credits
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '22'
          cache: 'npm'
      - run: npm ci
      - run: npm test
```

**Rules:**

- Always set `timeout-minutes` on every job
- Use `concurrency` to cancel outdated PR runs save credits, reduce noise
- Pin action versions to a full SHA for security-critical workflows (`uses: actions/checkout@11bd71901...`)
- For convenience, pinning to `@v4` is acceptable for trusted actions

## Caching

> Ref: [Caching dependencies](https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/caching-dependencies-to-speed-up-workflows)

```yaml
# Node.js built into setup-node
- uses: actions/setup-node@v4
  with:
    node-version: '22'
    cache: 'npm' # Caches node_modules based on lockfile hash

# Python built into setup-python
- uses: actions/setup-python@v5
  with:
    python-version: '3.13'
    cache: 'pip'

# Generic cache
- uses: actions/cache@v4
  with:
    path: ~/.cache/go-build
    key: ${{ runner.os }}-go-${{ hashFiles('**/go.sum') }}
    restore-keys: |
      ${{ runner.os }}-go-
```

**Rule**: Always include the lockfile hash in the cache key stale caches cause subtle bugs.

## Secrets Management

> Ref: [Using secrets](https://docs.github.com/en/actions/security-for-github-actions/security-guides/using-secrets-in-github-actions), [OIDC for cloud providers](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/about-security-hardening-with-openid-connect)

```yaml
# Reference secrets never hardcode
env:
  AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
  DATABASE_URL: ${{ secrets.DATABASE_URL }}

# Use environments for deployment secrets
jobs:
  deploy:
    environment: production # Links to an Environment with its own secrets
    steps:
      - run: deploy.sh
        env:
          DEPLOY_KEY: ${{ secrets.DEPLOY_KEY }}
```

**Rules:**

- All credentials go in GitHub Secrets never in env vars hardcoded in YAML
- Use **Environments** (`production`, `staging`) for deployment-specific secrets with protection rules
- Never print secrets: `echo ${{ secrets.TOKEN }}` prints `***` but can leak in logs via other means
- Use OIDC for AWS/GCP/Azure instead of long-lived access keys:

```yaml
permissions:
  id-token: write
  contents: read

- uses: aws-actions/configure-aws-credentials@v4
  with:
    role-to-assume: arn:aws:iam::123456789:role/GitHubActions
    aws-region: eu-west-1
```

## Reusable Workflows

> Ref: [Reusable workflows](https://docs.github.com/en/actions/sharing-automations/reusing-workflows), [Composite actions](https://docs.github.com/en/actions/sharing-automations/creating-actions/creating-a-composite-action)

```yaml
# .github/workflows/reusable-test.yml
on:
  workflow_call:
    inputs:
      node-version:
        required: false
        type: string
        default: '22'
    secrets:
      NPM_TOKEN:
        required: false

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
```

Call from another workflow:

```yaml
jobs:
  test:
    uses: ./.github/workflows/reusable-test.yml
    with:
      node-version: '22'
    secrets: inherit
```

Use reusable workflows to avoid copy-pasting across repos. Composite actions (`action.yml`) are better for single-job step reuse.

## Security Hardening

> Ref: [Security hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions), [Automatic token authentication](https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication)

```yaml
# Minimal permissions by default
permissions:
  contents: read # Specify only what's needed

jobs:
  deploy:
    permissions:
      contents: read
      id-token: write # Only this job needs OIDC
```

**Rules:**

- Set `permissions: read-all` or `permissions: {}` at workflow level, then grant per-job
- Never use `pull_request_target` with untrusted code access to secrets high-risk vector
- Pin third-party actions to commit SHA in security-sensitive workflows
- Use `gh secret set` or the UI never commit secrets

## Matrix Builds

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest, macos-latest]
    node: ['20', '22']
  fail-fast: false # Don't cancel all matrix jobs if one fails
```

## Common Job Patterns

```yaml
# Conditional deployment
- name: Deploy
  if: github.ref == 'refs/heads/main' && github.event_name == 'push'
  run: ./deploy.sh

# Upload artifacts between jobs
- uses: actions/upload-artifact@v4
  with:
    name: build-output
    path: dist/
    retention-days: 7

- uses: actions/download-artifact@v4
  with:
    name: build-output
    path: dist/
```

## Anti-Patterns to Flag

- No `timeout-minutes` jobs can hang indefinitely, burning credits and blocking pipelines
- Hardcoded secrets in workflow YAML visible in repo history forever, even after removal
- Using `pull_request_target` + `actions/checkout` with PR code [critical security flaw](https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/): grants write permissions and secrets access to untrusted fork code
- Unpinned third-party actions (`uses: some-action@main`) a compromised action can exfiltrate secrets; pin to SHA for critical workflows
- Running expensive jobs on every commit without `concurrency` cancel wastes credits and slows feedback
- Using `self-hosted` runners for untrusted fork PRs exposes host environment, filesystem, and network to malicious code
- `if: always()` without understanding it runs even after cancelled jobs use `if: success() || failure()` to skip cancelled
- Not using `permissions` default token has write access to everything; always restrict to minimum needed
- Storing artifacts without `retention-days` consumes storage indefinitely

## Self-Check

- [ ] Every job has `timeout-minutes` set
- [ ] `concurrency` with `cancel-in-progress` on PR workflows
- [ ] `permissions` set at workflow level (restrictive), expanded per-job only where needed
- [ ] All secrets in GitHub Secrets or Environments none hardcoded
- [ ] OIDC used for cloud provider auth instead of long-lived keys
- [ ] Third-party actions pinned to SHA in security-critical workflows
- [ ] Caching configured for dependency installs (lockfile hash in key)
- [ ] Reusable workflows or composite actions for repeated patterns
- [ ] No `pull_request_target` with checkout of PR code
- [ ] Artifacts have `retention-days` configured
