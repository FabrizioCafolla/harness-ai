#!/usr/bin/env python3
"""Harness AI assembles AI agent/skill assets with tool-specific frontmatter into a workspace.

Reads content files (pure Markdown, no frontmatter) from content/ and injects
per-tool metadata from config/agents.yml and config/skills.yml at runtime.
Supports merging additional content from N named, pre-cloned external
repositories (`contentRepos`), plus a `local` source authored directly in
the consuming workspace's own canonical store at `.harness-ai/skills/local/`
and `.harness-ai/agents/local/`.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import yaml


class _Dumper(yaml.Dumper):
    pass


_Dumper.add_representer(
    list,
    lambda dumper, data: dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True),
)

_HARNESS_DIR = ".harness-ai"
_LOCK_FILE = "lock"
_MANIFEST_FILE = "manifest.json"
_RESERVED_SOURCE_NAMES = {"default", "local", "workspace"}


def _write_with_frontmatter(dest: pathlib.Path, meta: dict, body: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(f"---\n{yaml.dump(meta, Dumper=_Dumper, default_flow_style=False, allow_unicode=True, sort_keys=False, width=float('inf'))}---\n\n{body}")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split a `local` skill/agent file into (frontmatter dict, body). Best-effort:
    a missing or malformed frontmatter block just yields an empty meta dict."""
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            fm_text = text[4:end]
            body = text[end + 4:].lstrip("\n")
            try:
                meta = yaml.safe_load(fm_text) or {}
            except yaml.YAMLError:
                meta = {}
            return meta, body
    return {}, text


def _slugify(url: str) -> str:
    name = url.rstrip("/").rsplit("/", 1)[-1]
    name = re.sub(r"\.git$", "", name)
    name = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    return name or "content-repo"


def _copy_extra(feature_dir: pathlib.Path, ws: pathlib.Path, ef: dict) -> None:
    src = feature_dir / ef["source"]
    dst = ws / ef["dest"]
    if not src.exists():
        print(f"  │  [WARN] missing extra file: {src}")
        return
    if dst.exists():
        print(f"  │  [skip] {dst.relative_to(ws)}  (already exists)")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  │  [copy] {src.name}  →  {dst.relative_to(ws)}")


def _update_agents_md(
    ws: pathlib.Path,
    feature_dir: pathlib.Path,
    content_repo_paths: list[pathlib.Path],
    skill_keys: list[str],
    agent_keys: list[str],
    caveman_default: bool = False,
) -> None:
    """Inject or update the harness-ai managed block in AGENTS.md."""
    agents_md = ws / "AGENTS.md"
    start = "<!-- [harness-ai:START] managed by harness-ai, do not edit manually -->"
    end = "<!-- [harness-ai:END] -->"

    parts: list[str] = []

    if caveman_default and "caveman" in skill_keys:
        parts.append(
            "**Default communication mode: caveman.** Respond in caveman mode "
            "(see the `caveman` skill) from the first message of every session — "
            "no need to wait for `/caveman`. Turn it off only on explicit "
            "\"stop caveman\" / \"normal mode\"."
        )

    public_content = feature_dir / "content" / "agents.harness-ai.md"
    if public_content.exists():
        parts.append(public_content.read_text().strip())

    for content_repo_path in content_repo_paths:
        if not content_repo_path.exists():
            continue
        private_content = content_repo_path / "agents.harness-ai.md"
        if private_content.exists():
            parts.append(private_content.read_text().strip())

    if skill_keys:
        skill_list = "\n".join(f"- `{k}`" for k in skill_keys)
        parts.append(f"### Installed skills\n\n{skill_list}")

    if agent_keys:
        agent_list = "\n".join(f"- `{k}`" for k in agent_keys)
        parts.append(f"### Installed agents\n\n{agent_list}")

    block = start + "\n\n" + "\n\n".join(parts) + "\n\n" + end

    if agents_md.exists():
        content = agents_md.read_text()
        if start in content:
            new_content = re.sub(
                rf"{re.escape(start)}.*?{re.escape(end)}",
                block,
                content,
                flags=re.DOTALL,
            )
            agents_md.write_text(new_content)
            print(f"  [agents.md] updated managed block")
        else:
            sep = "\n" if content.endswith("\n") else "\n\n"
            agents_md.write_text(content + sep + block + "\n")
            print(f"  [agents.md] appended managed block to existing AGENTS.md")
    else:
        agents_md.write_text(block + "\n")
        print(f"  [agents.md] created AGENTS.md with harness-ai block")


def _update_gitignore(ws: pathlib.Path, entries: list[str]) -> None:
    gitignore = ws / ".gitignore"
    start = "# [START] Harness AI"
    end = "# [END] Harness AI"
    block = start + "\n" + "\n".join(entries) + "\n" + end

    if gitignore.exists():
        content = gitignore.read_text()
        if start in content:
            new_content = re.sub(
                rf"{re.escape(start)}.*?{re.escape(end)}",
                block,
                content,
                flags=re.DOTALL,
            )
            gitignore.write_text(new_content)
            print(f"  [gitignore] updated block in .gitignore")
        else:
            sep = "\n" if content.endswith("\n") else "\n\n"
            gitignore.write_text(content + sep + block + "\n")
            print(f"  [gitignore] appended block to .gitignore")
    else:
        gitignore.write_text(block + "\n")
        print(f"  [gitignore] created .gitignore with harness-ai block")


