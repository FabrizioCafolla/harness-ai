#!/bin/bash
# Claude Code status line — model, dir, git, context window, cost, rate limits,
# token-saving tool indicators (rtk, headroom, caveman).
# Receives session JSON on stdin (see https://code.claude.com/docs/en/statusline).
# Requires: jq (degrades to a minimal line without it)

set -u

input=$(cat)

if ! command -v jq >/dev/null 2>&1; then
  echo "Claude | install jq for full statusline"
  exit 0
fi

jqr() { echo "$input" | jq -r "$1"; }

# ── Colors (ANSI) ─────────────────────────────────────────────────────────────
RESET=$'\033[0m'
DIM=$'\033[2m'
BOLD=$'\033[1m'
CYAN=$'\033[36m'
MAGENTA=$'\033[35m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
RED=$'\033[31m'

# ── Line 1: model | dir | git branch ─────────────────────────────────────────
model=$(jqr '.model.display_name // "Claude"')
cwd=$(jqr '.workspace.current_dir // .cwd // "?"')
dir=${cwd##*/}

git_info=""
if git -C "$cwd" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  branch=$(git -C "$cwd" branch --show-current 2>/dev/null)
  [[ -z "$branch" ]] && branch=$(git -C "$cwd" rev-parse --short HEAD 2>/dev/null)
  dirty=""
  [[ -n $(git -C "$cwd" status --porcelain 2>/dev/null | head -1) ]] && dirty="*"
  git_info=" ${DIM}|${RESET} ${MAGENTA} ${branch}${dirty}${RESET}"
fi

line1="${BOLD}${CYAN}${model}${RESET} ${DIM}|${RESET} 📁 ${dir}${git_info}"

# ── Token-saving tools: green = active, dim = installed but not active ───────
proj_dir=$(jqr '.workspace.project_dir // empty')
tools=""

# RTK is active when its PreToolUse hook is registered (user or project settings)
if command -v rtk >/dev/null 2>&1; then
  rtk_state="${DIM}⚡rtk·off${RESET}"
  for s in "${HOME}/.claude/settings.json" "${proj_dir}/.claude/settings.json"; do
    if [[ -f "$s" ]] && jq -e '.hooks.PreToolUse[]?.hooks[]? | select(.command == "rtk hook claude")' "$s" >/dev/null 2>&1; then
      rtk_state="${GREEN}⚡rtk${RESET}"
      break
    fi
  done
  tools+=" ${rtk_state}"
fi

# Headroom is active when the session routes through its proxy — i.e. the
# inherited ANTHROPIC_BASE_URL points at a local Headroom endpoint (set by
# `headroom wrap claude` or `headroom proxy` + env). Dim when only installed.
if command -v headroom >/dev/null 2>&1; then
  hr_state="${DIM}🧠headroom·off${RESET}"
  if [[ "${ANTHROPIC_BASE_URL:-}" == *"localhost"* || "${ANTHROPIC_BASE_URL:-}" == *"127.0.0.1"* ]]; then
    hr_state="${GREEN}🧠headroom${RESET}"
  fi
  tools+=" ${hr_state}"
fi

# Caveman: the transcript's on-disk schema is internal to Claude Code and can
# change between releases (undocumented — see code.claude.com/docs/en/sessions),
# and the skill itself writes no state file when it toggles on/off. There is no
# reliable way to detect real-time on/off state from a statusline hook, so this
# shows "installed" (dim) vs "installed and defaults to active" (green) rather
# than attempting to track the actual per-turn toggle.
if [[ -d "${HOME}/.claude/skills/caveman" || -d "${proj_dir}/.claude/skills/caveman" ]]; then
  cave_state="${DIM}🪨caveman${RESET}"
  if [[ -f "${proj_dir}/.harness-ai/config.yaml" ]] \
    && grep -qE '^\s*caveman:\s*true' "${proj_dir}/.harness-ai/config.yaml" 2>/dev/null; then
    cave_state="${GREEN}🪨caveman${RESET}"
  fi
  tools+=" ${cave_state}"
fi

[[ -n "$tools" ]] && line1+=" ${DIM}|${RESET}${tools}"

# ── Line 2: context bar | tokens | cost | lines | rate limit ─────────────────
pct=$(jqr '.context_window.used_percentage // empty')
ctx=""
if [[ -n "$pct" ]]; then
  pct=${pct%.*}
  color=$GREEN
  ((pct >= 50)) && color=$YELLOW
  ((pct >= 75)) && color=$RED

  width=10
  filled=$((pct * width / 100))
  ((filled > width)) && filled=$width
  bar=""
  for ((i = 0; i < width; i++)); do
    if ((i < filled)); then bar+="█"; else bar+="░"; fi
  done

  in_tokens=$(jqr '.context_window.total_input_tokens // 0')
  out_tokens=$(jqr '.context_window.total_output_tokens // 0')
  size=$(jqr '.context_window.context_window_size // 200000')
  used_k=$(((in_tokens + out_tokens) / 1000))
  size_k=$((size / 1000))
  ctx="${color}${bar} ${pct}%${RESET} ${DIM}${used_k}k/${size_k}k${RESET}"
else
  ctx="${DIM}░░░░░░░░░░ ctx n/a${RESET}"
fi

# Cost is real money only on API billing. Subscribers (Pro/Max) get rate_limits
# in the payload and pay via plan, so showing USD would be misleading.
cost=$(jqr '.cost.total_cost_usd // empty')
has_limits=$(jqr '.rate_limits // empty')
cost_part=""
if [[ -z "$has_limits" && -n "$cost" ]]; then
  cost_part=" ${DIM}|${RESET} 💰 $(printf '$%.2f' "$cost")"
fi

added=$(jqr '.cost.total_lines_added // 0')
removed=$(jqr '.cost.total_lines_removed // 0')
lines_part=""
((added + removed > 0)) && lines_part=" ${DIM}|${RESET} ${GREEN}+${added}${RESET}/${RED}-${removed}${RESET}"

limit_5h=$(jqr '.rate_limits.five_hour.used_percentage // empty')
limit_part=""
if [[ -n "$limit_5h" ]]; then
  limit_5h=${limit_5h%.*}
  lcolor=$GREEN
  ((limit_5h >= 60)) && lcolor=$YELLOW
  ((limit_5h >= 85)) && lcolor=$RED
  limit_part=" ${DIM}|${RESET} ⏱ ${lcolor}5h:${limit_5h}%${RESET}"
fi

echo "$line1"
echo "${ctx}${cost_part}${lines_part}${limit_part}"
