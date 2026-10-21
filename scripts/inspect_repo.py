#!/usr/bin/env python3
"""Collect deterministic Git evidence for the evolving-agents-md skill.

The script does not decide what belongs in AGENTS.md. It reports repository
facts so an agent can make that judgment.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def classify(path: str) -> list[str]:
    p = path.lower()
    name = Path(p).name
    signals: list[str] = []

    if name in {"package.json", "pyproject.toml", "requirements.txt", "go.mod", "cargo.toml", "gemfile", "composer.json"} or "lock" in name:
        signals.append("dependencies-tooling")
    if any(x in p for x in ("schema", "migration", "prisma", "openapi", "graphql")):
        signals.append("schema-interface")
    if any(x in p for x in (".github/workflows/", "dockerfile", "docker-compose", "deploy", "terraform", "cloudflare")):
        signals.append("build-deploy")
    if name in {"makefile", "justfile", "taskfile.yml", "taskfile.yaml"} or p.startswith("scripts/"):
        signals.append("commands-workflow")
    if any(x in p for x in ("eslint", "prettier", "biome", "ruff", "pytest", "vitest", "jest", "tsconfig")):
        signals.append("validation-conventions")
    if name == "agents.md":
        signals.append("agent-guidance")

    return signals


def discover_agents(root: Path) -> list[str]:
    ignored = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next"}
    found: list[str] = []
    for path in root.rglob("AGENTS.md"):
        if any(part in ignored for part in path.parts):
            continue
        found.append(path.relative_to(root).as_posix())
    return sorted(found)


def changed_files(baseline: str | None) -> list[dict[str, object]]:
    if baseline:
        output = git("diff", "--name-status", f"{baseline}..HEAD")
    else:
        # Without a trustworthy baseline, report current working-tree changes.
        output = git("status", "--short")

    files: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if baseline:
            parts = line.split("\t")
            status = parts[0]
            path = parts[-1]
        else:
            status = line[:2].strip() or "modified"
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
        files.append({"path": path, "status": status, "signals": classify(path)})
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Git evidence relevant to AGENTS.md maintenance")
    parser.add_argument("--baseline", help="Commit, tag, branch, or other Git ref to compare with HEAD")
    args = parser.parse_args()

    try:
        root_text = git("rev-parse", "--show-toplevel")
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2

    root = Path(root_text)
    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current", check=False) or None

    baseline = args.baseline
    baseline_source = "user" if baseline else None
    baseline_sha = None
    if baseline:
        try:
            baseline_sha = git("rev-parse", "--verify", f"{baseline}^{{commit}}")
        except RuntimeError as exc:
            print(json.dumps({"error": f"Invalid baseline {baseline!r}: {exc}"}))
            return 2

    files = changed_files(baseline_sha)
    evidence = {
        "repositoryRoot": str(root),
        "branch": branch,
        "head": head,
        "baseline": baseline_sha,
        "baselineSource": baseline_source,
        "agentsFiles": discover_agents(root),
        "changedFiles": files,
        "highSignalFiles": [item for item in files if item["signals"]],
        "note": (
            "No baseline supplied. Working-tree changes are reported; the agent must use Git history and current repository state to choose further evidence."
            if not baseline
            else "Changes are reported from the supplied baseline through HEAD."
        ),
    }
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
