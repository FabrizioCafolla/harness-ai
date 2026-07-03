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

# Run scaffold twice — second run must be a no-op (hash unchanged)
test-idempotent: clean
    @echo "==> First run..."
    mkdir -p {{workspace}}
    {{uv}} --workspace {{workspace}} --tools claude --install-defaults true
    @echo ""
    @echo "==> Second run (should skip)..."
    {{uv}} --workspace {{workspace}} --tools claude --install-defaults true

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
        --content-repo-local-path /tmp/harness-test-private
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
        --content-repo-local-path /tmp/harness-test-content
    @echo "==> Verifying private skill installed..."
    test -f {{workspace}}/.claude/skills/my-private-skill/SKILL.md \
        && echo "  [OK] private skill installed" \
        || { echo "  [FAIL] private skill NOT installed"; exit 1; }
    rm -rf /tmp/harness-test-content

# Remove test workspace
clean:
    @echo "==> Removing test workspace..."
    rm -rf {{workspace}}

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
