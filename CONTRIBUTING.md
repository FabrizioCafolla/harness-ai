# Contributing to harness-ai

This is for people changing harness-ai's own code. If you're consuming harness-ai in a workspace and want to add skills/agents, see [README.md](README.md) (usage) and [AGENTS.md](AGENTS.md) (mechanical steps: adding an agent, adding a skill, content-repo format, `init-extension`).

## What harness-ai is

An agnostic project-setup tool for agentic development, extensible via your own harness. "Agnostic" means it doesn't encode any one person's or team's opinions into the bundled content — the public `content/` tree is generic developer/build conventions (`developer-*` skills, taxonomy, config plumbing). "Extensible via your own harness" means the actual point of the tool is the content-repo merge: you're expected to point it at your own agents/skills (private or public) and have them merge cleanly on top, not to fork this repo to add your own opinions to it. `init-extension` exists because bootstrapping that extension repo by hand was real friction worth removing.

Concretely, that positioning constrains what belongs in this repo versus a content repo:

- Bundled `content/` skills should be broadly applicable engineering practice (a language convention, a tool's usage pattern), not one person's workflow or voice.
- New `install.*` toggles are for genuinely common tools worth a first-class flag; anything narrower belongs in `install.custom` (a workspace's own config, not a new toggle here).
- Web UI and CLI behavior in `wikictl/` should stay generically useful — it's shipped as part of the harness, not tailored to one deployment.

## Dev Setup

Requires bash, Python 3.9+, and `uv` (for `wikictl/`'s own test suite and for exercising `install.headroom`/`install.wikictl` locally). No build step — `cli.sh`, `harness.py`, and `content/` are used directly from a checkout via `--local-path`.

```bash
git clone https://github.com/FabrizioCafolla/harness-ai.git
cd harness-ai
bash cli.sh install --local-path "$(pwd)" --workspace /tmp/test-workspace
```

### Which `just test-*` recipe, and when

All of these call `harness.py` directly — they bypass `cli.sh`, so they're fast, but they don't exercise config resolution (`.harness-ai/config.yaml` vs CLI flags vs built-in defaults). Reach for `just test-e2e` (below) when the change touches that layer.

| Recipe                 | Reach for it when…                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| `just test`             | You changed anything in `content/` or `config/claude/` and want the fast, default-path sanity check.   |
| `just test-opencode`    | You changed anything OpenCode-specific (`content/paths.yml`'s `opencode:` block, `config/opencode/`).   |
| `just test-both`        | You changed hook merging or anything that behaves differently with multiple tools active at once.       |
| `just test-no-defaults` | You changed the `installDefaults` gate itself, or want to confirm a change doesn't leak bundled content when it's off. |
| `just test-idempotent`  | You changed the content-hash / lock-file logic (`_compute_content_hash`, `_read_lock`/`_write_lock`), or anything that runs on every scaffold pass and must stay a no-op on a second run with no changes. |
| `just test-hooks`       | You changed hook precedence or the `hooks/claude.json` / `hooks/opencode.ts` content-repo override paths. |
| `just test-content-repo`| You changed `_load_content`'s merge logic (agents/skills metadata, or now `paths.yml` — see `harness.py`'s `_load_content`) or anything about how a content repo's skills/agents show up in output. |
| `just test-e2e`         | You changed `cli.sh` itself: config resolution, install gating, PATH handling, `init-extension`, or anything a real `install`/`sync` invocation exercises that the recipes above don't (they call `harness.py` directly, not `cli.sh`). |
| `just update-skills`    | You're refreshing a bundled skill that tracks an upstream `ref:` (currently `caveman`, `skill-creator`) — not a general-purpose recipe to run on every change. |

Before opening a PR that touches `cli.sh`, `harness.py`, or `content/`, run the full local suite:

```bash
just test-all   # static checks + every scaffold recipe + the e2e suite
```

CI (`.github/workflows/test.yml`) runs the same `just test-all` plus wikictl's pytest on every PR, so a green local run means a green pipeline.

Do not chain the individual recipes on one command line (`just test test-opencode ...`): `just` runs a shared dependency once per invocation, so the `clean` step every recipe depends on fires only for the first one — later recipes silently reuse the previous workspace and skip via the content-hash lock. `test-all` sidesteps this by launching each recipe as its own `just` sub-invocation.

If the change touches `wikictl/`, also run its own suite (separate from the recipes above — `wikictl/` is a standalone package with its own tests):

```bash
cd wikictl && uv run --extra dev --extra serve pytest
```

## Contribution Workflow

For anything beyond an obviously-correct, single-file fix (typo, comment, a one-line bug fix with no behavior ambiguity): write an OpenSpec change proposal before implementing — proposal (why / what changes), design (decisions and trade-offs, especially anything that touches existing behavior or introduces a new config surface), specs (requirements as scenarios), and tasks (the implementation checklist). This repo doesn't carry its own `openspec/` directory; if you're working from a wrapper workspace that has OpenSpec tooling installed, use it there. If not, a proposal doc in the PR description covering the same four questions (why, what, trade-offs, task breakdown) serves the same purpose — the point is thinking through the design and getting it reviewed before code, not the specific tool.

Small fixes can skip straight to a PR. When in doubt about which bucket a change falls into, treat it as needing a proposal — the cost of a skipped one-file proposal is low; the cost of an unreviewed design decision baked into merged code is not.

**Test expectations:** every PR that changes behavior needs the relevant test(s) from [Dev Setup](#dev-setup) passing, plus a new test if the change adds behavior not already covered (a new `install.*` toggle, a new e2e fixture, a new wikictl web-UI feature). PRs that only change bundled skill/agent *content* (not scaffolding logic) don't need new automated tests, but should be scaffolded once locally (`just test`) to confirm the YAML/Markdown is well-formed.

For the mechanical steps of adding a skill or agent, the content-repo format, and the skill-naming taxonomy, see [AGENTS.md](AGENTS.md) — this document is about how to work on harness-ai's own code, not about extending it from a consuming workspace.
