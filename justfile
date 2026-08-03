workspace := "test"
uv       := "uv run --with pyyaml harness.py"

# List available recipes
default:
    @just --list

# Fast static checks: shell syntax, Python parse, YAML validity
check:
    bash -n cli.sh
    bash -n install.sh
    bash -n tests/e2e/run.sh
    python3 -c "import ast; ast.parse(open('harness.py').read())"
    uv run --with pyyaml python3 -c "import yaml, glob; [yaml.safe_load(open(f)) for f in ['content/paths.yml', 'content/skills/metadata.yml', 'content/agents/metadata.yml', 'config/config.default.yaml']]"
    @echo "check: OK"

# Full local suite, one command. Each recipe runs as its own `just` invocation
# on purpose: chaining them on one command line (`just test test-opencode ...`)
# dedupes the shared `clean` dependency to a single run, so later recipes
# silently reuse the previous workspace and skip via the content-hash lock.
test-all: check
    just test
    just test-opencode
    just test-both
    just test-no-defaults
    just test-idempotent
    just test-hooks
    just test-content-repo
    just test-symlinks
    just test-local-source
    just test-local-source-migration-safety
    just test-category-filter
    just test-workspace-source
    just test-foreign-entry
    just test-e2e
    just clean
    @echo "test-all: OK"

# Scaffold Claude only — mirrors devcontainer default
test: clean
    @echo "==> Creating test workspace: {{workspace}}/"
    mkdir -p {{workspace}}
    @echo "==> Running scaffold (tools: claude)..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp true \
        --create-file-hooks true \
        --create-file-setting true \
        --update-gitignore true \
        --install-defaults true

# Scaffold OpenCode only
test-opencode: clean
    @echo "==> Running scaffold (tools: opencode)..."
    mkdir -p {{workspace}}
    {{uv}} \
        --workspace {{workspace}} \
        --tools opencode \
        --create-file-mcp true \
        --create-file-hooks true \
        --create-file-setting false \
        --update-gitignore true \
        --install-defaults true

# Scaffold Claude + OpenCode with hooks
test-both: clean
    @echo "==> Running scaffold (tools: claude,opencode + hooks)..."
    mkdir -p {{workspace}}
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude,opencode \
        --create-file-mcp true \
        --create-file-hooks true \
        --create-file-setting true \
        --update-gitignore true \
        --install-defaults true

# Scaffold with installDefaults=false — expects empty output without a content repo
test-no-defaults: clean
    @echo "==> Running scaffold (no defaults, no content repo)..."
    mkdir -p {{workspace}}
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults false

# Run scaffold twice — second run must be a no-op (hash unchanged: same
# manifest.json, no symlinks recreated, no report reprinted with different
# numbers — the second invocation should print only the "no changes
# detected" line and return immediately).
test-idempotent: clean
    @echo "==> First run..."
    mkdir -p {{workspace}}
    {{uv}} --workspace {{workspace}} --tools claude --install-defaults true
    cp {{workspace}}/.harness-ai/manifest.json {{workspace}}-manifest-before.json
    @echo ""
    @echo "==> Second run (should skip)..."
    {{uv}} --workspace {{workspace}} --tools claude --install-defaults true | tee {{workspace}}-run2.log
    grep -q "no changes detected" {{workspace}}-run2.log \
        && echo "  [OK] second run short-circuited on the unchanged lock hash" \
        || { echo "  [FAIL] second run did not report 'no changes detected'"; exit 1; }
    cmp -s {{workspace}}-manifest-before.json {{workspace}}/.harness-ai/manifest.json \
        && echo "  [OK] manifest.json unchanged by the no-op run" \
        || { echo "  [FAIL] manifest.json changed on a no-op run"; exit 1; }
    rm -f {{workspace}}-run2.log {{workspace}}-manifest-before.json