def _hash_directory_contents(root: pathlib.Path) -> bytes:
    """Content hash (not git-based) of every file under `root`, sorted by
    relative path for determinism. Used for the `workspace` source (design.md
    D2a) — `.harness-ai/local/` is a plain subdirectory of the consuming
    workspace's own repo, not an independent checkout, so `git rev-parse HEAD`
    would return the outer repo's HEAD and miss uncommitted edits entirely."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode())
            h.update(p.read_bytes())
    return h.digest()


def _compute_content_hash(
    feature_dir: pathlib.Path,
    content_repos: list[tuple[str, pathlib.Path | None, str | None]],
) -> str:
    """Compute a deterministic hash of the harness-ai identity + every configured
    content repo's identity (name-sorted, so arg order never changes the digest).

    harness-ai identity: HEAD SHA when available (git clone), version string as
    fallback (devcontainer feature installed from tarball, no .git dir).

    Content repo identity, per repo: pre-computed SHA string (from git ls-remote,
    avoids a clone) takes precedence over local git; both are equivalent since
    they represent the same commit. The `workspace` source is content-hashed
    instead (see `_hash_directory_contents`), never git-hashed.
    """
    h = hashlib.sha256()

    try:
        sha = subprocess.check_output(
            ["git", "-C", str(feature_dir), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        ).strip()
        h.update(sha)
    except subprocess.CalledProcessError:
        version_file = feature_dir / "devcontainer-feature.json"
        if version_file.exists():
            data = json.loads(version_file.read_text())
            h.update(data.get("version", "unknown").encode())

    for name, path, precomputed_sha in sorted(content_repos, key=lambda t: t[0]):
        h.update(name.encode())
        if precomputed_sha:
            h.update(precomputed_sha.strip().encode())
        elif name == "workspace" and path and path.exists():
            h.update(_hash_directory_contents(path))
        elif path and path.exists():
            try:
                sha = subprocess.check_output(
                    ["git", "-C", str(path), "rev-parse", "HEAD"],
                    stderr=subprocess.DEVNULL,
                ).strip()
                h.update(sha)
            except subprocess.CalledProcessError:
                pass

    return h.hexdigest()


def _read_lock(ws: pathlib.Path) -> str:
    lock = ws / _HARNESS_DIR / _LOCK_FILE
    return lock.read_text().strip() if lock.exists() else ""


def _write_lock(ws: pathlib.Path, digest: str) -> None:
    lock_dir = ws / _HARNESS_DIR
    lock_dir.mkdir(parents=True, exist_ok=True)
    (lock_dir / _LOCK_FILE).write_text(digest + "\n")


def _read_manifest(ws: pathlib.Path) -> dict:
    p = ws / _HARNESS_DIR / _MANIFEST_FILE
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _write_manifest(ws: pathlib.Path, manifest: dict) -> None:
    manifest_dir = ws / _HARNESS_DIR
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / _MANIFEST_FILE).write_text(json.dumps(manifest, indent=2) + "\n")


def _cleanup_stale_for_tool(
    ws: pathlib.Path,
    tool: str,
    old_sources: dict,
    new_sources: dict,
    tool_paths: dict,
) -> dict[str, int]:
    """Remove one tool's skill/agent symlinks (and, for default/repo/workspace
    sources, their canonical store entries) that were managed in a previous
    run but are no longer current, keyed by source — see design.md D7/D9/D6a.

    Must be called *between* the `default`/`contentRepos`/`workspace` render
    loop and the `local`-linking pass, with `new_sources` containing that
    loop's real results PLUS a `"local"` entry set to a *preview* of what
    `local`'s linking pass is about to (re-)claim this run — the actual keys
    from `_scan_local_source`, known upfront regardless of whether the
    linking pass has run yet. This function itself, not the caller, decides
    what to do with that preview (see below) — found necessary during
    real-workspace testing: without it, every still-valid `local` key gets
    misdiagnosed as stale on every single run (the caller can't safely pass
    an accurate `new_sources["local"]` any other way, since it isn't known
    for certain until the linking pass itself runs, which happens after this
    call by design).

    Two different things happen with `"local"` here, for two different
    reasons (design.md D6a refinement):
    - The `"local"` entry in `new_sources` (the preview) makes the *old*
      `"local"` bucket's own stale-diff (below) accurate — without it, a key
      that's still genuinely local looks stale simply because the preview
      wasn't available yet, and its (perfectly fine) symlink gets deleted
      and immediately recreated on every run for no reason.
    - But `"local"` is deliberately EXCLUDED from `all_current_skills`/
      `all_current_agents` (the "did this key migrate to a same-shaped
      source, so skip physical deletion" check) below — `local`'s tool-dir
      representation (a whole-directory symlink) is structurally
      incompatible with the real-directory-plus-file-symlink shape every
      other source uses, so a key migrating *to* `local` must have its old
      physical directory actually removed here, clearing the path for
      `local`'s own linking pass — not preserved as if it were an in-place
      migration among same-shaped sources.

    `local`'s own canonical store (`.harness-ai/skills/local`/`.harness-ai/agents/local`
    — the author's actual source, design.md D3) is never deleted here; only a
    dangling tool-dir symlink (in `.claude`/`.opencode`/`.agents`/etc., all of
    them pure render targets for `local` now) whose local source disappeared
    is removed.
    """
    removed_counts: dict[str, int] = {}

    if not old_sources or not isinstance(next(iter(old_sources.values())), dict):
        # Pre-upgrade flat manifest shape ({skills: [...], agents: [...]})
        # can't be meaningfully diffed against the new source-keyed shape.
        # The render pass replaces old real copies with symlinks in place —
        # no separate migration step needed (design.md Migration Plan).
        return removed_counts

    base = ws / tool_paths["base_dir"]
    skills_base = base / tool_paths["skills"]["dir"]
    agents_dir = base / tool_paths["agents"]["dir"]
    agent_suffix = tool_paths["agents"]["suffix"]

    # Keys claimed by any *non-local* source so far this run (design.md
    # D6a) — a key can migrate from one source to another on a collision
    # (e.g. `default` loses precedence to a newly-added `workspace` entry)
    # rather than genuinely disappearing, and the physical tool-dir path is
    # shared across those sources (same real-dir-plus-file-symlink shape).
    # `local` is excluded here even though its preview may be present in
    # `new_sources` — see docstring.
    all_current_skills: set[str] = set()
    all_current_agents: set[str] = set()
    for src_name, src_data in new_sources.items():
        if src_name == "local":
            continue
        all_current_skills.update(src_data.get("skills", []))
        all_current_agents.update(src_data.get("agents", []))

    for source_name, prev in old_sources.items():
        current = new_sources.get(source_name, {"skills": [], "agents": []})
        stale_skills = set(prev.get("skills", [])) - set(current.get("skills", []))
        stale_agents = set(prev.get("agents", [])) - set(current.get("agents", []))
        removed = 0

        for key in sorted(stale_skills):
            if key in all_current_skills:
                # Migrated to a different (same-shaped) source this run, not
                # deleted — the winning source already owns the physical path.
                print(f"  [cleanup] {source_name} skill '{key}' migrated to another source — tool-dir path left alone")
            else:
                stale_dir = skills_base / key
                if stale_dir.is_symlink():
                    stale_dir.unlink()
                    removed += 1
                    print(f"  [cleanup] removed stale {source_name} skill symlink: {stale_dir.relative_to(ws)}")
                elif stale_dir.exists():
                    shutil.rmtree(stale_dir)
                    removed += 1
                    print(f"  [cleanup] removed stale {source_name} skill dir: {stale_dir.relative_to(ws)}/")
            if source_name != "local":
                canonical_dir = ws / _HARNESS_DIR / "skills" / source_name / key
                if canonical_dir.exists():
                    shutil.rmtree(canonical_dir)

        for key in sorted(stale_agents):
            if key in all_current_agents:
                print(f"  [cleanup] {source_name} agent '{key}' migrated to another source — tool-dir path left alone")
            else:
                stale_file = agents_dir / f"{key}{agent_suffix}"
                if stale_file.is_symlink() or stale_file.exists():
                    stale_file.unlink()
                    removed += 1
                    print(f"  [cleanup] removed stale {source_name} agent: {stale_file.relative_to(ws)}")
            if source_name != "local":
                canonical_dir = ws / _HARNESS_DIR / "agents" / source_name / key
                if canonical_dir.exists():
                    shutil.rmtree(canonical_dir)

        if removed:
            removed_counts[source_name] = removed

    return removed_counts


def _load_content(
    feature_dir: pathlib.Path,
    install_defaults: bool,
    content_repos: list[tuple[str, pathlib.Path]],
) -> tuple[dict, dict, dict, dict, dict, list[str], dict[str, pathlib.Path]]:
    """Merge `paths.yml` + agents/skills `metadata.yml` across `default` and N
    named content repos, in that order (later sources win on key collision).

    Returns (paths_cfg, agents_by_key, skills_by_key, agents_defaults,
    skills_defaults, source_order, source_roots). agents_by_key/skills_by_key
    map key -> {"source": name, "entry": {...}}.
    """

    def _load_yaml(p: pathlib.Path) -> dict:
        return yaml.safe_load(p.read_text()) if p.exists() else {}

    paths_cfg: dict = {}
    agents_by_key: dict[str, dict] = {}
    skills_by_key: dict[str, dict] = {}
    agents_defaults: dict = {}
    skills_defaults: dict = {}
    source_order: list[str] = []
    source_roots: dict[str, pathlib.Path] = {}

    def _merge_source(name: str, root: pathlib.Path, is_default_source: bool) -> None:
        nonlocal agents_defaults, skills_defaults
        source_order.append(name)
        source_roots[name] = root

        remote_paths = _load_yaml(root / "paths.yml")
        for tool, cfg in remote_paths.items():
            paths_cfg[tool] = cfg

        agents_meta = _load_yaml(root / "agents" / "metadata.yml")
        if is_default_source:
            agents_defaults = agents_meta.get("default") or {}
        for key, val in (agents_meta.get("agents") or {}).items():
            agents_by_key[key] = {"source": name, "entry": val}

        skills_meta = _load_yaml(root / "skills" / "metadata.yml")
        if is_default_source:
            skills_defaults = skills_meta.get("default") or {}
        for key, val in (skills_meta.get("skills") or {}).items():
            skills_by_key[key] = {"source": name, "entry": val}

    if install_defaults:
        _merge_source("default", feature_dir / "content", is_default_source=True)

    for name, path in content_repos:
        if path and path.exists():
            _merge_source(name, path, is_default_source=False)

    return paths_cfg, agents_by_key, skills_by_key, agents_defaults, skills_defaults, source_order, source_roots


def _tool_meta_for(entry: dict, tool: str, defaults: dict) -> dict | None:
    """Resolve a skill/agent's rendered frontmatter for one active tool profile.

    Falls back to the claude/opencode block's name+description when no explicit
    block for `tool` exists in metadata.yml — the always-on `agents` profile
    (D4) intentionally carries only those two keys and doesn't require every
    bundled/repo entry to declare its own `agents:` block.
    """
    if tool in entry and entry[tool] is not None:
        return {**defaults, **entry[tool]}
    if tool == "agents":
        for fallback_tool in ("claude", "opencode"):
            src = entry.get(fallback_tool)
            if src:
                minimal = {k: src[k] for k in ("name", "description") if k in src}
                return {**defaults, **minimal}
    return None


def _scan_local_source(ws: pathlib.Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """Discover `local` skills/agents: files authored directly under
    `.harness-ai/skills/local/<key>/SKILL.md` and `.harness-ai/agents/local/<key>.md`
    — see design.md D1/D2. This is `local`'s own canonical store, never a
    render target for any other source, so no self-reference guard is needed
    here (unlike the old `.agents/skills`/`.agents/agents` location, which
    used to double as a render target too)."""
    skills: dict[str, dict] = {}
    agents: dict[str, dict] = {}

    skills_dir = ws / _HARNESS_DIR / "skills" / "local"
    if skills_dir.is_dir():
        for entry in sorted(skills_dir.iterdir()):
            skill_md = entry / "SKILL.md"
            if skill_md.is_file():
                meta, _ = _parse_frontmatter(skill_md.read_text())
                skills[entry.name] = meta

    agents_dir = ws / _HARNESS_DIR / "agents" / "local"
    if agents_dir.is_dir():
        for entry in sorted(agents_dir.iterdir()):
            if entry.suffix == ".md" and entry.is_file():
                meta, _ = _parse_frontmatter(entry.read_text())
                agents[entry.stem] = meta

    return skills, agents


def _category_key_match(key: str, category: str | None, subcategory: str | None, categories: set[str], keys: set[str]) -> bool:
    if key in keys:
        return True
    if category and category in categories:
        return True
    if category and subcategory and f"{category}.{subcategory}" in categories:
        return True
    return False


def _apply_skill_filter(
    skills_by_key: dict[str, dict],
    include_categories: list[str],
    include_keys: list[str],
    exclude_categories: list[str],
    exclude_keys: list[str],
) -> dict[str, dict]:
    """category/subcategory/key include-then-exclude filter for default/repo
    skills — see design.md D5. `local` skills aren't in `skills_by_key` (they
    have no metadata.yml entry) and are filtered separately, key-only."""
    inc_cats, inc_keys = set(include_categories), set(include_keys)
    exc_cats, exc_keys = set(exclude_categories), set(exclude_keys)

    result: dict[str, dict] = {}
    for key, info in skills_by_key.items():
        entry = info["entry"]
        category, subcategory = entry.get("category"), entry.get("subcategory")

        included = (not inc_cats and not inc_keys) or _category_key_match(key, category, subcategory, inc_cats, inc_keys)
        if not included:
            continue
        excluded = bool(exc_cats or exc_keys) and _category_key_match(key, category, subcategory, exc_cats, exc_keys)
        if excluded:
            continue
        result[key] = info
    return result


def _resolve_from_sources(source_roots: dict[str, pathlib.Path], source_order: list[str], relative: str) -> pathlib.Path | None:
    """Later sources win — used for hooks/mcp.json/opencode.json overrides,
    which (unlike skills/agents) aren't owned by a single already-known source."""
    found = None
    for name in source_order:
        candidate = source_roots[name] / relative
        if candidate.exists():
            found = candidate
    return found


