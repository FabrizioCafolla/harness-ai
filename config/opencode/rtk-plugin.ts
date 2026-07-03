// Vendored from rtk-ai/rtk, hooks/opencode/rtk.ts (installed upstream via
// `rtk init -g --opencode`). Re-synced manually — no automated ref tracking
// for this file yet (see justfile's `update-skills` for the pattern used by
// content/skills/ entries that do track an upstream ref).
//
// Always copied when the `opencode` tool is scaffolded, regardless of
// install.rtk: the plugin self-disables at runtime if the `rtk` binary is
// not on PATH (see the `which rtk` guard below), matching the Claude hook
// template's behavior of always being present but only acting when rtk
// exists.
import type { Plugin } from "@opencode-ai/plugin"

// RTK OpenCode plugin — rewrites commands to use rtk for token savings.
// Requires: rtk >= 0.23.0 in PATH.
//
// This is a thin delegating plugin: all rewrite logic lives in `rtk rewrite`,
// which is the single source of truth (src/discover/registry.rs).
// To add or change rewrite rules, edit the Rust registry — not this file.

export const RtkOpenCodePlugin: Plugin = async ({ $ }) => {
  try {
    await $`which rtk`.quiet()
  } catch {
    console.warn("[rtk] rtk binary not found in PATH — plugin disabled")
    return {}
  }

  return {
    "tool.execute.before": async (input, output) => {
      const tool = String(input?.tool ?? "").toLowerCase()
      if (tool !== "bash" && tool !== "shell") return
      const args = output?.args
      if (!args || typeof args !== "object") return

      const command = (args as Record<string, unknown>).command
      if (typeof command !== "string" || !command) return

      try {
        const result = await $`rtk rewrite ${command}`.quiet().nothrow()
        const rewritten = String(result.stdout).trim()
        if (rewritten && rewritten !== command) {
          ;(args as Record<string, unknown>).command = rewritten
        }
      } catch {
        // rtk rewrite failed — pass through unchanged
      }
    },
  }
}