# Verify hooks override from a simulated private content repo
test-hooks: clean
    @echo "==> Setting up simulated private repo with hooks override..."
    mkdir -p {{workspace}} /tmp/harness-test-private/hooks
    echo '{"PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "echo pre-tool-use-from-private"}]}], "PostToolUse": [], "UserPromptSubmit": [], "Stop": [], "Notification": []}' \
        > /tmp/harness-test-private/hooks/claude.json
    echo '// session-start-from-private (test marker)' \
        > /tmp/harness-test-private/hooks/opencode.ts
    @echo "==> Running scaffold with private content repo..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude,opencode \
        --create-file-mcp true \
        --create-file-hooks true \
        --create-file-setting true \
        --update-gitignore true \
        --install-defaults true \
        --content-repos harness-test-private=/tmp/harness-test-private
    @echo "==> Verifying private hooks applied..."
    grep -q "pre-tool-use-from-private" {{workspace}}/.claude/settings.json \
        && echo "  [OK] Claude hooks: private override applied" \
        || { echo "  [FAIL] Claude hooks: private override NOT applied"; exit 1; }
    grep -q "session-start-from-private" {{workspace}}/.opencode/plugins/rtk.ts \
        && echo "  [OK] OpenCode hooks: private override applied" \
        || { echo "  [FAIL] OpenCode hooks: private override NOT applied"; exit 1; }
    rm -rf /tmp/harness-test-private

# Scaffold with a simulated local content repo (private skills + hooks)
test-content-repo: clean
    @echo "==> Setting up simulated content repo..."
    mkdir -p /tmp/harness-test-content/agents \
              /tmp/harness-test-content/skills/my-private-skill \
              /tmp/harness-test-content/hooks
    printf 'default:\n  claude:\n  opencode:\n\nagents:\n' \
        > /tmp/harness-test-content/agents/metadata.yml
    printf 'default:\n  claude:\n  opencode:\n\nskills:\n  my-private-skill:\n    category: engineering\n    subcategory: build-and-quality\n    claude:\n      name: my-private-skill\n      description: Test private skill\n    opencode:\n      name: my-private-skill\n      description: Test private skill\n' \
        > /tmp/harness-test-content/skills/metadata.yml
    printf '# My Private Skill\nThis is a test private skill.' \
        > /tmp/harness-test-content/skills/my-private-skill/SKILL.md
    @echo "==> Running scaffold with content repo..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp true \
        --create-file-hooks true \
        --create-file-setting true \
        --update-gitignore true \
        --install-defaults true \
        --content-repos harness-test-content=/tmp/harness-test-content
    @echo "==> Verifying private skill installed..."
    test -f {{workspace}}/.claude/skills/my-private-skill/SKILL.md \
        && echo "  [OK] private skill installed" \
        || { echo "  [FAIL] private skill NOT installed"; exit 1; }
    test -L {{workspace}}/.claude/skills/my-private-skill/SKILL.md \
        && echo "  [OK] private skill is a symlink into the canonical store" \
        || { echo "  [FAIL] private skill SKILL.md is not a symlink"; exit 1; }
    readlink {{workspace}}/.claude/skills/my-private-skill/SKILL.md | grep -q "harness-ai/skills/harness-test-content/my-private-skill" \
        && echo "  [OK] symlink resolves into .harness-ai/skills/harness-test-content/" \
        || { echo "  [FAIL] symlink does not point into the named content-repo source's canonical store"; exit 1; }
    rm -rf /tmp/harness-test-content

# Verify default/content-repo skills render into the canonical store and
# .claude/.opencode/.agents are symlinks into it (not independent copies),
# and that .agents renders even though 'agents' isn't in --tools (D1/D4).
test-symlinks: clean
    @echo "==> Running scaffold (tools: claude)..."
    mkdir -p {{workspace}}
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true
    @echo "==> Verifying canonical-store symlinks..."
    test -L {{workspace}}/.claude/skills/caveman/SKILL.md \
        && echo "  [OK] .claude/skills/caveman/SKILL.md is a symlink" \
        || { echo "  [FAIL] .claude/skills/caveman/SKILL.md is not a symlink"; exit 1; }
    readlink {{workspace}}/.claude/skills/caveman/SKILL.md | grep -q "harness-ai/skills/default/caveman/claude.SKILL.md" \
        && echo "  [OK] symlink resolves into .harness-ai/skills/default/caveman/" \
        || { echo "  [FAIL] symlink does not point into the canonical store"; exit 1; }
    test -L {{workspace}}/.agents/skills/caveman/SKILL.md \
        && echo "  [OK] .agents/skills/caveman/SKILL.md exists as a symlink (agents wasn't in --tools)" \
        || { echo "  [FAIL] .agents/skills/caveman/SKILL.md missing or not a symlink"; exit 1; }