def _make_symlink(link_path: pathlib.Path, target_path: pathlib.Path) -> str:
    """Create/replace a relative symlink at link_path -> target_path.

    Returns "created" (symlink made or repointed), "unchanged" (already
    correct), or "foreign" — link_path holds real, non-symlink content that
    harness-ai never put there, which is left completely untouched instead of
    being clobbered (design.md D5 — every render path funnels through this
    one function, so the guard lives here once, not at each call site)."""
    link_path.parent.mkdir(parents=True, exist_ok=True)
    rel_target = os.path.relpath(target_path, link_path.parent)
    if link_path.is_symlink():
        if os.readlink(link_path) == rel_target:
            return "unchanged"
        link_path.unlink()
    elif link_path.exists():
        return "foreign"
    link_path.symlink_to(rel_target)
    return "created"


def _apply_claude_hooks(ws: pathlib.Path, hooks_path: pathlib.Path) -> None:
    """Merge hooks template into .claude/settings.json, replacing only the 'hooks' key."""
    settings_path = ws / ".claude" / "settings.json"
    if not settings_path.exists():
        print(f"  [hooks] .claude/settings.json not found, skipping Claude hooks")
        return

    try:
        hooks_data = json.loads(hooks_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] failed to read hooks template {hooks_path}: {e}")
        return

    try:
        settings = json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] failed to read .claude/settings.json: {e}")
        return

    settings["hooks"] = hooks_data
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    print(f"  [hooks] updated .claude/settings.json[hooks]")


