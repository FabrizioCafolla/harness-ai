# harness-ai

Devcontainer feature that scaffolds AI agent and skill assets (Claude Code, OpenCode) into a workspace. Each asset is assembled from tool-agnostic content files with per-tool YAML frontmatter injected at runtime.

Nothing is vendored into the published feature. A single script, `cli.sh`, does the actual work — it's fetched at runtime (pinned to the feature version in the devcontainer, or from `main` for standalone use) and it clones this repo to get `harness.py` and the content it needs. The devcontainer and the `curl | bash` installer run the exact same file.

Configuration follows one rule: **`.harness-ai/config.yaml` in your workspace wins.** The devcontainer feature has no options at all — everything configurable lives in that one file.

---

## Getting Started

Pick one:

### Devcontainer

Add the feature to `devcontainer.json` (Python must come first — see [Prerequisites](#prerequisites)):

```json
{
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.13" },
    "ghcr.io/fabriziocafolla/harness-ai/harness-ai:0": {}
  }
}
```

Rebuild the container. On create, `harnessai install` runs automatically: it seeds `.harness-ai/config.yaml`, installs RTK/Headroom/openspec (on by default), and scaffolds `.claude/` (skills, agents, hooks, statusline). Every later start re-syncs via `harnessai sync` if content changed. Nothing to run by hand.

### Standalone CLI

In any workspace, no devcontainer needed:

```bash
curl -fsSL https://raw.githubusercontent.com/FabrizioCafolla/harness-ai/main/cli.sh | bash
```

That's `install` with the defaults: Claude only, RTK + Headroom + openspec on, wikictl off. It creates `.claude/`, `.mcp.json`, `.gitignore` entries, and a `.harness-ai/config.yaml` you can edit directly afterward — no need to remember flags, just change the YAML and re-run:

```bash
curl -fsSL https://raw.githubusercontent.com/FabrizioCafolla/harness-ai/main/cli.sh | bash -s -- sync
```

Want OpenCode too, or wikictl on from the start? Pass flags on the first run instead of editing YAML after:

```bash
curl -fsSL https://raw.githubusercontent.com/FabrizioCafolla/harness-ai/main/cli.sh | bash -s -- install --tools claude,opencode --wikictl
```

Full flag reference: [CLI § Options](#options). Full config reference: [Configuration](#configuration).

---

## Prerequisites

### Supported base images

harness-ai requires **bash** and **Python 3.9+** (which includes `venv` out of the box).

| Base                   | Supported | Notes                                          |
| ---------------------- | --------- | ----------------------------------------------- |
| Debian / Ubuntu        | Yes       | All `mcr.microsoft.com/devcontainers/*` images |
| RHEL / Fedora / CentOS | Yes       | bash and python3 available via dnf/yum         |
| Alpine                 | No        | No bash by default (busybox sh only)           |

### Python 3.9+

harness-ai does **not** install Python you must provide it via the base image or the devcontainer Python feature.

For devcontainers, add the Python feature **before** harness-ai:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/python:1": { "version": "3.13" },
    "ghcr.io/fabriziocafolla/harness-ai/harness-ai:0": {}
  }
}
```

For CLI usage, ensure `python3 >= 3.9` is in your PATH.

### uv (optional)

Only needed if you enable Headroom or wikictl (`uv tool install` under the hood). Without it, those installs are skipped with a warning; everything else works.

### npm (optional)

Only needed for `install.openspec` (on by default). Without it, the openspec install is skipped with a warning; everything else works.

---

## How it works

**Devcontainer:**

1. `install.sh` runs once at image build. It doesn't install anything — it just checks Python, reads the feature's `version`, and writes `/usr/local/bin/harnessai`, a small launcher with that version baked in as the pinned ref.
2. `postCreateCommand: harnessai install` runs on first container create: fetches `cli.sh` at the pinned ref, resolves `.harness-ai/config.yaml`, installs whatever's enabled (RTK/Headroom/wikictl/openspec), and runs the first scaffold.
3. `postStartCommand: harnessai sync` runs on every later start: fetches `cli.sh` again, but only re-scaffolds if content actually changed (a cheap `git ls-remote` hash check) — no binary reinstalls.
4. Both exit 0 on failure. Offline, GitHub down, whatever — container start is never blocked.

**Standalone CLI:** `cli.sh` is fetched via `curl | bash`, clones harness-ai at `--ref` (default `main`), resolves config the same way, and runs the scaffold. It's literally the same script the devcontainer uses.

---

## Usage

### Devcontainer

Same feature block as [Getting Started](#getting-started) — no options. Every setting lives in `.harness-ai/config.yaml` (see [Configuration](#configuration)).

### CLI

Download once instead of piping on every invocation:

```bash
curl -fsSL https://raw.githubusercontent.com/FabrizioCafolla/harness-ai/main/cli.sh -o harness-ai.sh
bash harness-ai.sh [install|sync] [OPTIONS]
bash harness-ai.sh init-extension <path> [--name <str>]
```

#### Subcommands

| Subcommand             | Description                                                                                                        |
| ----------------------- | -------------------------------------------------------------------------------------------------------------------- |
| `install`               | Resolve config, install enabled binaries (RTK/Headroom/wikictl/openspec/custom), run the scaffold. Default when omitted. |
| `sync`                  | Fast path: skip binary installs, hash-check before re-scaffolding.                                                  |
| `init-extension <path>` | Scaffold a minimal starter content-repo extension at `<path>` — see [Extending harness-ai](#extending-harness-ai). |

#### Options

Every CLI flag has an equivalent key in `.harness-ai/config.yaml` (see [Configuration](#configuration)), which takes priority when present — flags only matter for a workspace's first run, before that file exists. Run `bash harness-ai.sh -h` for the full, current flag list rather than duplicating it here.

**Requirements:** `git`, `python3 >= 3.9` with `venv` module (pyyaml is installed automatically in an isolated venv if missing).

#### Interactive mode

```bash
bash harness-ai.sh install --interactive
```

Prompts for each setting (tools, install toggles, caveman default, content repo). Flags passed before `--interactive` set the defaults shown in the prompts. `.harness-ai/config.yaml`, if present, still wins over whatever you answer.

---

## Configuration

`.harness-ai/config.yaml` in the target workspace is the single source of truth, shared by the devcontainer (which has no options of its own) and the CLI. It's created copy-once on the first `harnessai install`, seeded from the built-in defaults, and from then on any key it sets overrides the matching CLI flag.

```yaml
version: 1
tools: [claude]              # claude, opencode
install:
  rtk: true
  headroom: true
  wikictl: false
  openspec: true
  # Arbitrary extra install commands (run as `bash -c "<command>"`, skipped
  # by `sync`). Must be self-idempotent — no already-installed check is done.
  custom:
    speckit: "uv tool install speckit-cli"
scaffold:
  createFileMCP: true
  createFileHooks: true
  createFileSetting: true
  updateGitignore: true
  installDefaults: true
behavior:
  caveman: true
contentRepo:
  url: ""
  ref: main
```

Edit it directly to change tools, toggle an install, flip a behavior default, or point at a content repo. No rebuild needed — just run `harnessai install` (or wait for the next `harnessai sync`).

`.harness-ai/lock` and `.harness-ai/manifest.json` live alongside `config.yaml` in the same directory — only `config.yaml` is tracked in git; the other two are harness-ai's own state and are gitignored.

---

## Usability extras

- **Statusline** (Claude Code only — `.claude/statusline.sh` + `statusLine` in the `settings.json` template, scaffolded when `claude` is in `tools`): model, directory, git branch, context window % with color-coded bar, token counts, session cost (API billing only — hidden on Pro/Max plans where `rate_limits` is present), lines added/removed, 5-hour rate limit, and token-saving tool indicators (`⚡rtk` / `🪨caveman`, green = active, dim = installed). The caveman indicator reads `.harness-ai/config.yaml`'s `behavior.caveman` value directly rather than parsing the session transcript (that schema is undocumented and unstable across Claude Code releases) — it shows the configured default, not necessarily the exact current-turn state. Requires `jq` in the container; degrades to a minimal line without it. Skipped if the workspace already has `.claude/statusline.sh` / `settings.json`.
- **Caveman skill, default-on** ([upstream](https://github.com/JuliusBrussee/caveman)): bundled in the default skills, deployed to every active tool's skills dir (`.claude/skills/caveman`, `.opencode/skills/caveman`). Compresses the model's prose replies (~65% of output tokens). When `behavior.caveman: true` (the default) and the skill is installed, harness-ai injects an instruction into the AGENTS.md managed block — read natively by both Claude Code and OpenCode — so caveman mode applies from the first message of every session, no `/caveman` invocation needed. Turn it off for a session with "stop caveman", or disable the default entirely with `behavior.caveman: false`. Refresh the bundled copy from upstream with `just update-skills caveman`.
- **RTK** (`install.rtk` / `--no-rtk`, on by default): installs the binary; for Claude Code, injects the `PreToolUse` hook into the Claude hooks template so every scaffold run merges it into `.claude/settings.json`; for OpenCode, drops a static plugin (`.opencode/plugins/rtk.ts`, vendored from [rtk-ai/rtk](https://github.com/rtk-ai/rtk)) that self-disables at runtime if the `rtk` binary isn't on PATH. Bash commands are then transparently rewritten to token-compressed `rtk` equivalents (60-90% savings on `git status`, test runners, `find`, …). Check savings with `rtk gain`.
- **Headroom** (`install.headroom` / `--no-headroom`, on by default): installs the CLI via `uv tool install "headroom-ai[proxy]"` (requires `uv`; warns and continues if missing). Compresses the request payload at the API boundary — a different layer than RTK. Not a hook and **not auto-active**: activate per-session with `headroom wrap <cli>` (e.g. `headroom wrap claude`, `headroom wrap opencode`). Overlaps RTK on the input side while active, so prefer one over the other rather than stacking both.
- **openspec** (`install.openspec` / `--no-openspec`, on by default): installs the [`@fission-ai/openspec`](https://www.npmjs.com/package/@fission-ai/openspec) CLI via `npm install -g`. Skipped with a warning if `npm` isn't on PATH; never fails the rest of the install.

---

## wikictl

A file-based memory layer for AI agents — a wiki of Markdown entries with YAML frontmatter, queried over MCP. Its source lives at `wikictl/` in this repo and is fetched by `cli.sh` at the pinned ref, same as everything else no separate vendoring step.

Off by default. Enabling it (`install.wikictl: true` in `.harness-ai/config.yaml`, or `--wikictl` on the CLI) provisions:

- **CLI** — installed via `uv tool install` from the fetched checkout (requires `uv`; warns and continues if missing). Provides `wikictl create|read|list|search|tags|edit|move|delete|schema|index|serve`.
- **MCP server** — a gated `wikictl` entry (`http://127.0.0.1:9797/mcp/`, started by `wikictl serve`) merged into `.mcp.json` (Claude Code) and, when `opencode` is in `tools`, into `opencode.json`'s `mcp` key. The server encodes a metadata-first protocol and exposes `get_schema` (the entry metadata contract).

The `wikictl-*` skills deploy unconditionally alongside the other default skills, regardless of whether wikictl itself is enabled.

```yaml
install:
  wikictl: true
```

---

## Content repo

Point at any GitHub repo that follows the `content/` structure to merge additional (or private) agents and skills on top of the bundled defaults.

### Layout

```
your-content-repo/
├── agents/
│   ├── metadata.yml    # per-tool frontmatter for each agent
│   └── my-agent.md     # agent content (no frontmatter)
├── skills/
│   ├── metadata.yml    # per-tool frontmatter for each skill
│   └── my-skill/
│       └── SKILL.md    # skill content (no frontmatter)
├── hooks/              # optional: override default hook templates
│   ├── claude.json     # replaces config/claude/hooks.json
│   └── opencode.ts     # replaces config/opencode/rtk-plugin.ts
├── mcp.json            # optional: override shared .mcp.json template
├── opencode.json       # optional: override the opencode.json starter template
└── agents.harness-ai.md  # optional: extra content appended to the AGENTS.md managed block
```

You can include any subset anything absent falls back to bundled defaults (unless `installDefaults: false` / `--no-defaults`). Hooks and MCP overrides are full replacements, not merges. Remote content wins on key conflicts with the bundled defaults.

### Using it

Set the content repo in `.harness-ai/config.yaml` (not as a feature option there are no feature options):

```yaml
contentRepo:
  url: https://github.com/my-org/ai-content
  ref: main
```

For private repos, set `GITHUB_TOKEN` as a devcontainer secret:

```json
{
  "secrets": ["GITHUB_TOKEN"]
}
```

Auth resolves automatically: `GITHUB_TOKEN` env var → `gh` CLI token → anonymous (public repos only).

From the CLI, the equivalent is a flag instead of YAML:

```bash
GITHUB_TOKEN=$(gh auth token) bash harness-ai.sh install --content-repo https://github.com/my-org/ai-content
```

---

## Extending harness-ai

Don't hand-write a new content repo's layout ([Content repo](#content-repo) above) — generate it:

```bash
bash harness-ai.sh init-extension ./my-extension --name "My Extension"
```

This scaffolds the lean shape a real extension actually needs: `agents/metadata.yml` + one placeholder agent, `skills/metadata.yml` + one placeholder skill, a starter `agents.harness-ai.md`, and a `README.md`. Verify it works before customizing:

```bash
bash harness-ai.sh install --content-repo-local-path ./my-extension
```

`hooks/`, `mcp.json`, and `paths.yml` overrides are supported but optional/advanced — `init-extension` doesn't scaffold them; see [AGENTS.md](./AGENTS.md#content-repo-format) for their format. For the skill-naming and taxonomy conventions your new skills should follow, and for contributing to harness-ai's own code, see [AGENTS.md](./AGENTS.md) and [CONTRIBUTING.md](./CONTRIBUTING.md).