# Formalizes the `local` source: a hand-authored
# .harness-ai/skills/local/<key>/SKILL.md file (inline frontmatter, no
# metadata.yml) is discovered and symlinked into every active tool dir,
# `.agents` included, never rendered/copied (design.md D1/D2/D3 of
# harness-ai-local-canonical-store). Regression-tests the idempotent
# second-run behavior: a bug there would make harness-ai double-count or loop
# on its own prior symlink output.
test-local-source: clean
    @echo "==> Seeding a hand-authored local skill (canonical store: .harness-ai/skills/local/)..."
    mkdir -p {{workspace}}/.harness-ai/skills/local/example
    printf -- '---\nname: example\ndescription: Test local skill.\n---\n\nLocal skill body.\n' \
        > {{workspace}}/.harness-ai/skills/local/example/SKILL.md
    @echo "==> First run..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run1.log
    test -L {{workspace}}/.claude/skills/example \
        && echo "  [OK] .claude/skills/example symlinked to the local source" \
        || { echo "  [FAIL] .claude/skills/example is not a symlink"; exit 1; }
    readlink {{workspace}}/.claude/skills/example | grep -q '.harness-ai/skills/local/example' \
        && echo "  [OK] symlink points at .harness-ai/skills/local/example" \
        || { echo "  [FAIL] symlink target unexpected"; exit 1; }
    # Core behavior change from the pre-1.0 layout (design.md D3): `.agents` is
    # now a pure render target for `local` too, no more same-path exception —
    # previously this test asserted the opposite (that `.agents/skills` was
    # the source, not a link target).
    test -L {{workspace}}/.agents/skills/example \
        && echo "  [OK] .agents/skills/example is ALSO a symlink now (no more agents-profile exception for local)" \
        || { echo "  [FAIL] CRITICAL: .agents/skills/example is not a symlink — agents-profile exception regressed"; exit 1; }
    readlink {{workspace}}/.agents/skills/example | grep -q '.harness-ai/skills/local/example' \
        && echo "  [OK] .agents symlink also points at .harness-ai/skills/local/example" \
        || { echo "  [FAIL] .agents symlink target unexpected"; exit 1; }
    grep -qE 'claude +local +skill +1 +1' {{workspace}}-run1.log \
        && echo "  [OK] sync summary counts local: seen=1 linked=1 (claude)" \
        || { echo "  [FAIL] sync summary did not show local seen=1 linked=1 for claude"; exit 1; }
    grep -qE 'agents +local +skill +1 +1' {{workspace}}-run1.log \
        && echo "  [OK] sync summary counts local: seen=1 linked=1 (agents)" \
        || { echo "  [FAIL] sync summary did not show local seen=1 linked=1 for agents"; exit 1; }
    @echo "==> Second run (forced, no changes) — must not double-count or loop..."
    rm -f {{workspace}}/.harness-ai/lock
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run2.log
    grep -qE 'claude +local +skill +1 +1' {{workspace}}-run2.log \
        && echo "  [OK] second run: local count still seen=1 linked=1" \
        || { echo "  [FAIL] second run local count changed"; exit 1; }
    # Regression (design.md D6a refinement, found via real-workspace testing):
    # the per-tool cleanup call runs before the local-linking pass and, on an
    # early version of that fix, always saw an empty "local" preview at that
    # point — misdiagnosing every still-valid local key as stale and
    # unlinking+relinking it on every single run. Harmless to final state
    # (local's own pass immediately recreates the symlink) but wasteful churn
    # and a misleading "removed" count in the sync report, forever, on every
    # run, for every local skill — not caught by the seen/linked-only regex
    # above, which doesn't look at the removed column at all.
    grep -qE 'claude +local +skill +1 +1 +0' {{workspace}}-run2.log \
        && echo "  [OK] second run: removed=0 for local (no spurious unlink+relink churn)" \
        || { echo "  [FAIL] CRITICAL: local skill was spuriously removed+recreated on an unchanged second run"; exit 1; }
    @echo "==> Removing the local skill by hand — third run must clean up only the dangling symlinks..."
    rm -rf {{workspace}}/.harness-ai/skills/local/example
    rm -f {{workspace}}/.harness-ai/lock
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true
    test ! -e {{workspace}}/.claude/skills/example \
        && echo "  [OK] dangling .claude/skills/example symlink removed" \
        || { echo "  [FAIL] .claude/skills/example still present"; exit 1; }
    test ! -e {{workspace}}/.agents/skills/example \
        && echo "  [OK] dangling .agents/skills/example symlink removed too" \
        || { echo "  [FAIL] .agents/skills/example still present"; exit 1; }
    @echo "==> Regression: skills.exclude.keys on a local skill must remove only the tool-dir symlinks, never the real .harness-ai/skills/local source..."
    mkdir -p {{workspace}}/.harness-ai/skills/local/example2
    printf -- '---\nname: example2\ndescription: Test local skill.\n---\n\nLocal skill body.\n' \
        > {{workspace}}/.harness-ai/skills/local/example2/SKILL.md
    rm -f {{workspace}}/.harness-ai/lock
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true
    test -f {{workspace}}/.harness-ai/skills/local/example2/SKILL.md \
        && echo "  [OK] real source file present before exclusion" \
        || { echo "  [FAIL] setup failed: example2 source missing"; exit 1; }
    rm -f {{workspace}}/.harness-ai/lock
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        --skills-exclude-keys example2
    test -f {{workspace}}/.harness-ai/skills/local/example2/SKILL.md \
        && echo "  [OK] real .harness-ai/skills/local/example2 source file SURVIVED exclusion (not deleted)" \
        || { echo "  [FAIL] CRITICAL: skills.exclude.keys deleted the user's real local skill file"; exit 1; }
    test ! -e {{workspace}}/.claude/skills/example2 \
        && echo "  [OK] only the dangling .claude/skills/example2 symlink was removed" \
        || { echo "  [FAIL] .claude/skills/example2 symlink was not removed"; exit 1; }
    rm -f {{workspace}}-run1.log {{workspace}}-run2.log