def _apply_opencode_hook(ws: pathlib.Path, hooks_path: pathlib.Path, dest: str) -> None:
    """Write the OpenCode RTK plugin file verbatim (always overwrite, no JSON merge)."""
    try:
        hooks_data = hooks_path.read_text()
    except OSError as e:
        print(f"  [WARN] failed to read hooks template {hooks_path}: {e}")
        return

    dst = ws / dest
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(hooks_data)
    print(f"  [hooks] wrote {dst.relative_to(ws)}")


def _merge_wikictl_mcp(ws: pathlib.Path, feature_dir: pathlib.Path) -> None:
    """Merge the gated wikictl server into .mcp.json (idempotent, additive only)."""
    snippet = feature_dir / "config" / "mcp.wikictl.json"
    if not snippet.exists():
        print(f"  [WARN] missing config/mcp.wikictl.json template")
        return
    try:
        wikictl_servers = json.loads(snippet.read_text()).get("mcpServers", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] failed to read config/mcp.wikictl.json: {e}")
        return

    dst = ws / ".mcp.json"
    if dst.exists():
        try:
            data = json.loads(dst.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [WARN] failed to read .mcp.json, skipping wikictl entry: {e}")
            return
    else:
        data = {"mcpServers": {}}

    servers = data.setdefault("mcpServers", {})
    if all(servers.get(k) == v for k, v in wikictl_servers.items()):
        print(f"  [skip] .mcp.json wikictl entry (already present)")
        return
    servers.update(wikictl_servers)
    dst.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  [mcp] added wikictl server to .mcp.json")


def _merge_wikictl_mcp_opencode(ws: pathlib.Path, feature_dir: pathlib.Path) -> None:
    """Merge the gated wikictl server into opencode.json's mcp key (idempotent, additive only)."""
    snippet = feature_dir / "config" / "mcp.wikictl.opencode.json"
    if not snippet.exists():
        print(f"  [WARN] missing config/mcp.wikictl.opencode.json template")
        return
    try:
        wikictl_servers = json.loads(snippet.read_text()).get("mcp", {})
    except (json.JSONDecodeError, OSError) as e:
        print(f"  [WARN] failed to read config/mcp.wikictl.opencode.json: {e}")
        return

    dst = ws / "opencode.json"
    if dst.exists():
        try:
            data = json.loads(dst.read_text())
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [WARN] failed to read opencode.json, skipping wikictl entry: {e}")
            return
    else:
        data = {"$schema": "https://opencode.ai/config.json", "mcp": {}}

    servers = data.setdefault("mcp", {})
    if all(servers.get(k) == v for k, v in wikictl_servers.items()):
        print(f"  [skip] opencode.json wikictl entry (already present)")
        return
    servers.update(wikictl_servers)
    dst.write_text(json.dumps(data, indent=2) + "\n")
    print(f"  [mcp] added wikictl server to opencode.json")


def _render_skill(
    ws: pathlib.Path,
    tool: str,
    tool_paths: dict,
    source_name: str,
    key: str,
    meta: dict,
    body: str,
    refs_src: pathlib.Path | None,
) -> tuple[bool, bool]:
    """Returns (rendered, refs_foreign). `rendered` is False if the skill's
    main tool-dir slot was blocked by foreign content (design.md D5/D6) — the
    skill is not counted as linked. `refs_foreign` is True if a separate,
    foreign `references/` slot was blocked — tracked independently so it's
    reflected in the `foreign` counter even when the main file rendered fine
    (found during fresh-eyes review: previously silent in the sync summary,
    only visible via the `[foreign]` log line)."""
    canonical_dir = ws / _HARNESS_DIR / "skills" / source_name / key
    canonical_file = canonical_dir / f"{tool}.SKILL.md"
    _write_with_frontmatter(canonical_file, meta, body)

    base = ws / tool_paths["base_dir"]
    filename = tool_paths["skills"]["filename"]
    skill_dir = base / tool_paths["skills"]["dir"] / key
    skill_dir.mkdir(parents=True, exist_ok=True)
    result = _make_symlink(skill_dir / filename, canonical_file)
    if result == "foreign":
        print(f"  │  [foreign] skill '{key}' ({tool}, source: {source_name}) — real content already at {(skill_dir / filename).relative_to(ws)}, left untouched")

    refs_foreign = False
    if refs_src and refs_src.exists():
        canonical_refs = canonical_dir / "references"
        shutil.copytree(refs_src, canonical_refs, dirs_exist_ok=True)
        refs_result = _make_symlink(skill_dir / "references", canonical_refs)
        if refs_result == "foreign":
            refs_foreign = True
            print(f"  │  [foreign] skill '{key}' references ({tool}, source: {source_name}) — real content already at {(skill_dir / 'references').relative_to(ws)}, left untouched")

    return result != "foreign", refs_foreign


def _render_agent(
    ws: pathlib.Path,
    tool: str,
    tool_paths: dict,
    source_name: str,
    key: str,
    meta: dict,
    body: str,
) -> bool:
    """Returns False if the agent's tool-dir slot was blocked by foreign
    content (design.md D5/D6) — the agent is not counted as linked."""
    canonical_dir = ws / _HARNESS_DIR / "agents" / source_name / key
    canonical_file = canonical_dir / f"{tool}.md"
    _write_with_frontmatter(canonical_file, meta, body)

    base = ws / tool_paths["base_dir"]
    suffix = tool_paths["agents"]["suffix"]
    agents_dir = base / tool_paths["agents"]["dir"]
    agents_dir.mkdir(parents=True, exist_ok=True)
    dest = agents_dir / f"{key}{suffix}"
    result = _make_symlink(dest, canonical_file)
    if result == "foreign":
        print(f"  │  [foreign] agent '{key}' ({tool}, source: {source_name}) — real content already at {dest.relative_to(ws)}, left untouched")
    return result != "foreign"


def _link_local_skill(ws: pathlib.Path, tool_paths: dict, tool: str, key: str) -> bool:
    """Returns False if blocked by foreign content (design.md D5/D6)."""
    base = ws / tool_paths["base_dir"]
    skills_base = base / tool_paths["skills"]["dir"]
    skills_base.mkdir(parents=True, exist_ok=True)
    dest = skills_base / key
    result = _make_symlink(dest, ws / _HARNESS_DIR / "skills" / "local" / key)
    if result == "foreign":
        print(f"  │  [foreign] skill '{key}' ({tool}, source: local) — real content already at {dest.relative_to(ws)}, left untouched")
    return result != "foreign"


def _link_local_agent(ws: pathlib.Path, tool_paths: dict, tool: str, key: str) -> bool:
    """Returns False if blocked by foreign content (design.md D5/D6)."""
    base = ws / tool_paths["base_dir"]
    suffix = tool_paths["agents"]["suffix"]
    agents_dir = base / tool_paths["agents"]["dir"]
    agents_dir.mkdir(parents=True, exist_ok=True)
    dest = agents_dir / f"{key}{suffix}"
    result = _make_symlink(dest, ws / _HARNESS_DIR / "agents" / "local" / f"{key}.md")
    if result == "foreign":
        print(f"  │  [foreign] agent '{key}' ({tool}, source: local) — real content already at {dest.relative_to(ws)}, left untouched")
    return result != "foreign"


def scaffold(
    workspace: str,
    tools: list[str],
    create_file_mcp: bool,
    create_file_hooks: bool,
    create_file_setting: bool,
    update_gitignore: bool,
    install_defaults: bool,
    content_repos: list[tuple[str, str]],
    install_wikictl: bool = False,
    behavior_caveman: bool = False,
    skills_include_categories: list[str] | None = None,
    skills_include_keys: list[str] | None = None,
    skills_exclude_categories: list[str] | None = None,
    skills_exclude_keys: list[str] | None = None,
) -> None:
    feature_dir = pathlib.Path(__file__).parent
    ws = pathlib.Path(workspace)

    repo_names = [name for name, _ in content_repos]
    for name in repo_names:
        if name in _RESERVED_SOURCE_NAMES:
            sys.exit(f"contentRepos name '{name}' is reserved (used internally for the bundled/local sources) — choose a different name")
    if len(repo_names) != len(set(repo_names)):
        sys.exit("contentRepos names must be unique")

    repo_paths = [(name, pathlib.Path(path)) for name, path in content_repos]

    # Auto-detected `workspace` source (design.md D2): a `.harness-ai/local/`
    # directory needs no config entry, and — appended last — automatically
    # wins any same-key collision against `default`/`contentRepos` via plain
    # dict-overwrite order in `_load_content`, with zero changes needed there.
    workspace_dir = ws / _HARNESS_DIR / "local"
    if workspace_dir.is_dir():
        repo_paths.append(("workspace", workspace_dir))

    # --- Hash check: skip if nothing changed ---
    digest = _compute_content_hash(feature_dir, [(name, path, None) for name, path in repo_paths])
    if _read_lock(ws) == digest:
        print(f"\n harness-ai  no changes detected skipping (workspace: {ws})\n")
        return

    paths_cfg, agents_by_key, skills_by_key, agents_defaults, skills_defaults, source_order, source_roots = _load_content(
        feature_dir, install_defaults, repo_paths
    )
    filtered_skills_by_key = _apply_skill_filter(
        skills_by_key,
        skills_include_categories or [],
        skills_include_keys or [],
        skills_exclude_categories or [],
        skills_exclude_keys or [],
    )
    local_skills, local_agents = _scan_local_source(ws)
    exclude_key_set = set(skills_exclude_keys or [])
    included_local_skill_keys = sorted(k for k in local_skills if k not in exclude_key_set)

    # Per-source count of skills dropped by the category/key filter — reported
    # in the "filtered" column alongside the (rarer) local/default collision
    # skips, both being reasons a source's content didn't fully materialize.
    skills_filtered_out_by_source: dict[str, int] = {}
    for key, info in skills_by_key.items():
        if key not in filtered_skills_by_key:
            source = info["source"]
            skills_filtered_out_by_source[source] = skills_filtered_out_by_source.get(source, 0) + 1

    active_tools = list(dict.fromkeys([*tools, "agents"]))

    print(f"\n harness-ai  workspace: {ws}")
    enabled = ", ".join(tools) if tools else "none"
    flags = (
        f"mcp={'yes' if create_file_mcp else 'no'}  "
        f"hooks={'yes' if create_file_hooks else 'no'}  "
        f"settings={'yes' if create_file_setting else 'no'}  "
        f"gitignore={'yes' if update_gitignore else 'no'}  "
        f"defaults={'yes' if install_defaults else 'no'}"
    )
    print(f"  tools: {enabled} (+agents, always-on)  |  {flags}\n")

    old_manifest = _read_manifest(ws)
    new_manifest: dict = {}
    gitignore_entries: list[str] = [f"{_HARNESS_DIR}/{_LOCK_FILE}", f"{_HARNESS_DIR}/{_MANIFEST_FILE}"]
    counters: dict[tuple[str, str], dict[str, int]] = {}
    unmanaged_entries: list[pathlib.Path] = []
    removed_counts: dict[tuple[str, str], int] = {}

    def _bump(tool: str, source: str, field: str) -> None:
        c = counters.setdefault((tool, source), {"seen": 0, "linked": 0, "skipped": 0, "foreign": 0})
        c[field] += 1

    def _bump_by(tool: str, source: str, field: str, amount: int) -> None:
        c = counters.setdefault((tool, source), {"seen": 0, "linked": 0, "skipped": 0, "foreign": 0})
        c[field] += amount

    for tool in active_tools:
        if tool not in paths_cfg:
            print(f"  [WARN] unknown tool '{tool}' — no paths config found, skipping.")
            continue

        tool_paths = paths_cfg[tool]
        base = ws / tool_paths["base_dir"]
        extra_files = tool_paths.get("extra_files", {})
        print(f"  ┌─ [{tool.upper()}]  base: {base}")
        new_manifest[tool] = {}

        # --- default/contentRepos skills + agents ---
        for source_name in source_order:
            rendered_skills: list[str] = []
            for key in sorted(k for k, info in filtered_skills_by_key.items() if info["source"] == source_name):
                entry = filtered_skills_by_key[key]["entry"]
                if key in local_skills:
                    # local always wins on a same-key collision (design.md D2)
                    # — for every tool, including the always-on `agents`
                    # profile: rendering here anyway would just get clobbered
                    # a few lines down by _link_local_skill, double-counted
                    # in the report.
                    print(f"  │  [collision] skill '{key}' claimed by local — skipping render from '{source_name}'")
                    _bump(tool, source_name, "skipped")
                    continue
                meta = _tool_meta_for(entry, tool, skills_defaults.get(tool, {}) or {})
                if meta is None:
                    continue
                _bump(tool, source_name, "seen")
                content_root = source_roots[source_name]
                filename = tool_paths["skills"]["filename"]
                content_file = content_root / "skills" / key / filename
                if not content_file.exists():
                    print(f"  │  [WARN] missing content for skill '{key}' (source: {source_name})")
                    continue
                body = content_file.read_text()
                refs_src = content_root / "skills" / key / "references"
                rendered, refs_foreign = _render_skill(ws, tool, tool_paths, source_name, key, meta, body, refs_src if refs_src.exists() else None)
                if rendered:
                    rendered_skills.append(key)
                    _bump(tool, source_name, "linked")
                else:
                    _bump(tool, source_name, "foreign")
                if refs_foreign:
                    _bump(tool, source_name, "foreign")

            rendered_agents: list[str] = []
            for key in sorted(k for k, info in agents_by_key.items() if info["source"] == source_name):
                entry = agents_by_key[key]["entry"]
                if key in local_agents:
                    print(f"  │  [collision] agent '{key}' claimed by local — skipping render from '{source_name}'")
                    _bump(tool, source_name, "skipped")
                    continue
                meta = _tool_meta_for(entry, tool, agents_defaults.get(tool, {}) or {})
                if meta is None:
                    continue
                _bump(tool, source_name, "seen")
                content_root = source_roots[source_name]
                content_file = content_root / "agents" / f"{key}.md"
                if not content_file.exists():
                    print(f"  │  [WARN] missing content for agent '{key}' (source: {source_name})")
                    continue
                body = content_file.read_text()
                rendered = _render_agent(ws, tool, tool_paths, source_name, key, meta, body)
                if rendered:
                    rendered_agents.append(key)
                    _bump(tool, source_name, "linked")
                else:
                    _bump(tool, source_name, "foreign")

            new_manifest[tool][source_name] = {"skills": rendered_skills, "agents": rendered_agents}
            filtered_out = skills_filtered_out_by_source.get(source_name, 0)
            if filtered_out:
                _bump_by(tool, source_name, "skipped", filtered_out)

        # --- Cleanup, BEFORE the local-linking pass (design.md D6a) ---
        # A key migrating from a default/contentRepos/workspace source to
        # `local` needs the old real directory actually removed here, so
        # `local`'s own (structurally different) whole-directory symlink
        # attempt below has a clear path instead of finding stale content
        # and refusing to clobber it as foreign. The "local" preview below
        # (this run's actual scan results, known upfront) is what keeps a
        # still-valid local key from being misdiagnosed as stale merely
        # because the linking pass itself hasn't run yet — found via
        # real-workspace testing (design.md D6a refinement).
        cleanup_preview = {**new_manifest[tool], "local": {"skills": included_local_skill_keys, "agents": sorted(local_agents)}}
        for source_name, cnt in _cleanup_stale_for_tool(ws, tool, old_manifest.get(tool, {}), cleanup_preview, tool_paths).items():
            removed_counts[(tool, source_name)] = cnt

        # --- local skills + agents ---
        # `local` renders into every active tool including `agents` (design.md
        # D3) — `.harness-ai/skills/local`/`.harness-ai/agents/local` is now a
        # real canonical store, never a render target itself, so there's no
        # same-path collision left to special-case for the `agents` profile.
        linked_local_skill_keys: list[str] = []
        for key in included_local_skill_keys:
            _bump(tool, "local", "seen")
            if _link_local_skill(ws, tool_paths, tool, key):
                linked_local_skill_keys.append(key)
                _bump(tool, "local", "linked")
            else:
                _bump(tool, "local", "foreign")
        linked_local_agent_keys: list[str] = []
        for key in sorted(local_agents):
            _bump(tool, "local", "seen")
            if _link_local_agent(ws, tool_paths, tool, key):
                linked_local_agent_keys.append(key)
                _bump(tool, "local", "linked")
            else:
                _bump(tool, "local", "foreign")
        new_manifest[tool]["local"] = {"skills": linked_local_skill_keys, "agents": linked_local_agent_keys}

        # --- Unmanaged tool-dir entries (design.md D6, foreign-entry-safety) ---
        # Independent of any collision above: a directory entry no known
        # source (including `local`) claimed this run, surfaced so it's
        # never silently invisible even when nothing tried to overwrite it.
        known_skill_keys: set[str] = set()
        known_agent_keys: set[str] = set()
        for src_data in new_manifest[tool].values():
            known_skill_keys.update(src_data.get("skills", []))
            known_agent_keys.update(src_data.get("agents", []))

        skills_base = base / tool_paths["skills"]["dir"]
        if skills_base.is_dir():
            for entry in sorted(skills_base.iterdir()):
                if entry.name not in known_skill_keys:
                    unmanaged_entries.append(entry.relative_to(ws))

        agents_scan_dir = base / tool_paths["agents"]["dir"]
        agent_suffix = tool_paths["agents"]["suffix"]
        if agents_scan_dir.is_dir():
            for entry in sorted(agents_scan_dir.iterdir()):
                stem = entry.name[:-len(agent_suffix)] if agent_suffix and entry.name.endswith(agent_suffix) else entry.name
                if stem not in known_agent_keys:
                    unmanaged_entries.append(entry.relative_to(ws))

        skill_count = sum(len(v["skills"]) for v in new_manifest[tool].values())
        agent_count = sum(len(v["agents"]) for v in new_manifest[tool].values())
        print(f"  │  skills ({skill_count})  agents ({agent_count})")

        # --- Settings files ---
        if create_file_setting:
            for ef in extra_files.get("settings", []):
                _copy_extra(feature_dir, ws, ef)
                if ef.get("ignore", False):
                    gitignore_entries.append(ef["dest"])

        # --- Hooks ---
        if create_file_hooks:
            hooks_cfg = tool_paths.get("hooks")
            if hooks_cfg:
                hooks_suffix = pathlib.Path(hooks_cfg["source"]).suffix
                repo_only_roots = {n: r for n, r in source_roots.items() if n != "default"}
                repo_order = [n for n in source_order if n != "default"]
                hooks_src = _resolve_from_sources(repo_only_roots, repo_order, f"hooks/{tool}{hooks_suffix}")
                if not hooks_src:
                    bundled = feature_dir / hooks_cfg["source"]
                    hooks_src = bundled if bundled.exists() else None
                if hooks_src and hooks_src.exists():
                    if tool == "claude":
                        _apply_claude_hooks(ws, hooks_src)
                    elif tool == "opencode":
                        dest = hooks_cfg.get("dest", f".{tool}/hooks.json")
                        _apply_opencode_hook(ws, hooks_src, dest)
                    else:
                        print(f"  │  [WARN] no hooks handler registered for tool '{tool}'")
                else:
                    print(f"  │  [WARN] missing hooks template for '{tool}'")

        print(f"  └─ [{tool.upper()}] done\n")

    # A tool dropped from `tools:` since the previous run still needs its
    # old manifest entries cleaned up, even though it's no longer iterated
    # above (it's not in active_tools) — mirrors the prior single-pass
    # behavior for this case; new_sources is empty, so everything old is stale.
    for tool, tool_old in old_manifest.items():
        if tool in active_tools:
            continue
        tool_paths = paths_cfg.get(tool)
        if not tool_paths:
            continue
        for source_name, cnt in _cleanup_stale_for_tool(ws, tool, tool_old, {}, tool_paths).items():
            removed_counts[(tool, source_name)] = cnt

    # --- Shared MCP file (.mcp.json) ---
    if create_file_mcp:
        repo_only_roots = {n: r for n, r in source_roots.items() if n != "default"}
        mcp_src = _resolve_from_sources(repo_only_roots, [n for n in source_order if n != "default"], "mcp.json")
        if not mcp_src:
            bundled = feature_dir / "config" / "mcp.json"
            mcp_src = bundled if bundled.exists() else None
        mcp_dst = ws / ".mcp.json"
        if mcp_src:
            if mcp_dst.exists():
                print(f"  [skip] .mcp.json  (already exists)")
            else:
                shutil.copy2(mcp_src, mcp_dst)
                print(f"  [copy] {mcp_src.name}  →  .mcp.json")
        else:
            print(f"  [WARN] missing config/mcp.json template")

    # --- Gated wikictl MCP entry ---
    if install_wikictl:
        _merge_wikictl_mcp(ws, feature_dir)

    # --- Shared MCP file (opencode.json) ---
    if create_file_mcp and "opencode" in tools:
        repo_only_roots = {n: r for n, r in source_roots.items() if n != "default"}
        oc_src = _resolve_from_sources(repo_only_roots, [n for n in source_order if n != "default"], "opencode.json")
        if not oc_src:
            bundled = feature_dir / "config" / "opencode.json"
            oc_src = bundled if bundled.exists() else None
        oc_dst = ws / "opencode.json"
        if oc_src:
            if oc_dst.exists():
                print(f"  [skip] opencode.json  (already exists)")
            else:
                shutil.copy2(oc_src, oc_dst)
                print(f"  [copy] {oc_src.name}  →  opencode.json")
        else:
            print(f"  [WARN] missing config/opencode.json template")

    if install_wikictl and "opencode" in tools:
        _merge_wikictl_mcp_opencode(ws, feature_dir)

    if update_gitignore and gitignore_entries:
        _update_gitignore(ws, list(dict.fromkeys(gitignore_entries)))

    all_skill_keys = sorted(set(filtered_skills_by_key) | set(included_local_skill_keys))
    all_agent_keys = sorted(set(agents_by_key) | set(local_agents))
    repo_dirs_only = [path for _, path in repo_paths]
    _update_agents_md(ws, feature_dir, repo_dirs_only, all_skill_keys, all_agent_keys, behavior_caveman)

    # --- Sync summary table (design.md D7, D6/foreign-entry-safety for the
    # `foreign` column) ---
    print("  ── sync summary ──────────────────────────────────────────")
    print(f"  {'tool':<10} {'source':<20} {'seen':>5} {'linked':>7} {'removed':>8} {'filtered':>9} {'foreign':>8}")
    for (tool, source), c in sorted(counters.items()):
        removed = removed_counts.get((tool, source), 0)
        print(f"  {tool:<10} {source:<20} {c['seen']:>5} {c['linked']:>7} {removed:>8} {c['skipped']:>9} {c['foreign']:>8}")
    print("")

    if unmanaged_entries:
        print("  ── unmanaged entries (not overwritten, not tracked) ────────")
        for path in unmanaged_entries:
            print(f"  {path}")
        print("")

    _write_manifest(ws, new_manifest)
    _write_lock(ws, digest)
    print(f"  harness-ai complete\n")


def _flag(value: str) -> bool:
    return value.lower() == "true"


def _parse_csv(value: str) -> list[str]:
    return [t.strip() for t in value.split(",") if t.strip()]


def _parse_name_value(items: list[str]) -> list[tuple[str, str]]:
    result = []
    for item in items:
        if "=" not in item:
            sys.exit(f"expected NAME=VALUE, got: {item}")
        name, value = item.split("=", 1)
        result.append((name, value))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Harness AI: assemble AI assets with tool-specific frontmatter."
    )
    parser.add_argument("--workspace", required=True, help="Target workspace directory")
    parser.add_argument("--tools", default="claude", help="Comma-separated tools to scaffold (e.g. claude,opencode) — 'agents' is always appended")
    parser.add_argument("--create-file-mcp", default="true", help="Create .mcp.json config file (true/false)")
    parser.add_argument("--create-file-hooks", default="true", help="Create and manage hooks files (true/false)")
    parser.add_argument("--create-file-setting", default="true", help="Create settings files (true/false)")
    parser.add_argument("--update-gitignore", default="true", help="Add scaffold paths to .gitignore (true/false)")
    parser.add_argument("--install-defaults", default="true", help="Install bundled default content (true/false)")
    parser.add_argument("--install-wikictl", default="false", help="Add the gated wikictl MCP server to .mcp.json (true/false)")
    parser.add_argument("--behavior-caveman", default="false", help="Inject a caveman-mode-by-default instruction into AGENTS.md (true/false)")
    parser.add_argument("--content-repos", action="append", default=[], metavar="NAME=PATH", help="Repeatable: a named, already-resolved (cloned or local) content-repo checkout")
    parser.add_argument("--content-repo-sha", action="append", default=[], metavar="NAME=SHA", help="Repeatable: pre-computed HEAD SHA (from git ls-remote) for a named content repo; used by --check-only to skip a local git call")
    parser.add_argument("--skills-include-categories", default="", help="Comma-separated category/category.subcategory allowlist")
    parser.add_argument("--skills-include-keys", default="", help="Comma-separated explicit skill-key allowlist")
    parser.add_argument("--skills-exclude-categories", default="", help="Comma-separated category/category.subcategory denylist")
    parser.add_argument("--skills-exclude-keys", default="", help="Comma-separated explicit skill-key denylist")
    parser.add_argument("--check-only", action="store_true", help="Compare content hash against lock file without running scaffold; exits 0 if up-to-date, 1 if stale")
    args = parser.parse_args()

    if args.check_only:
        _feature_dir = pathlib.Path(__file__).parent
        _ws = pathlib.Path(args.workspace)
        _shas = _parse_name_value(args.content_repo_sha)
        _hash_entries: list[tuple[str, pathlib.Path | None, str | None]] = [(name, None, sha) for name, sha in _shas]
        # `workspace` (design.md D2a) has no SHA to precompute — it's a plain
        # local directory, not a git checkout — so the fast check-only path
        # must hash its content directly, exactly like the live-run path in
        # scaffold(), or an edited workspace-source skill would never be
        # detected as changed by `harnessai sync`'s fast path.
        _workspace_dir = _ws / _HARNESS_DIR / "local"
        if _workspace_dir.is_dir():
            _hash_entries.append(("workspace", _workspace_dir, None))
        _digest = _compute_content_hash(_feature_dir, _hash_entries)
        if _read_lock(_ws) == _digest:
            print(f"\n harness-ai  no changes detected, skipping (workspace: {_ws})\n")
            sys.exit(0)
        sys.exit(1)

    scaffold(
        workspace=args.workspace,
        tools=_parse_csv(args.tools),
        create_file_mcp=_flag(args.create_file_mcp),
        create_file_hooks=_flag(args.create_file_hooks),
        create_file_setting=_flag(args.create_file_setting),
        update_gitignore=_flag(args.update_gitignore),
        install_defaults=_flag(args.install_defaults),
        content_repos=_parse_name_value(args.content_repos),
        install_wikictl=_flag(args.install_wikictl),
        behavior_caveman=_flag(args.behavior_caveman),
        skills_include_categories=_parse_csv(args.skills_include_categories),
        skills_include_keys=_parse_csv(args.skills_include_keys),
        skills_exclude_categories=_parse_csv(args.skills_exclude_categories),
        skills_exclude_keys=_parse_csv(args.skills_exclude_keys),
    )
