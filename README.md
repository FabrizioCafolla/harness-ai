# harness-ai

[harness-ai](https://github.com/FabrizioCafolla/harness-ai) is a devcontainer feature that assembles AI skills, agents, and hooks into the workspace at container startup. It merges content from the bundled defaults, any number of named content repos, and a workspace-local source, injects per-tool frontmatter, and writes output to tool-specific paths.

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
| ---------------------- | --------- | ---------------------------------------------- |
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

| Subcommand              | Description                                                                                                              |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `install`               | Resolve config, install enabled binaries (RTK/Headroom/wikictl/openspec/custom), run the scaffold. Default when omitted. |
| `sync`                  | Fast path: skip binary installs, hash-check before re-scaffolding.                                                       |
| `init-extension <path>` | Scaffold a minimal starter content-repo extension at `<path>` — see [Extending harness-ai](#extending-harness-ai).       |

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
tools: [claude] # claude, opencode
install:
  rtk: true
  headroom: true
  wikictl: false
  openspec: true
  # Arbitrary extra install commands (run as `bash -c "<command>"`, skipped
  # by `sync`). Must be self-idempotent — no already-installed check is done.
  custom:
    speckit: 'uv tool install speckit-cli'
scaffold:
  createFileMCP: true
  createFileHooks: true
  createFileSetting: true
  updateGitignore: true
  installDefaults: true
behavior:
  caveman: true
contentRepos: []
skills:
  include:
    categories: []
    keys: []
  exclude:
    categories: []
    keys: []
```

Edit it directly to change tools, toggle an install, flip a behavior default, or point at one or more content repos. No rebuild needed — just run `harnessai install` (or wait for the next `harnessai sync`).

**Skill selection** (`skills.include`/`skills.exclude`, or the matching `--skills-include-categories`/`--skills-include-keys`/`--skills-exclude-categories`/`--skills-exclude-keys` flags): filters which `default`/content-repo/`workspace` skills get installed, by category, `category.subcategory`, or explicit key. Empty `include` means "install everything" (today's default). `exclude` is checked after `include`, so it can carve one key out of an otherwise-included category. Agents are never filtered this way. `local` skills aren't gated by `include`/category rules at all (they're always installed if present) — only `exclude.keys` can remove one by name. See the [Skill taxonomy](#skill-taxonomy) table below for valid category/subcategory values.

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

## Content repos

Point at one or more GitHub repos that follow the `content/` structure to merge additional (or private) agents and skills on top of the bundled defaults. Each is a named **source** — see [Sources and the canonical store](#sources-and-the-canonical-store) for how they're materialized into the workspace.

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
├── commands/
│   ├── metadata.yml    # per-tool frontmatter for each command
│   ├── my-command.md   # command content (no frontmatter)  ->  /my-command
│   └── ns/
│       └── other.md    # namespaced                        ->  /ns:other
├── hooks/              # optional: override default hook templates
│   ├── claude.json     # replaces config/claude/hooks.json
│   └── opencode.ts     # replaces config/opencode/rtk-plugin.ts
├── mcp.json             # optional: override shared .mcp.json template
├── opencode.json        # optional: override the opencode.json starter template
├── paths.yml             # optional: per-tool output path overrides
└── agents.harness-ai.md  # optional: extra content appended to the AGENTS.md managed block
```

You can include any subset anything absent falls back to bundled defaults (unless `installDefaults: false` / `--no-defaults`). Hooks and MCP overrides are full replacements, not merges. On a same-key collision, later sources win: `default` → `contentRepos` in the order listed → `workspace` (an auto-detected `.harness-ai/local/`, see [below](#workspace-local-content)) → `local` (further below) always last.

### Using it

Set one or more named content repos in `.harness-ai/config.yaml`:

```yaml
contentRepos:
  - name: my-private-content
    url: https://github.com/my-org/ai-content
    ref: main
  - name: another-team-content
    url: https://github.com/other-org/more-content
    ref: main
```

`name` is required and must be unique — it's the subfolder under the canonical store (`.harness-ai/skills/<name>/`) and the label used in the sync report. `default`, `workspace`, and `local` are reserved (harness-ai rejects a config that reuses them).

**Migrating from the old singular key:** `contentRepo: {url, ref}` still works — it's read as sugar for a one-entry `contentRepos` list (name derived from the URL) and prints a deprecation warning. No action needed on upgrade; switch to `contentRepos` whenever convenient.

For private repos, set `GITHUB_TOKEN` as a devcontainer secret:

```json
{
  "secrets": ["GITHUB_TOKEN"]
}
```

Auth resolves automatically: `GITHUB_TOKEN` env var → `gh` CLI token → anonymous (public repos only). It's shared across every configured repo (no per-repo auth).

From the CLI, the equivalent is comma-separated flags instead of YAML:

```bash
GITHUB_TOKEN=$(gh auth token) bash harness-ai.sh install \
  --content-repo https://github.com/my-org/ai-content,https://github.com/other-org/more-content \
  --content-repo-name my-private-content,another-team-content
```

---

## Workspace-local content

A **`workspace`** source is auto-detected from `.harness-ai/local/` in the target workspace — no config entry, no git repo, no clone. It's structured exactly like a [content repo](#content-repos), just read straight from that directory:

```
.harness-ai/local/
├── agents/
│   ├── metadata.yml
│   └── my-agent.md
├── skills/
│   ├── metadata.yml
│   └── my-skill/
│       └── SKILL.md
└── paths.yml   # optional — falls back to `default`'s if omitted
```

Full category/subcategory support and `skills.include`/`skills.exclude` filtering apply exactly as for `default`/`contentRepos`. On a same-key collision, `workspace` wins over `default` and every `contentRepos` entry (it's last in load order) but still loses to a real `local` (`.harness-ai/skills/local/`) file, which always wins over everything.

Use `workspace` for project-specific overrides that want the full repo-shaped format (categories, per-tool profiles); use [`local`](#local-skills) for a quick, no-ceremony single file. They're not mutually exclusive — a workspace can use both.

Delete `.harness-ai/local/` and re-sync to remove the source cleanly; nothing special to undo.

---

## Skill paths

Take a single skill straight from a directory inside someone else's repo, without vendoring it or adding the whole repo as a content source:

```yaml
skillPaths:
  - url: https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me
```

The ref and the sub-path are read out of the GitHub URL, so that is usually the whole entry. Three optional fields cover the rest:

| field | when you need it |
| --- | --- |
| `name` | install the skill under a different key than the directory name |
| `ref` | pin a branch or tag other than the one in the URL (an explicit `ref` always wins) |
| `path` | point inside a remote whose URL has no `/tree/` part (a self-hosted git host, a `file://` checkout) |

**One skill or many.** A path holding a `SKILL.md` is a single skill. A path that doesn't is treated as a folder of skills, and every immediate sub-directory holding a `SKILL.md` is installed under its own name.

**The whole directory travels.** Examples, `scripts/`, `agents/`, `references/`: whatever the skill ships beside `SKILL.md` comes with it, because a skill whose instructions point at its own files is broken without them.

Frontmatter is read from the file itself (third-party skills carry it inline, unlike a content repo's `metadata.yml`) and passed through verbatim, extra keys included. Nothing of ours is stamped on top: harness-ai's bundled `license`/`author` defaults are deliberately not applied to a skill someone else wrote.

**Precedence.** `skillPaths` sits above the bundled defaults and below `contentRepos`: a repo you curate always outranks a skill pulled from elsewhere, and `local` still wins over everything. Fetching uses a sparse checkout of just that sub-path, and `sync`'s fast path tracks each entry's remote SHA with `git ls-remote`, so an upstream change is picked up without cloning to find out.

---

## Commands

Commands are slash commands (`/deploy:rollback`) and ship through the same pipeline as skills and
agents: `default` -> `contentRepos` -> `workspace` -> `local`, later sources winning an identical
key, foreign content never overwritten.

The one thing specific to commands is the key. A command is **addressed by its path**, so the key
*is* the path under `commands/`, without the `.md`, namespace directories included:

| key in `metadata.yml` | content file | rendered to | invoked as |
| --- | --- | --- | --- |
| `deep-task-analysis` | `commands/deep-task-analysis.md` | `.claude/commands/deep-task-analysis.md` | `/deep-task-analysis` |
| `dev/deep-task-analysis` | `commands/dev/deep-task-analysis.md` | `.claude/commands/dev/deep-task-analysis.md` | `/dev:deep-task-analysis` |

`metadata.yml` carries the per-tool frontmatter, exactly like skills and agents. For Claude that is
`description`, `argument-hint`, `allowed-tools`, `model`:

```yaml
default:
  claude:
    metadata:
      author: You
      version: "1.0"
  agents:

commands:
  dev/deep-task-analysis:
    claude:
      name: deep-task-analysis
      description: Research, plan, then implement locally.
      argument-hint: "<target-path> <issue-or-goal>"
      allowed-tools: [Read, Grep, Edit, Write, Bash]
```

A `local` command needs no `metadata.yml`: write the frontmatter inline in
`.harness-ai/commands/local/<ns>/<name>.md`, same as a local skill or agent.

Cleanup removes a stale command's symlink and prunes the namespace directory it leaves empty, so a
renamed namespace doesn't leave an empty folder in the tool's command list.

Only tool profiles that declare a `commands` block in `paths.yml` receive them: today `claude` and
the tool-neutral `agents` profile. `opencode` deliberately has none yet, since its command path
convention hasn't been verified here. Add a `commands:` block to its profile to turn it on.

---

## Local skills

A **`local`** source formalizes hand-authoring a skill or agent directly in the *consuming* workspace's own canonical store, no content repo needed:

```
.harness-ai/
├── skills/local/
│   └── my-skill/
│       ├── SKILL.md       # frontmatter INLINE (name/description in the file itself)
│       └── references/    # optional, used as-is
├── agents/local/
│   └── my-agent.md         # frontmatter inline
└── commands/local/
    └── ns/
        └── my-command.md   # frontmatter inline  ->  /ns:my-command
```

Unlike `default`/content-repo/`workspace` skills, a `local` file's frontmatter lives directly in the file (the way Claude Code's own Skill/Agent authoring tools write them) — there's no `metadata.yml` and no per-tool rendering step. harness-ai discovers every `SKILL.md`/`<key>.md` under `.harness-ai/skills/local/`/`.harness-ai/agents/local/` on each run and symlinks its whole skill directory (or the agent file) into every active tool's directory, `.agents/skills/<key>` included — `local` renders through the exact same canonical-store-plus-symlink path every other source uses, with no tool-specific exception. It's the one source harness-ai **never deletes or rewrites at its canonical location** — only a dangling tool-dir symlink whose local file disappeared gets cleaned up; the authored file itself is always yours.

`local` always wins on a same-key collision with `default`/content-repo/`workspace` sources — a workspace can deliberately override a bundled, repo, or `workspace` skill by authoring the same key locally.

Category/subcategory filtering (below) doesn't apply to `local` skills (they carry no metadata for it) — `skills.exclude.keys` can still remove one by name.

**Migrating from the pre-1.0 layout**: earlier versions authored `local` directly at `.agents/skills/<key>/SKILL.md` / `.agents/agents/<key>.md`, which also had to double as the always-on `agents` tool's render target. If you have real files there, move them by hand before upgrading:

```
mv .agents/skills/<key> .harness-ai/skills/local/<key>
mv .agents/agents/<key>.md .harness-ai/agents/local/<key>.md
```

Do this for every `local` key, then run `harnessai sync --force`. Skipping the move isn't silently dangerous — the foreign-entry-safety guard refuses to turn a real `.agents/skills/<key>` file into a symlink and reports it as `[foreign]` instead, so nothing is lost, but the key won't render into any tool until you complete the move.

---

## Public vs. private project setup

Three shapes, combinable:

- **Public / bundled-only** — no `contentRepos`. Just the bundled `content/` (developer/advisor skills, taxonomy) plus whatever `local` skills the workspace authors itself. The default for a new workspace.
- **Private content repo(s)** — one or more `contentRepos` entries pointing at a private (or public) repo with your own/your team's skills and agents, merged on top of the bundled defaults. Set `GITHUB_TOKEN` for private repos.
- **Workspace-only `workspace` content** — a `.harness-ai/local/` directory, repo-shaped but never published anywhere; auto-detected, no config entry.
- **Workspace-only `local` skills** — no content repo at all, just hand-authored `.harness-ai/skills/local/<key>/SKILL.md` files. Useful for skills that are specific to one project and not worth publishing anywhere.

Most real setups combine several of these: bundled defaults + a team's private repo + a handful of project-specific `local`/`workspace` skills the bundled/private content doesn't cover.

## Sources and the canonical store

Every source — `default`, each `contentRepos` entry, `workspace`, and `local` — has a canonical store under `.harness-ai/`, tracked in git:

```
.harness-ai/
├── skills/<source>/<key>/
│   ├── claude.SKILL.md      # rendered with the claude frontmatter block
│   ├── opencode.SKILL.md    # only if opencode is active
│   ├── agents.SKILL.md      # always (the .agents target is always-on, see below)
│   └── references/          # copied once from the source, shared across profiles
└── agents/<source>/<key>/
    ├── claude.md
    ├── opencode.md
    └── agents.md
```

`.claude/skills/<key>/SKILL.md`, `.opencode/skills/<key>/SKILL.md`, and `.agents/skills/<key>/SKILL.md` become symlinks into that store instead of independent copies — one canonical render per tool profile, referenced everywhere it's needed. This is tracked in git (not gitignored) so a fresh clone has working skills immediately, and a PR diff shows exactly what content changed and from where.

`local`'s canonical store (`.harness-ai/skills/local/<key>/`, `.harness-ai/agents/local/<key>.md`) is the one exception to the "rendered per tool profile" shape: since `local` has no `metadata.yml` and no per-tool frontmatter, it's authored as exactly one file per key, and every tool directory — `.agents` included — symlinks straight to that one file rather than to a per-profile render (see [Local skills](#local-skills) above). It's still a real canonical store like every other source: tracked in git, protected by the same foreign-entry-safety guard, never a render target for anything else.

**`.agents` is always populated**, independent of `tools:` — unlike `claude`/`opencode`, which stay opt-in. It's the emerging cross-tool convention other tools read directly.

**Prerequisite:** symlinked output requires `core.symlinks=true` in the git checkout — git's default on Linux/macOS (every devcontainer, unconditionally); on native Windows it needs Developer Mode/admin (`git config core.symlinks true`) for the standalone-CLI case.

### Foreign content is never overwritten

Before placing any symlink, harness-ai checks whether the target already holds real, non-symlink content it doesn't recognize (something you or another tool put there directly, outside any configured source). If so, it's left completely untouched instead of being deleted — you'll see a `[foreign]` line naming the tool, source, and key that was blocked. Independent of that, every `sync`/`install` run also lists, in an "unmanaged entries" section (only printed when non-empty), every tool-dir path that no source currently claims — so you always know what's sitting in `.claude/skills`/`.opencode/skills`/`.agents/skills` outside harness-ai's management, even without a collision.

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

## Skill taxonomy

Skills are organized by category and subcategory. Every entry in `metadata.yml` carries `category` and `subcategory` fields.

Plain, single-word subcategories on purpose — grouping follows what a skill actually does, not a target count.

| Category        | Subcategory     | Typical prefix                           |
| --------------- | --------------- | ---------------------------------------- |
| `engineering`   | `coding`        | `developer-*`                            |
| `engineering`   | `architecture`  | `developer-*`, `advisor-*`               |
| `engineering`   | `operations`    | `advisor-*`                              |
| `engineering`   | `documentation` | `advisor-*`                              |
| `communication` | `content`       | `advisor-*`                              |
| `communication` | `messaging`     | `advisor-*`                              |
| `communication` | `style`         | `caveman`                                |
| `reasoning`     | `brainstorming` | `advisor-*`                              |
| `reasoning`     | `research`      | `advisor-*`, `research-scout`            |
| `reasoning`     | `speaking`      | `advisor-*`                              |
| `tools`         | `cli`           | `developer-github-cli`, `wikictl-*`      |
| `meta`          | `creation`      | `skill-creator`, `agent-creator`         |
| `meta`          | `review`        | `advisor-work-review`                    |
| `coaching`      | `planning`      | `advisor-*` (private, personal-training) |
| `coaching`      | `support`       | `advisor-*` (private, personal-training) |