# Migration safety (design.md D4 of harness-ai-local-canonical-store): an
# unmigrated pre-1.0 workspace still has a real .agents/skills/<key>/SKILL.md
# file at the old `local` location. Establishing the new symlink there must be
# blocked by the foreign-entry-safety guard, not silently clobbered, so the
# workspace maintainer gets a clear [foreign] signal to run the `mv` by hand.
test-local-source-migration-safety: clean
    @echo "==> Simulating an unmigrated workspace: old-shape real file + new-shape source both present..."
    mkdir -p {{workspace}}/.agents/skills/example {{workspace}}/.harness-ai/skills/local/example
    printf '# Not harness-ai\nOLD-SHAPE-REAL-FILE-MARKER\n' > {{workspace}}/.agents/skills/example/SKILL.md
    printf -- '---\nname: example\ndescription: Test local skill.\n---\n\nLocal skill body.\n' \
        > {{workspace}}/.harness-ai/skills/local/example/SKILL.md
    @echo "==> Running scaffold (tools: claude)..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run1.log
    grep -q "OLD-SHAPE-REAL-FILE-MARKER" {{workspace}}/.agents/skills/example/SKILL.md \
        && echo "  [OK] old-shape real file left byte-for-byte untouched" \
        || { echo "  [FAIL] CRITICAL: old-shape file was overwritten"; exit 1; }
    test ! -L {{workspace}}/.agents/skills/example \
        && echo "  [OK] .agents/skills/example is still a real dir, not a symlink" \
        || { echo "  [FAIL] CRITICAL: .agents/skills/example became a symlink over the unmigrated file"; exit 1; }
    grep -q "\[foreign\] skill 'example' (agents, source: local)" {{workspace}}-run1.log \
        && echo "  [OK] blocked migration reported inline with a [foreign] line" \
        || { echo "  [FAIL] no [foreign] line printed for the blocked local migration"; exit 1; }
    grep -q "unmanaged entries" {{workspace}}-run1.log \
        && echo "  [OK] unmanaged section printed" \
        || { echo "  [FAIL] unmanaged section missing"; exit 1; }
    rm -f {{workspace}}-run1.log

# Verify category/subcategory/key include+exclude filtering (skills only,
# design.md D5): restrict to one category, then carve one key out of it.
test-category-filter: clean
    @echo "==> Running scaffold (skills.include.categories=meta, exclude.keys=agent-creator)..."
    mkdir -p {{workspace}}
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        --skills-include-categories meta \
        --skills-exclude-keys agent-creator
    @echo "==> Verifying filter..."
    test -d {{workspace}}/.claude/skills/skill-creator \
        && echo "  [OK] skill-creator present (category: meta, included)" \
        || { echo "  [FAIL] skill-creator missing"; exit 1; }
    test ! -e {{workspace}}/.claude/skills/agent-creator \
        && echo "  [OK] agent-creator absent (excluded by key from an otherwise-included category)" \
        || { echo "  [FAIL] agent-creator present, should have been excluded"; exit 1; }
    test ! -e {{workspace}}/.claude/skills/caveman \
        && echo "  [OK] caveman absent (category: communication, not included)" \
        || { echo "  [FAIL] caveman present, should have been filtered out by category"; exit 1; }

