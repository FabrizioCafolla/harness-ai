## harness-ai

[harness-ai](https://github.com/FabrizioCafolla/harness-ai) is a devcontainer feature that assembles AI skills, agents, commands and hooks into the workspace at container startup. Sources merge in precedence order, later winning: the bundled defaults, single skills pulled from a path inside another repo (`skillPaths`), any number of named content repos, a workspace-local source, and finally `local` content hand-authored in the workspace itself. Per-tool frontmatter is injected on the way out, to tool-specific paths.

**Generated files must never be edited directly.** On the next scaffold run (`harnessai sync` on container start, or `harnessai install`) they are fully regenerated — any manual change is lost. To change a skill or agent: edit the source in the content repo, not the output. Hooks are also harness-managed: customize them via the content repo override.

### Memory layer (wikictl)

[wikictl](https://github.com/FabrizioCafolla/harness-ai/tree/main/wikictl) is a file-based AI memory system, gated behind `install.wikictl` (off by default). When enabled, harness-ai installs the `wikictl` CLI, adds its MCP server to the workspace's MCP config (`http://127.0.0.1:9797/mcp/` by default) so agents can read/write entries directly, and scaffolds the `wikictl`, `wikictl-read`, `wikictl-create`, `wikictl-edit`, and `wikictl-mcp` skills that teach the metadata-first workflow (scan entry metadata before loading full bodies). Entries are plain Markdown with YAML frontmatter, stored under `wiki/` in the workspace — persistent knowledge (decisions, research, project context) that survives across sessions, browsable via `wikictl serve`'s web UI or queried straight from the CLI (`wikictl list`, `wikictl search`, `wikictl read <name>`).

### Setup

Structured config — `tools`, install toggles, content repos — lives in the workspace's `.harness-ai/config.yaml`, the single source of truth. The devcontainer feature ships with no options at all.

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
contentRepos:
  - name: your-private-skills-repo
    url: https://github.com/your-org/your-private-skills-repo
    ref: main
skillPaths:
  - url: https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me
```

`skillPaths` takes a skill straight from a directory in someone else's repo: the ref and sub-path come from the URL, and the whole directory travels, subfolders included. Point it at a folder of skills instead of one skill and every sub-directory holding a `SKILL.md` is installed.

The old singular `contentRepo: {url, ref}` still works (sugar for a one-entry `contentRepos` list, name derived from the URL) with a deprecation warning — see [Content repos](https://github.com/FabrizioCafolla/harness-ai#content-repos).

**CLI** (`cli.sh`) — for use outside a devcontainer:

```bash
GITHUB_TOKEN=$(gh auth token) bash cli.sh install \
  --workspace /path/to/project \
  --tools claude \
  --content-repo https://github.com/your-org/your-private-skills-repo
```
