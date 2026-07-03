# Harness AI Developer Guide

harness-ai is a devcontainer feature and standalone CLI that scaffolds AI agent and skill assets (Claude Code, OpenCode) into a workspace. Content is tool-agnostic Markdown; per-tool YAML frontmatter is injected at scaffold time.

## Repository Layout

```
harness-ai/
├── content/                    # Tool-agnostic Markdown content
│   ├── paths.yml               # Output paths per tool (claude / opencode)
│   ├── agents/
│   │   ├── metadata.yml        # Per-tool frontmatter for each agent
│   │   └── <key>.md            # Agent body (no frontmatter)
│   ├── skills/
│   │   ├── metadata.yml        # Per-tool frontmatter for each skill
│   │   └── <skill-key>/
│   │       ├── SKILL.md        # Skill body (no frontmatter)
│   │       └── references/     # Optional reference docs
│   └── agents.harness-ai.md    # Static content injected into every scaffolded AGENTS.md
├── config/                     # Per-tool config templates
│   ├── mcp.json                # Shared .mcp.json template (Claude Code)
│   ├── mcp.wikictl.json        # Gated wikictl MCP entry (merged into .mcp.json when wikictl is enabled)
│   ├── opencode.json           # OpenCode's own config/mcp starter template (copy-once)
│   ├── mcp.wikictl.opencode.json # Gated wikictl MCP entry (merged into opencode.json's mcp key when wikictl is enabled)
│   ├── config.default.yaml     # Starter .harness-ai/config.yaml template (copy-once)
│   ├── claude/
│   │   ├── hooks.json          # Claude hooks template (always-managed; install.rtk injects the rtk hook here)
│   │   ├── settings.json       # Claude settings (copy-once, includes statusLine)
│   │   ├── settings.local.json # Claude local settings (copy-once, gitignored)
│   │   └── statusline.sh       # Claude statusline (copy-once → .claude/statusline.sh)
│   └── opencode/
│       └── rtk-plugin.ts       # OpenCode RTK plugin (always-managed → .opencode/plugins/rtk.ts; vendored from rtk-ai/rtk, self-disables if rtk isn't on PATH)
├── wikictl/                    # wikictl package source (fetched at runtime, never vendored into the feature)
│   ├── pyproject.toml          # Standalone pip-installable package
│   └── src/wikictl/            # CLI + MCP server + render-only web UI
├── harness.py                  # Main Python scaffolder
├── install.sh                  # Devcontainer entrypoint — minimal, generates the harnessai launcher only
├── cli.sh                      # Single implementation: install/sync/init-extension subcommands, used by devcontainer AND curl
└── devcontainer-feature.json   # Feature manifest (no options)
```

## How It Works

Nothing about harness-ai is vendored into the published feature. `cli.sh` is the single implementation of both the devcontainer path and the standalone curl path; on every run it fetches (or, for local dev, uses `--local-path` against) `harness.py` + `content/` + `wikictl/` from this repo at a `--ref`, pinned to the feature version for the devcontainer.

**Devcontainer path:**

1. `install.sh` runs at image build: verifies Python, reads the feature `version` from `devcontainer-feature.json`, and generates `/usr/local/bin/harnessai` — a small launcher with that version baked in as `REF`. It installs no binary and vendors nothing. There are no feature options to bake in — the feature manifest carries `postCreateCommand`/`postStartCommand` only.
2. `postCreateCommand: harnessai install` fetches `cli.sh`@REF and runs its `install` subcommand: resolves `.harness-ai/config.yaml`, installs enabled binaries, runs `harness.py`.
3. `postStartCommand: harnessai sync` fetches `cli.sh`@REF and runs `sync`: a hash-check that only re-scaffolds when content changed, skipping binary installs.
4. Both `harnessai` invocations `|| exit 0` — a failed fetch (offline, GitHub outage) never blocks container start.

**CLI path:**