# Auto-detected `workspace` source from .harness-ai/local/ (design.md
# D1-D4): repo-shaped, no config entry. Proves the full precedence chain —
# workspace overrides default, but a real `local` (.harness-ai/skills/local/)
# entry still overrides workspace (D2 unchanged).
test-workspace-source: clean
    @echo "==> Seeding .harness-ai/local/ overriding the bundled 'agent-creator' skill..."
    mkdir -p {{workspace}}/.harness-ai/local/skills/agent-creator {{workspace}}/.harness-ai/local/agents
    printf 'default:\n  claude:\n  opencode:\n\nagents:\n' \
        > {{workspace}}/.harness-ai/local/agents/metadata.yml
    printf 'default:\n  claude:\n  opencode:\n\nskills:\n  agent-creator:\n    category: meta\n    subcategory: creation\n    claude:\n      name: agent-creator\n      description: Workspace override of agent-creator.\n    opencode:\n      name: agent-creator\n      description: Workspace override of agent-creator.\n' \
        > {{workspace}}/.harness-ai/local/skills/metadata.yml
    printf '# Agent Creator (workspace override)\nWORKSPACE-OVERRIDE-BODY-MARKER\n' \
        > {{workspace}}/.harness-ai/local/skills/agent-creator/SKILL.md
    @echo "==> Running scaffold (tools: claude, defaults on)..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run1.log
    grep -qE 'claude +workspace' {{workspace}}-run1.log \
        && echo "  [OK] sync summary includes a 'workspace' source row" \
        || { echo "  [FAIL] sync summary has no 'workspace' row"; exit 1; }
    readlink {{workspace}}/.claude/skills/agent-creator/SKILL.md | grep -q "harness-ai/skills/workspace/agent-creator" \
        && echo "  [OK] agent-creator symlinks into the workspace source's canonical store (won over default)" \
        || { echo "  [FAIL] agent-creator did not resolve to the workspace source"; exit 1; }
    grep -q "WORKSPACE-OVERRIDE-BODY-MARKER" {{workspace}}/.harness-ai/skills/workspace/agent-creator/claude.SKILL.md \
        && echo "  [OK] canonical store holds the workspace-authored body" \
        || { echo "  [FAIL] canonical store does not hold the workspace body"; exit 1; }
    @echo "==> Baseline: --check-only must report up-to-date right after the run above, before any edit..."
    {{uv}} --workspace {{workspace}} --check-only \
        && echo "  [OK] --check-only reports up-to-date with nothing changed (proves the next assertion isn't vacuously always-stale)" \
        || { echo "  [FAIL] --check-only reported stale with nothing changed"; exit 1; }
    @echo "==> Editing the workspace skill body WITHOUT touching the lock file — --check-only must detect it as stale..."
    # Regression test for design.md D2a: .harness-ai/local/ is a plain
    # subdirectory of the consuming workspace's own repo, not an independent
    # git checkout, so change detection must hash its actual content — not
    # rely on git rev-parse HEAD (which wouldn't move on an uncommitted edit)
    # or on a precomputed SHA (there is none to precompute). This must hold
    # for --check-only specifically, since that's the fast path `harnessai
    # sync` actually uses on every container start — not just the full
    # scaffold path exercised by the rest of this recipe.
    printf '# Agent Creator (workspace override)\nWORKSPACE-OVERRIDE-BODY-MARKER-V2\n' \
        > {{workspace}}/.harness-ai/local/skills/agent-creator/SKILL.md
    ! {{uv}} --workspace {{workspace}} --check-only \
        && echo "  [OK] --check-only correctly reports stale after editing workspace-source content (no lock touched)" \
        || { echo "  [FAIL] CRITICAL: --check-only did not detect the workspace-source content edit"; exit 1; }
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true
    grep -q "WORKSPACE-OVERRIDE-BODY-MARKER-V2" {{workspace}}/.harness-ai/skills/workspace/agent-creator/claude.SKILL.md \
        && echo "  [OK] the edited body was actually picked up by the real run" \
        || { echo "  [FAIL] edited workspace body was not materialized"; exit 1; }
    @echo "==> Adding a real 'local' (.harness-ai/skills/local/) entry for the same key — local must still win over workspace..."
    # No need to touch .agents/skills/agent-creator by hand first: it's
    # currently a symlink into workspace's canonical store, and the normal
    # cleanup-then-local-linking pass removes that stale symlink and recreates
    # it pointing at the local target on its own — same as any other same-key
    # source migration (design.md D6a).
    mkdir -p {{workspace}}/.harness-ai/skills/local/agent-creator
    printf -- '---\nname: agent-creator\ndescription: Local override of agent-creator.\n---\n\nLOCAL-OVERRIDE-BODY-MARKER\n' \
        > {{workspace}}/.harness-ai/skills/local/agent-creator/SKILL.md
    rm -f {{workspace}}/.harness-ai/lock
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run2.log
    grep -q "\[collision\] skill 'agent-creator' claimed by local — skipping render from 'workspace'" {{workspace}}-run2.log \
        && echo "  [OK] collision report: local skipped workspace's render, as designed" \
        || { echo "  [FAIL] expected collision line not found"; exit 1; }
    readlink {{workspace}}/.claude/skills/agent-creator | grep -q '.harness-ai/skills/local/agent-creator' \
        && echo "  [OK] agent-creator now symlinks to the real local source (local beats workspace)" \
        || { echo "  [FAIL] agent-creator did not resolve to the local source"; exit 1; }
    readlink {{workspace}}/.agents/skills/agent-creator | grep -q '.harness-ai/skills/local/agent-creator' \
        && echo "  [OK] .agents/skills/agent-creator also re-pointed to the local source (agents profile no longer exempt)" \
        || { echo "  [FAIL] .agents/skills/agent-creator did not resolve to the local source"; exit 1; }
    rm -f {{workspace}}-run1.log {{workspace}}-run2.log

