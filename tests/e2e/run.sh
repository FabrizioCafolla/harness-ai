#!/usr/bin/env bash
# =============================================================================
# harness-ai e2e config-resolution tests.
#
# Exercises cli.sh install exactly as a real user would invoke it (via
# --local-path against this checkout — never harness.py directly), against a
# matrix of workspace starting states under fixtures/:
#
#   no-config/        no .harness-ai/config.yaml at all -> CLI defaults apply,
#                      then a starter config.yaml is seeded from them
#   full-config/      every key set, all inverted from the CLI defaults ->
#                      the config file alone must drive the run (no flags
#                      passed) and must be left untouched (copy-once)
#   partial-config/   only one key set -> that key overrides, every other
#                      setting falls through to the CLI's built-in default
#   malformed-config/ invalid YAML -> cli.sh must die() with a clear error
#                      and must not scaffold anything
#   custom-tools/     multi-entry install.custom map, one entry failing ->
#                      the delimited-blob bridge round-trips and the failing
#                      entry warns without aborting the run
#   wikictl-enabled/  install.wikictl: true -> wikictl actually installs,
#                      resolves on PATH, and serves on port 9797
#
# This is the "cli.sh can start from a project with no config (defaults) or
# load whatever config it finds at the established path and act accordingly"
# contract, checked end to end rather than by reading the code.
# =============================================================================
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FIXTURES_DIR="${REPO_DIR}/tests/e2e/fixtures"
SCRATCH_ROOT="${REPO_DIR}/tests/e2e/.scratch"

PASS=0
FAIL=0

pass() { PASS=$((PASS + 1)); echo "  [OK] $*"; }
fail() { FAIL=$((FAIL + 1)); echo "  [FAIL] $*"; }

assert_file_exists() {
    [[ -f "$1" ]] && pass "$2" || fail "$2 (missing: $1)"
}

assert_file_absent() {
    [[ ! -e "$1" ]] && pass "$2" || fail "$2 (unexpectedly present: $1)"
}

assert_contains() {
    grep -qF -- "$2" "$1" 2>/dev/null && pass "$3" || fail "$3 (did not find '$2' in $1)"
}

assert_not_contains() {
    grep -qF -- "$2" "$1" 2>/dev/null && fail "$3 (unexpectedly found '$2' in $1)" || pass "$3"
}