1. `cli.sh` is fetched via `curl | bash` (defaults to the `install` subcommand if none given)
2. It clones harness-ai at `--ref` (default `main`; `--local-path DIR` uses a local checkout instead — required to test uncommitted changes)
3. It resolves `.harness-ai/config.yaml` in the target workspace on top of CLI flags, installs enabled binaries, optionally clones a `--content-repo`, then runs `harness.py`

**Configuration precedence:** for every setting, `.harness-ai/config.yaml` (workspace) > CLI flag (passed directly to `cli.sh`, or baked into the `harnessai` launcher — though the launcher bakes nothing today, since the feature has no options) > built-in default. The workspace config is copy-once seeded from `config/config.default.yaml`.

**Optional components (gated by `.harness-ai/config.yaml` → `install.*`, or the matching CLI flag):**

- **RTK** (`install.rtk` / `--no-rtk`, default on) — token-compressing Bash rewrite. Claude Code gets a `PreToolUse` hook (merged into `.claude/settings.json[hooks]`); OpenCode gets a static plugin (`config/opencode/rtk-plugin.ts` → `.opencode/plugins/rtk.ts`) that self-disables at runtime if `rtk` isn't on PATH — no cli.sh-side merge step needed for it, see `_apply_opencode_hook` in `harness.py`.
- **Headroom** (`install.headroom` / `--no-headroom`, default on) — request-level context compression CLI; installed but inactive until `headroom wrap <cli>` (e.g. `headroom wrap claude`, `headroom wrap opencode`).
- **openspec** (`install.openspec` / `--no-openspec`, default on) — installs `@fission-ai/openspec` via `npm install -g`; warns and continues if `npm` is missing or the install fails.
- **wikictl** (`install.wikictl` / `--wikictl`, default **off**) — file-based AI memory layer. The source lives at `wikictl/` in this repo, fetched at the pinned ref and installed with `uv tool install "${HARNESS_SRC}/wikictl[serve]"`; warns and continues if `uv` is missing. `cli.sh` passes `--install-wikictl` to `harness.py`, which then merges the gated `config/mcp.wikictl.json` server entry (default port **9797**) into `.mcp.json` (Claude Code) and, when `opencode` is an active tool, `config/mcp.wikictl.opencode.json` into `opencode.json`'s `mcp` key (`_merge_wikictl_mcp_opencode`). The `wikictl-*` skills live in `content/skills/` and deploy unconditionally (like `caveman`).
  - Agents using wikictl read the metadata-first protocol from the MCP server itself: scan with `list_entries`/`search_entries` (metadata only), evaluate relevance from `description`/`tags`, then `read_entry` only what's needed. `get_schema` returns the entry metadata contract (field names, types, required/optional, validation rules) and works on an empty wiki.
  - `cli.sh` guarantees `uv`-installed binaries (wikictl, Headroom) resolve on `PATH` immediately after install: `_ensure_uv_tool_path()` exports `uv tool dir --bin` onto `PATH` for the rest of the current run, and a best-effort `uv tool update-shell` (never fails the install) makes them resolvable in later shells too.
- **custom** (`install.custom`, a `name: <shell command>` map, default `{}`) — arbitrary extra install commands not covered by the four built-ins above (e.g. `speckit: "uv tool install speckit-cli"`). Each entry runs as `bash -c "<command>"` during `install` (never `sync`), warn-and-continue on failure. No already-installed check — commands are expected to be self-idempotent, the same contract mise's `[tasks]` and devbox's `init_hook` use for the same flat name→command shape.

**Behavior defaults (gated by `.harness-ai/config.yaml` → `behavior.*`, or the matching CLI flag — steer model behavior via AGENTS.md, not a binary install; AGENTS.md is read natively by both Claude Code and OpenCode):**

