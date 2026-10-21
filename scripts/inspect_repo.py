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
        ["git", *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
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
    return sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("AGENTS.md")
        if not any(part in ignored for part in path.parts)
    )


def resolve_ref(ref: str) -> str:
    return git("rev-parse", "--verify", f"{ref}^{{commit}}")


def discover_baseline(agents_files: list[str], head: str) -> dict[str, str | None]:
    """Choose a conservative automatic baseline using Git-only evidence.

    Preference order:
    1. A diverged upstream branch's merge-base, which represents the start of
       the current branch's work.
    2. The most recent commit that changed an existing AGENTS.md, treated only
       as a heuristic reconciliation boundary.
    3. The repository root commit, which is expensive but avoids silently
       pretending a newer trustworthy boundary exists.
    """
    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False)
    if upstream:
        merge_base = git("merge-base", "HEAD", upstream, check=False)
        upstream_head = git("rev-parse", upstream, check=False)
        if merge_base and upstream_head and head != upstream_head and merge_base != head:
            return {
                "sha": merge_base,
                "source": "upstream-merge-base",
                "confidence": "high",
                "reason": f"Current branch diverges from {upstream}; using their merge-base.",
            }

    if agents_files:
        last_agents_commit = git("log", "-1", "--format=%H", "--", *agents_files, check=False)
        if last_agents_commit and last_agents_commit != head:
            return {
                "sha": last_agents_commit,
                "source": "last-agents-change",
                "confidence": "medium",
                "reason": "Using the last commit that changed an applicable AGENTS.md as a discovery boundary. This does not prove all earlier changes were reconciled.",
            }

    root_commit = git("rev-list", "--max-parents=0", "HEAD", check=False).splitlines()
    if root_commit:
        return {
            "sha": root_commit[0],
            "source": "repository-root",
            "confidence": "low",
            "reason": "No stronger Git-only reconciliation boundary was found; using repository history from the root commit.",
        }

    return {
        "sha": None,
        "source": "none",
        "confidence": "none",
        "reason": "Git did not provide a usable automatic baseline. Reconcile current repository state directly.",
    }


def changed_files(baseline: str | None) -> list[dict[str, object]]:
    output = git("diff", "--name-status", f"{baseline}..HEAD") if baseline else git("status", "--short")
    files: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        if baseline:
            parts = line.split("\t")
            status, path = parts[0], parts[-1]
        else:
            status = line[:2].strip() or "modified"
            path = line[3:].strip()
            if " -> " in path:
                path = path.split(" -> ", 1)[1]
        files.append({"path": path, "status": status, "signals": classify(path)})
    return files


def working_tree_files() -> list[dict[str, object]]:
    output = git("status", "--short")
    files: list[dict[str, object]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
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
        root = Path(git("rev-parse", "--show-toplevel"))
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2

    head = git("rev-parse", "HEAD")
    branch = git("branch", "--show-current", check=False) or None
    agents_files = discover_agents(root)

    if args.baseline:
        try:
            baseline_info = {
                "sha": resolve_ref(args.baseline),
                "source": "user",
                "confidence": "explicit",
                "reason": f"User supplied baseline {args.baseline!r}.",
            }
        except RuntimeError as exc:
            print(json.dumps({"error": f"Invalid baseline {args.baseline!r}: {exc}"}))
            return 2
    else:
        baseline_info = discover_baseline(agents_files, head)

    baseline_sha = baseline_info["sha"]
    files = changed_files(baseline_sha)
    working = working_tree_files()
    evidence = {
        "repositoryRoot": str(root),
        "branch": branch,
        "head": head,
        "baseline": baseline_info,
        "agentsFiles": agents_files,
        "changedFiles": files,
        "highSignalFiles": [item for item in files if item["signals"]],
        "workingTreeChanges": working,
        "note": "Automatic baselines are discovery boundaries, not proof that older AGENTS.md guidance is complete. Current repository state remains the source of truth.",
    }
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
