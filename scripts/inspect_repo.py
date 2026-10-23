#!/usr/bin/env python3
"""Collect deterministic Git evidence for the evolving-agents-md skill.

The script does not decide what belongs in AGENTS.md. It reports repository
facts so an agent can make that judgment.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from repo_git import GitRepo


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


def discover_baseline(repo: GitRepo, agents_files: list[str], head: str) -> dict[str, str | None]:
    """Choose a conservative automatic baseline using Git-only evidence.

    Preference order:
    1. A diverged upstream branch's merge-base, which represents the start of
       the current branch's work.
    2. The most recent commit that changed an existing AGENTS.md, treated only
       as a heuristic reconciliation boundary.
    3. The repository root commit, which is expensive but avoids silently
       pretending a newer trustworthy boundary exists.
    """
    git = repo.git
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Git evidence relevant to AGENTS.md maintenance")
    parser.add_argument("--baseline", help="Commit, tag, branch, or other Git ref to compare with HEAD")
    parser.add_argument("--repo", default=".", help="Target repository or a directory within it (default: current directory)")
    args = parser.parse_args()

    try:
        repo = GitRepo(args.repo)
        git = repo.git
        root = repo.root
        head = git("rev-parse", "HEAD")
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2

    branch = git("branch", "--show-current", check=False) or None
    agents_files = repo.agents_files()

    if args.baseline:
        try:
            baseline_info = {
                "sha": git("rev-parse", "--verify", f"{args.baseline}^{{commit}}"),
                "source": "user",
                "confidence": "explicit",
                "reason": f"User supplied baseline {args.baseline!r}.",
            }
        except RuntimeError as exc:
            print(json.dumps({"error": f"Invalid baseline {args.baseline!r}: {exc}"}))
            return 2
    else:
        baseline_info = discover_baseline(repo, agents_files, head)

    baseline_sha = baseline_info["sha"]

    def add_signals(items):
        return [
            {**item, "signals": sorted(set(classify(item["path"]) + classify(item.get("previousPath", ""))))}
            for item in items
        ]

    files = add_signals(repo.changed_files(baseline_sha))
    working = add_signals(repo.working_tree_files())
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
