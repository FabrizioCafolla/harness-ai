#!/usr/bin/env bash
# =============================================================================
# harness-ai devcontainer feature entrypoint.
#
# This is a required entrypoint per the devcontainer Feature spec, but it does
# almost nothing: it verifies Python, reads the feature's own version, and
# generates a thin `harnessai` launcher pinned to that version. It installs
# no binary and vendors no harness-ai content — `harnessai install`
# (postCreateCommand) and `harnessai sync` (postStartCommand) do that at
# runtime by fetching cli.sh from the repo at the pinned ref. See cli.sh for
# the actual implementation (shared with the standalone curl installer).
#
# The feature has no options (see devcontainer-feature.json) — there is
# nothing to bake into the launcher. All configuration lives in the
# workspace's .harness-ai/config.yaml, read by cli.sh at runtime.
# =============================================================================
set -euo pipefail

FEATURE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# Verify Python 3.9+.
# This is a prerequisite — harness-ai does NOT install Python.
# ---------------------------------------------------------------------------
if ! command -v python3 &>/dev/null; then
  echo "[ERROR] harness-ai requires Python 3.9+ but python3 was not found."
  echo ""
  echo "  Add the Python devcontainer feature BEFORE harness-ai:"
  echo ""
  echo '    "features": {'
  echo '      "ghcr.io/devcontainers/features/python:1": { "version": "3.13" },'
  echo '      "ghcr.io/fabriziocafolla/harness-ai/harness-ai:0": {}'
  echo '    }'
  echo ""
  exit 1
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [[ "${PY_MAJOR}" -lt 3 ]] || [[ "${PY_MAJOR}" -eq 3 && "${PY_MINOR}" -lt 9 ]]; then
  echo "[ERROR] harness-ai requires Python 3.9+, found ${PY_VERSION}."
  exit 1
fi
echo "[OK] Python ${PY_VERSION} found"

# ---------------------------------------------------------------------------
# Resolve the feature version — this becomes the pinned ref that harnessai
# fetches cli.sh (and harness-ai content) at, so behaviour stays reproducible
# for a given feature version instead of tracking a moving `main`.
# ---------------------------------------------------------------------------
FEATURE_VERSION=$(python3 -c "import json; print(json.load(open('${FEATURE_DIR}/devcontainer-feature.json'))['version'])")
echo "[OK] harness-ai version ${FEATURE_VERSION}"

# ---------------------------------------------------------------------------
# Generate the harnessai launcher. It fetches the real implementation
# (cli.sh) from the repo at the pinned FEATURE_VERSION on every invocation —
# nothing is vendored, so there is no packaging step that can drop an asset.
# A failed fetch or scaffold run must never block container start.
# ---------------------------------------------------------------------------
cat > /usr/local/bin/harnessai <<EOF
#!/usr/bin/env bash
set -euo pipefail
REF="${FEATURE_VERSION}"
SUB="install"
if [[ \$# -gt 0 && "\$1" != -* ]]; then
  SUB="\$1"
  shift
fi
curl -fsSL "https://raw.githubusercontent.com/FabrizioCafolla/harness-ai/\${REF}/cli.sh" \\
  | bash -s -- "\${SUB}" --ref "\${REF}" --workspace "\${CONTAINER_WORKSPACE_FOLDER:-\$(pwd)}" "\$@" \\
  || exit 0
EOF

chmod +x /usr/local/bin/harnessai
echo "[OK] harnessai installed (pinned to ${FEATURE_VERSION})"
