## harness-ai

[harness-ai](https://github.com/FabrizioCafolla/harness-ai) is a devcontainer feature that assembles AI skills, agents, and hooks into the workspace at container startup. It reads content from one or two repositories, injects per-tool frontmatter, and writes output to tool-specific paths.

**Generated files must never be edited directly.** On the next scaffold run (`harnessai sync` on container start, or `harnessai install`) they are fully regenerated — any manual change is lost. To change a skill or agent: edit the source in the content repo, not the output. Hooks are also harness-managed: customize them via the content repo override.

### Memory layer (wikictl)

[wikictl](https://github.com/FabrizioCafolla/harness-ai/tree/main/wikictl) is a file-based AI memory system, gated behind `install.wikictl` (off by default). When enabled, harness-ai installs the `wikictl` CLI, adds its MCP server to the workspace's MCP config (`http://127.0.0.1:9797/mcp/` by default) so agents can read/write entries directly, and scaffolds the `wikictl`, `wikictl-read`, `wikictl-create`, `wikictl-edit`, and `wikictl-mcp` skills that teach the metadata-first workflow (scan entry metadata before loading full bodies). Entries are plain Markdown with YAML frontmatter, stored under `wiki/` in the workspace — persistent knowledge (decisions, research, project context) that survives across sessions, browsable via `wikictl serve`'s web UI or queried straight from the CLI (`wikictl list`, `wikictl search`, `wikictl read <name>`).

### Setup

Structured config — `tools`, install toggles, the content repo — lives in the workspace's `.harness-ai/config.yaml`, the single source of truth. The devcontainer feature ships with no options at all.

**Devcontainer** (`devcontainer.json`):

```json
{
  "features": {
    "ghcr.io/fabriziocafolla/harness-ai/harness-ai:0": {}
  }
}
```

`.harness-ai/config.yaml`:

```yaml
tools: [claude]
install:
  openspec: true
behavior:
  caveman: true
contentRepo:
  url: https://github.com/your-org/your-private-skills-repo
  ref: main
```

**CLI** (`cli.sh`) — for use outside a devcontainer:

```bash
GITHUB_TOKEN=$(gh auth token) bash cli.sh install \
  --workspace /path/to/project \
  --tools claude \
  --content-repo https://github.com/your-org/your-private-skills-repo
```