# Foreign-entry safety (design.md D5/D6): a real, non-symlink file harness-ai
# never created must never be overwritten/deleted, must be reported inline
# when a render would have clobbered it, and must appear in the end-of-run
# "unmanaged" list whether or not a collision was attempted this run.
test-foreign-entry: clean
    @echo "==> Pre-seeding a foreign (hand-placed) SKILL.md at a key 'default' also defines..."
    mkdir -p {{workspace}}/.claude/skills/agent-creator {{workspace}}/.claude/skills/my-scratch-skill
    printf '# Not harness-ai\nFOREIGN-BODY-MARKER\n' > {{workspace}}/.claude/skills/agent-creator/SKILL.md
    printf '# Scratch\nUnrelated to any source.\n' > {{workspace}}/.claude/skills/my-scratch-skill/SKILL.md
    @echo "==> Running scaffold (tools: claude, defaults on)..."
    {{uv}} \
        --workspace {{workspace}} \
        --tools claude \
        --create-file-mcp false \
        --create-file-hooks false \
        --create-file-setting false \
        --update-gitignore false \
        --install-defaults true \
        | tee {{workspace}}-run1.log
    grep -q "FOREIGN-BODY-MARKER" {{workspace}}/.claude/skills/agent-creator/SKILL.md \
        && echo "  [OK] foreign SKILL.md left byte-for-byte untouched" \
        || { echo "  [FAIL] CRITICAL: foreign content was overwritten"; exit 1; }
    test ! -L {{workspace}}/.claude/skills/agent-creator/SKILL.md \
        && echo "  [OK] agent-creator/SKILL.md is still a real file, not a symlink" \
        || { echo "  [FAIL] agent-creator/SKILL.md became a symlink"; exit 1; }
    grep -q "\[foreign\] skill 'agent-creator'" {{workspace}}-run1.log \
        && echo "  [OK] blocked render reported inline with a [foreign] line" \
        || { echo "  [FAIL] no [foreign] line printed for the blocked render"; exit 1; }
    grep -qE 'claude +default.*[1-9][0-9]*$' {{workspace}}-run1.log \
        && echo "  [OK] summary table's foreign column is nonzero for (claude, default)" \
        || { echo "  [FAIL] summary table foreign column did not reflect the blocked render"; exit 1; }
    grep -q "unmanaged entries" {{workspace}}-run1.log \
        && echo "  [OK] unmanaged section printed" \
        || { echo "  [FAIL] unmanaged section missing"; exit 1; }
    grep -q ".claude/skills/agent-creator" {{workspace}}-run1.log \
        && echo "  [OK] blocked key listed in the unmanaged section" \
        || { echo "  [FAIL] blocked key not listed as unmanaged"; exit 1; }
    grep -q ".claude/skills/my-scratch-skill" {{workspace}}-run1.log \
        && echo "  [OK] unrelated scratch entry listed in the unmanaged section (no collision needed to be flagged)" \
        || { echo "  [FAIL] unrelated scratch entry not listed as unmanaged"; exit 1; }
    test -f {{workspace}}/.claude/skills/my-scratch-skill/SKILL.md \
        && echo "  [OK] unrelated scratch entry left on disk" \
        || { echo "  [FAIL] unrelated scratch entry was removed"; exit 1; }
    rm -f {{workspace}}-run1.log