assert_yaml_eq() {
    local file="$1" expr="$2" expected="$3" desc="$4" actual
    actual=$(uv run --with pyyaml python3 -c "
import yaml, sys
cfg = yaml.safe_load(open('${file}')) or {}
print(${expr})
" 2>/dev/null)
    [[ "${actual}" == "${expected}" ]] \
        && pass "${desc}" \
        || fail "${desc} (expected '${expected}', got '${actual}')"
}

fresh_scratch() {
    local name="$1"
    local dir="${SCRATCH_ROOT}/${name}"
    rm -rf "${dir}"
    mkdir -p "${dir}"
    local fixture="${FIXTURES_DIR}/${name}"
    if [[ -d "${fixture}" ]]; then
        # copy fixture contents (including dotfiles) into the scratch workspace
        (shopt -s dotglob; cp -r "${fixture}"/* "${dir}"/ 2>/dev/null) || true
    fi
    rm -f "${dir}/.gitkeep"
    echo "${dir}"
}

echo "=== no-config: no .harness-ai/config.yaml -> CLI defaults, then seeded ==="
ws=$(fresh_scratch "no-config")
assert_file_absent "${ws}/.harness-ai/config.yaml" "starts with no config"
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -ne 0 ]]; then
    fail "cli.sh install exited ${rc} (see ${ws}.log)"
else
    assert_file_exists "${ws}/.harness-ai/config.yaml" "starter config.yaml seeded"
    assert_yaml_eq "${ws}/.harness-ai/config.yaml" "cfg['tools']" "['claude']" "seeded tools == CLI default [claude]"
    assert_yaml_eq "${ws}/.harness-ai/config.yaml" "cfg['install']['wikictl']" "False" "seeded install.wikictl == CLI default false"
    assert_yaml_eq "${ws}/.harness-ai/config.yaml" "cfg['behavior']['caveman']" "True" "seeded behavior.caveman == CLI default true"
    assert_file_exists "${ws}/.claude/skills/caveman/SKILL.md" "caveman skill installed (bundled default)"
    assert_contains "${ws}/AGENTS.md" "Default communication mode: caveman" "AGENTS.md has caveman-default instruction (behavior.caveman true)"
    assert_not_contains "${ws}/.mcp.json" "wikictl" "no wikictl MCP entry (install.wikictl false)"
    assert_file_absent "${ws}/.opencode" "no opencode output (opencode not in tools)"
fi

echo ""
echo "=== full-config: every key set, no CLI flags -> config alone drives the run ==="
ws=$(fresh_scratch "full-config")
before_sum=$(sha256sum "${ws}/.harness-ai/config.yaml" | cut -d' ' -f1)
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -ne 0 ]]; then
    fail "cli.sh install exited ${rc} (see ${ws}.log)"
else
    after_sum=$(sha256sum "${ws}/.harness-ai/config.yaml" | cut -d' ' -f1)
    [[ "${before_sum}" == "${after_sum}" ]] \
        && pass "pre-existing config.yaml left untouched (copy-once)" \
        || fail "pre-existing config.yaml was modified"
    assert_file_exists "${ws}/.claude/settings.json" "claude output present (claude in tools)"
    assert_file_exists "${ws}/.opencode/plugins/rtk.ts" "opencode RTK plugin present (opencode in tools)"
    assert_file_exists "${ws}/opencode.json" "opencode.json present (opencode in tools)"
    assert_contains "${ws}/.mcp.json" "wikictl" "wikictl MCP entry present (install.wikictl true, no --wikictl flag passed)"
    assert_contains "${ws}/opencode.json" "wikictl" "wikictl MCP entry present in opencode.json (install.wikictl true, opencode in tools)"
    assert_not_contains "${ws}/.claude/settings.json" "rtk hook claude" "RTK hook NOT merged (install.rtk false)"
    assert_not_contains "${ws}/AGENTS.md" "Default communication mode: caveman" "no caveman-default instruction (behavior.caveman false)"
    assert_file_exists "${ws}/.claude/skills/caveman/SKILL.md" "caveman skill still installed (installDefaults true - only the AGENTS.md default is off)"
fi

echo ""
echo "=== partial-config: one key set -> rest falls through to CLI defaults ==="
ws=$(fresh_scratch "partial-config")
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -ne 0 ]]; then
    fail "cli.sh install exited ${rc} (see ${ws}.log)"
else
    assert_file_exists "${ws}/.claude/settings.json" "tools fell through to CLI default [claude] (not set in fixture)"
    assert_file_absent "${ws}/.opencode" "opencode NOT scaffolded (tools not set in fixture -> CLI default claude-only)"
    assert_contains "${ws}/.mcp.json" "wikictl" "wikictl MCP entry present (the one key the fixture does set)"
    assert_contains "${ws}/.claude/settings.json" "rtk hook claude" "RTK hook merged (install.rtk not set in fixture -> CLI default true)"
    assert_contains "${ws}/AGENTS.md" "Default communication mode: caveman" "caveman-default instruction present (behavior.caveman not set -> CLI default true)"
fi

echo ""
echo "=== malformed-config: invalid YAML -> die() with a clear error, nothing scaffolded ==="
ws=$(fresh_scratch "malformed-config")
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -eq 0 ]]; then
    fail "cli.sh install exited 0 on malformed YAML (expected a non-zero die())"
else
    pass "cli.sh install exited non-zero (${rc}) on malformed YAML"
fi
assert_contains "${ws}.log" "check it is valid YAML" "error message names the bad config file"
assert_file_absent "${ws}/.claude" "nothing scaffolded after the config parse failure"

echo ""
echo "=== custom-tools: multi-entry install.custom round-trips through the delimited-blob bridge ==="
ws=$(fresh_scratch "custom-tools")
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -ne 0 ]]; then
    fail "cli.sh install exited ${rc} (see ${ws}.log)"
else
    assert_contains "${ws}.log" "Custom tool installed: ok-tool" "ok-tool ran (custom command executed)"
    assert_contains "${ws}.log" "fail-tool" "fail-tool's failure is logged"
    assert_contains "${ws}.log" "[WARN]" "fail-tool failure is a warning, not a hard stop"
fi

echo ""
echo "=== wikictl-enabled: install.wikictl true -> wikictl actually installs, resolves, and serves ==="
ws=$(fresh_scratch "wikictl-enabled")
bash "${REPO_DIR}/cli.sh" install --local-path "${REPO_DIR}" --workspace "${ws}" >"${ws}.log" 2>&1
rc=$?
if [[ ${rc} -ne 0 ]]; then
    fail "cli.sh install exited ${rc} (see ${ws}.log)"
else
    if command -v wikictl &>/dev/null; then
        pass "wikictl resolves on PATH after install"
    else
        fail "wikictl not found on PATH after install (see ${ws}.log)"
    fi
    assert_contains "${ws}/.mcp.json" "9797" "mcp.json wikictl entry uses port 9797"

    mkdir -p "${ws}/wiki"
    serve_log="${ws}-serve.log"
    wikictl --wiki-dir "${ws}/wiki" serve --port 9797 >"${serve_log}" 2>&1 &
    serve_pid=$!
    served=0
    for _ in $(seq 1 20); do
        if curl -fsS "http://127.0.0.1:9797/api/entries" &>/dev/null; then
            served=1
            break
        fi
        sleep 0.5
    done
    if [[ ${served} -eq 1 ]]; then
        pass "wikictl serve --port 9797 boots and responds"
    else
        fail "wikictl serve --port 9797 did not respond (see ${serve_log})"
    fi
    kill "${serve_pid}" 2>/dev/null
    wait "${serve_pid}" 2>/dev/null
fi

echo ""
echo "=== Results: ${PASS} passed, ${FAIL} failed ==="
rm -rf "${SCRATCH_ROOT}"
[[ ${FAIL} -eq 0 ]]