- **caveman-default** (`behavior.caveman` / `--no-caveman`, default on) — when true and the `caveman` skill is among the tool's installed skills, `harness.py`'s `_update_agents_md()` prepends a "respond in caveman mode from message one" instruction to the managed AGENTS.md block. Inert until the `caveman` skill is actually installed (`installDefaults: true` or a content-repo override providing it). The bundled `statusline.sh` (Claude Code only) shows the caveman indicator by reading this config key directly — it does not parse the session transcript (undocumented, unstable schema across Claude Code releases).

**harness.py reads:**

- `content/paths.yml` where to write output files per tool
- `content/agents/metadata.yml` frontmatter for each agent, per tool
- `content/skills/metadata.yml` frontmatter for each skill, per tool
- Markdown bodies from `content/agents/` and `content/skills/`
- `content/agents.harness-ai.md` static content appended to every scaffolded AGENTS.md managed block
- Remote content-repo files merged on top (same key = remote wins, universally — `paths.yml` included, no exceptions); a content repo's own `agents.harness-ai.md`, if present, is appended after the bundled one

## Adding an Agent

1. Create `content/agents/<key>.md` Markdown body only, no frontmatter
2. Register it in `content/agents/metadata.yml`:

```yaml
agents:
  <key>:
    opencode:
      name: Display Name
      description: 'When OpenCode should activate this agent.'
      mode: subagent
    claude:
      name: Display Name
      description: 'When Claude should activate this agent.'
      allowedTools: [Read, Edit, Bash]
```

OpenCode's `permission` key (`edit`/`bash`/`webfetch`: `allow`/`deny`/`ask`) gates broad tool *categories*, not an arbitrary allowlist like Claude's `allowedTools` — there's no lossless 1:1 mapping. Omit `permission` for full access (the default), or set it explicitly per agent if it needs restricting.

## Adding a Skill

### Naming convention

All skills follow one of two prefixes:

| Prefix        | Meaning                                                                                  | Examples                                    |
| ------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------- |
| `developer-*` | Operative used while **building** (language conventions, framework patterns, tool usage) | `developer-python`, `developer-kubernetes`  |
| `advisor-*`   | Strategic used for **decisions, reviews, design**                                        | `advisor-sre`, `advisor-cloud-architecture` |

Named exceptions with no prefix: `research-scout`, `skill-creator`, `agent-creator` (cross-cutting meta tools), `caveman` (a response-style modifier, not a build/advise skill), and `wikictl`, `wikictl-read`, `wikictl-create`, `wikictl-edit`, `wikictl-mcp` (tool-operation skills for a specific CLI/MCP server, same rationale as `developer-github-cli`).

### Steps

1. Create `content/skills/<key>/SKILL.md` Markdown body only, **no frontmatter**
2. (Optional) Add reference docs under `content/skills/<key>/references/`
3. Register it in `content/skills/metadata.yml` with `category`, `subcategory`, and tool blocks:

```yaml
skills:
  developer-example:
    category: engineering # See taxonomy below
    subcategory: coding
    opencode:
      name: developer-example
      description: 'When OpenCode should invoke this skill.'
    claude:
      name: developer-example
      description: 'When Claude should invoke this skill.'
```