# Remove test workspace
clean:
    @echo "==> Removing test workspace..."
    rm -rf {{workspace}} {{workspace}}-*.log {{workspace}}-*.json

# Config-resolution e2e suite: exercises cli.sh install (not harness.py
# directly) against the fixture matrix under tests/e2e/fixtures/ (no-config,
# full-config, partial-config, malformed-config, custom-tools, wikictl-enabled)
# — see tests/e2e/run.sh for details.
test-e2e:
    @bash tests/e2e/run.sh

# Refresh bundled skill bodies from their upstream ref: in content/skills/metadata.yml.
# NAME limits the refresh to one skill; omit it to refresh every skill with a ref:.
# Handles both a direct raw-file URL and a GitHub blob-view URL (.../blob/...?plain=1),
# normalizing the latter to raw.githubusercontent.com. Warns (does not skip silently)
# on a ref: shape it doesn't recognize. Frontmatter, if present upstream, is stripped —
# harness.py generates it from metadata.yml.
update-skills NAME="":
    #!/usr/bin/env bash
    set -euo pipefail
    refs=$(uv run --with pyyaml python3 -c '
    import sys, yaml

    name_filter = sys.argv[1] if len(sys.argv) > 1 else ""
    data = yaml.safe_load(open("content/skills/metadata.yml")) or {}

    for key, skill in (data.get("skills") or {}).items():
        if name_filter and key != name_filter:
            continue
        for tool in ("claude", "opencode"):
            ref = ((skill.get(tool) or {}).get("metadata") or {}).get("ref")
            if ref:
                print(f"{key}\t{ref}")
                break
    ' "{{NAME}}")

    if [[ -z "${refs}" ]]; then
        if [[ -n "{{NAME}}" ]]; then
            echo "[ERROR] No skill named '{{NAME}}' declares a ref: in content/skills/metadata.yml"
            exit 1
        fi
        echo "[WARN] No skills declare a ref: in content/skills/metadata.yml"
        exit 0
    fi

    while IFS=$'\t' read -r key ref; do
        raw_url=""
        if [[ "${ref}" =~ ^https://github\.com/([^/]+)/([^/]+)/blob/([^?]+) ]]; then
            raw_url="https://raw.githubusercontent.com/${BASH_REMATCH[1]}/${BASH_REMATCH[2]}/${BASH_REMATCH[3]}"
        elif [[ "${ref}" =~ ^https://raw\.githubusercontent\.com/.+\.[A-Za-z0-9]+$ ]]; then
            raw_url="${ref}"
        else
            echo "[WARN] ${key}: ref '${ref}' doesn't match a known shape (raw file URL or GitHub blob URL) — skipping, fix manually"
            continue
        fi

        dest="content/skills/${key}/SKILL.md"
        echo "==> Fetching ${key} from ${raw_url}..."
        curl -fsSL "${raw_url}" \
            | awk 'NR==1 && $0=="---"{fm=1; next} fm==1 && $0=="---"{fm=2; next} fm==1{next} {print}' \
            | sed '/./,$!d' > "${dest}.tmp"

        if [[ ! -s "${dest}.tmp" ]]; then
            echo "[ERROR] Downloaded skill body for ${key} is empty, check upstream layout"
            rm -f "${dest}.tmp"
            exit 1
        fi
        mv "${dest}.tmp" "${dest}"
        echo "==> Updated ${dest}"
        git diff --stat -- "${dest}" || true
    done <<< "${refs}"