4. If the skill body is refreshed from an upstream source, add a `ref:` key to its `metadata.yml` entry pointing at the raw or blob-view SKILL.md URL — see [Updating externally-sourced skills](#updating-externally-sourced-skills).

### Taxonomy

Plain, single-word subcategories on purpose — the previous `-and-`-joined labels (`build-and-quality`, `architecture-and-platform`, …) were vague enough that skills got misfiled into near-synonyms. Grouping is driven by what the skill actually does, not by hitting a target count.

| Category        | Subcategories                    |
| --------------- | ----------------------------------- |
| `engineering`   | `coding`, `architecture`, `operations`, `documentation` |
| `communication` | `content`, `messaging`, `style`  |
| `reasoning`     | `brainstorming`, `research`, `speaking` |
| `tools`         | `cli`                             |
| `meta`          | `creation`, `review`              |
| `coaching`      | `planning`, `support`             |

- `engineering`: `coding` = writing/reviewing code; `architecture` = system/infra design; `operations` = running things in production; `documentation` = decision records and technical docs.
- `communication`: `content` = anything public-facing (brand voice, posts, visual identity — text and image alike); `messaging` = direct 1:1 communication with a specific person (email, stakeholder updates); `style` = response-*style* modifiers, how the assistant talks rather than what it produces. `caveman` is the only current `style` occupant.
- `coaching`: only used by private content today (personal-training skills) but part of the shared vocabulary — `planning` = designing the program (exercise selection, periodization); `support` = sustaining it once running (adherence, recovery, nutrition).
- `tools/cli` is the only subcategory currently in use under `tools`; add a new one only when a skill actually needs it rather than pre-declaring unused buckets.

### Public skill inventory

| Key                               | Category      | Subcategory  |
| --------------------------------- | ------------- | ------------- |
| `developer-python`                | engineering   | coding        |
| `developer-shell`                 | engineering   | coding        |
| `developer-javascript`            | engineering   | coding        |
| `developer-typescript`            | engineering   | coding        |
| `developer-framework-astro`       | engineering   | coding        |
| `developer-go`                    | engineering   | coding        |
| `developer-docker`                | engineering   | coding        |
| `developer-github-actions`        | engineering   | coding        |
| `developer-tdd`                   | engineering   | coding        |
| `developer-diagnosing-bugs`       | engineering   | coding        |
| `developer-microservices-and-api` | engineering   | architecture  |
| `developer-terraform`             | engineering   | architecture  |
| `developer-kubernetes`            | engineering   | architecture  |
| `developer-github-cli`            | tools         | cli           |
| `wikictl`                         | tools         | cli           |
| `wikictl-read`                    | tools         | cli           |
| `wikictl-create`                  | tools         | cli           |
| `wikictl-edit`                    | tools         | cli           |
| `wikictl-mcp`                     | tools         | cli           |
| `caveman`                         | communication | style         |
| `skill-creator`                   | meta          | creation      |
| `agent-creator`                   | meta          | creation      |

**`developer-github-actions` vs `developer-github-cli` split**: deliberately in different categories despite both being "GitHub". `developer-github-actions` is `engineering/coding` — it's about writing and reviewing workflow YAML, a build artifact like any other config file. `developer-github-cli` is `tools/cli` — it's about operating the `gh` CLI itself (issues, PRs, releases), not producing a build artifact. The same distinction places the `wikictl-*` skills in `tools` rather than `engineering`: they operate a specific CLI/MCP server, they don't encode a language or framework convention.

**Why 5 `wikictl-*` skills instead of 1**: every `developer-*` skill is one file per tool/language (`developer-docker`, `developer-kubernetes`, …), but wikictl is split into 5 (`wikictl`, `wikictl-read`, `wikictl-create`, `wikictl-edit`, `wikictl-mcp`). This is deliberate, not an inconsistency to "fix" by merging them: each `wikictl-*` skill is a distinct *workflow* (reading vs. creating vs. editing memory, or the MCP transport specifically) that should trigger independently based on what the agent is actually trying to do, where a `developer-*` skill is one *topic* with internal structure (sections within a single SKILL.md) that all trigger together whenever that tool is in play. `wikictl` itself is the bootstrap/dispatcher skill pointing at the other four.

### SKILL.md rules

- **No YAML frontmatter** in SKILL.md name and description come exclusively from `metadata.yml`
- Body under 500 lines; use `references/` subdirectory for overflow content
- Description in `metadata.yml` should be specific about when to trigger lean "pushy" to avoid under-triggering

## Content Repo Format

Private or supplemental content repos can contain:

```text
your-content-repo/
├── agents/
│   ├── metadata.yml         # per-tool frontmatter
│   └── <key>.md             # agent body (no frontmatter)
├── skills/
│   ├── metadata.yml         # per-tool frontmatter
│   └── <skill-key>/
│       └── SKILL.md         # skill body (no frontmatter)
├── hooks/                   # optional config overrides
│   ├── claude.json          # full replacement for config/claude/hooks.json
│   └── opencode.ts          # full replacement for config/opencode/rtk-plugin.ts
├── mcp.json                 # optional: full replacement for config/mcp.json
├── opencode.json            # optional: full replacement for config/opencode.json
├── paths.yml                # optional: per-tool output paths, merged per-tool-key over the bundled default
└── agents.harness-ai.md     # optional: appended after the bundled agents.harness-ai.md
```

`agents/`, `skills/`, and `agents.harness-ai.md` are what real extensions actually use — see [Extending harness-ai](#extending-harness-ai) below. `hooks/`, `mcp.json`, and `paths.yml` are supported but optional/advanced.

Key rules:

- No frontmatter in `.md` files — frontmatter comes exclusively from `metadata.yml`
- `metadata.yml` must start with a `default:` block followed by an `agents:` or `skills:` key
- Same key in both repos → content repo wins; absent key → falls back to bundled defaults. This is universal across every content type, `paths.yml` included — a content repo's `paths.yml` can override the output path for one tool while the bundled default still applies to any tool it doesn't mention.
- `hooks/` and `mcp.json` are full replacements, not merged with defaults
- `agents.harness-ai.md` is additive: both the bundled and the content-repo copy are appended to the managed AGENTS.md block, not replaced

## Extending harness-ai

`cli.sh init-extension <path> [--name <str>]` scaffolds a new content-repo extension at `<path>`, matching the lean shape a real extension actually uses (`agents/` + `skills/`, each with `metadata.yml` + one placeholder body, plus a starter `agents.harness-ai.md` and `README.md`) — not the full documented format above. It deliberately does not scaffold `hooks/`, `mcp.json`, or `paths.yml`; the generated `README.md` points back here for those.

```bash
cli.sh init-extension ./my-extension --name "My Extension"
cli.sh install --content-repo-local-path ./my-extension   # verify it scaffolds before customizing
```

`--content-repo-local-path` is a `cli.sh install`/`sync` flag for pointing at an already-local content-repo checkout (dev/test), parallel to `--local-path` for harness-ai's own checkout — it skips the clone step in `cmd_install`/`cmd_sync` entirely.

## Config Templates

Files under `config/` are deployed to the workspace based on the active `.harness-ai/config.yaml` `scaffold.*` keys (or the matching CLI flag):

| Source                              | Destination                    | Config key           | Behavior       |
| ------------------------------------ | ------------------------------- | --------------------- | -------------- |
| `config/mcp.json`                   | `.mcp.json`                     | `scaffold.createFileMCP`     | copy-once      |
| `config/claude/hooks.json`          | `.claude/settings.json[hooks]`  | `scaffold.createFileHooks`   | always-managed |
| `config/claude/settings.json`       | `.claude/settings.json`         | `scaffold.createFileSetting` | copy-once      |
| `config/claude/settings.local.json` | `.claude/settings.local.json`   | `scaffold.createFileSetting` | copy-once      |
| `config/claude/statusline.sh`       | `.claude/statusline.sh`         | `scaffold.createFileSetting` | copy-once      |
| `config/opencode/rtk-plugin.ts`     | `.opencode/plugins/rtk.ts`      | `scaffold.createFileHooks`   | always-managed |
| `config/opencode.json`              | `opencode.json`                 | `scaffold.createFileMCP`     | copy-once      |

**copy-once**: file is created on first scaffold run; skipped if destination already exists (preserves user edits).

**always-managed**: file is written on every scaffold run regardless of whether it exists. Hooks are harness-owned — customize them via the content repo override, not by editing the deployed file directly.

### Content repo overrides

A private content repo can override config templates by placing files at these paths:

| Content repo path    | Overrides                       |
| --------------------- | -------------------------------- |
| `mcp.json`           | `config/mcp.json`               |
| `opencode.json`      | `config/opencode.json`          |
| `hooks/claude.json`  | `config/claude/hooks.json`      |
| `hooks/opencode.ts`  | `config/opencode/rtk-plugin.ts` |

## Updating externally-sourced skills

Some bundled skills track an upstream source recorded as a `ref:` key on the skill's entry in `content/skills/metadata.yml`. Two exist today:

| Skill           | `ref:`                                                                                        | URL shape        |
| --------------- | ----------------------------------------------------------------------------------------------- | ----------------- |
| `caveman`       | `https://github.com/JuliusBrussee/caveman`                                                      | raw-fetchable repo root |
| `skill-creator` | `https://github.com/anthropics/skills/blob/main/skills/skill-creator/SKILL.md?plain=1`          | GitHub blob-view URL |

Run `just update-skills` to refresh every skill that declares a `ref:` (or `just update-skills <name>` for one). The recipe normalizes GitHub blob-view URLs (`.../blob/...?plain=1`) to their raw equivalent (`.../raw/...`) so both `ref:` shapes go through the same fetch path, and warns instead of silently skipping a skill whose `ref:` doesn't match either known shape. It never touches `metadata.yml` frontmatter — only the `SKILL.md` body, since frontmatter is generated from `metadata.yml` at scaffold time.

## Local Testing

```bash
just check              # fast static checks: shell syntax, Python parse, YAML validity
just test-all           # check + every recipe below + test-e2e, one command (what CI runs)
just test               # scaffold Claude only into ./test/
just test-opencode      # scaffold OpenCode only
just test-both          # scaffold Claude + OpenCode with hooks
just test-no-defaults   # scaffold with installDefaults=false — expects empty output without a content repo
just test-hooks         # verify hooks override from a simulated private repo
just test-content-repo  # verify private skills from a simulated content repo
just test-idempotent    # run twice — second run must be a no-op
just test-e2e           # config-resolution e2e suite, see below
just update-skills      # refresh all externally-sourced skill bodies (see above)
just clean              # remove ./test/
```

The recipes above call `harness.py` directly (via the `{{uv}}` variable) — useful for iterating on the scaffolder itself, but they bypass `cli.sh` entirely, so they never exercise config resolution (`.harness-ai/config.yaml` vs CLI flags vs built-in defaults).

### `tests/e2e/`: config-resolution suite

`tests/e2e/run.sh` (via `just test-e2e`) runs `cli.sh install --local-path <this checkout>` — the actual entrypoint a real user or the devcontainer invokes — against a matrix of workspace starting states in `tests/e2e/fixtures/`:

| Fixture             | Starting state                          | Proves                                                                 |
| -------------------- | ---------------------------------------- | ----------------------------------------------------------------------- |
| `no-config/`         | no `.harness-ai/config.yaml` at all      | CLI defaults apply, then a starter `config.yaml` is seeded from them   |
| `full-config/`       | every key set, all inverted from defaults | the config file alone drives the run (no flags passed) and is left untouched (copy-once) |
| `partial-config/`    | only one key set (`install.wikictl`)     | that key overrides; every other setting falls through to the CLI's built-in default |
| `malformed-config/`  | invalid YAML                              | `cli.sh` `die()`s with a clear error and scaffolds nothing             |
| `custom-tools/`      | multi-entry `install.custom` map, one entry failing | the delimited-blob bridge (`_read_config` → `_load_config` → `_seed_starter_config`'s fd-3 decode → `_install_custom_tools`) round-trips correctly and warn-and-continues on the failing entry |
| `wikictl-enabled/`   | `install.wikictl: true`                   | wikictl actually installs, resolves on `PATH`, and `wikictl serve` boots and responds on port 9797 — not just that the config flag parsed |

Each fixture is copied into a scratch workspace under `tests/e2e/.scratch/` (gitignored, removed at the end of the run), never mutated in place. Add a new fixture by creating `tests/e2e/fixtures/<name>/.harness-ai/config.yaml` (or leaving it out, for a no-config-style case) and a matching block in `run.sh`.
