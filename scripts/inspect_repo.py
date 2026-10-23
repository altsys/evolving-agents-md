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


def boundary(sha: str | None, source: str, confidence: str, reason: str) -> dict:
    return {"sha": sha, "source": source, "confidence": confidence, "reason": reason}


def discover_baseline(repo: GitRepo, agents_files: list[str], head: str | None, shallow: bool) -> dict:
    """Select a discovery boundary without treating truncated history as complete."""
    git = repo.git
    if head is None:
        return boundary(None, "no-commits", "none", "The repository has no commits. Review current files and working-tree changes directly.")
    if shallow:
        return boundary(None, "shallow-history", "none", "History is shallow; visible roots and guidance edits may be truncated. Review current repository state without inventing a reconciliation boundary.")

    upstream = git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", check=False)
    branch_boundary = None
    if upstream:
        merge_base = git("merge-base", "HEAD", upstream, check=False)
        upstream_head = git("rev-parse", upstream, check=False)
        if merge_base and upstream_head and head != upstream_head and merge_base != head:
            branch_boundary = merge_base

    # A recent nested edit is not evidence that older root/sibling guidance was
    # reconciled. Retain the common ancestor of every current scope's boundary.
    guidance_boundaries = [git("log", "-1", "--format=%H", "--", f":(literal){path}", check=False)
                           for path in agents_files]
    guidance_complete = bool(guidance_boundaries) and all(guidance_boundaries)
    boundaries = list(dict.fromkeys(guidance_boundaries)) if guidance_complete else []
    if branch_boundary and (not agents_files or guidance_complete):
        boundaries.append(branch_boundary)
    if boundaries:
        boundaries = list(dict.fromkeys(boundaries))
        candidate = boundaries[0] if len(boundaries) == 1 else git("merge-base", "--octopus", *boundaries, check=False)
        if candidate and candidate != head:
            if branch_boundary and candidate == branch_boundary:
                return boundary(candidate, "upstream-merge-base", "high", f"Using the merge-base with {upstream}, conservatively combined with existing guidance boundaries.")
            source = "last-agents-change" if len(set(guidance_boundaries)) == 1 else "guidance-merge-base"
            return boundary(candidate, source, "medium", "Using a common ancestor of the latest edits to each current guidance scope and any branch boundary. This is a discovery heuristic, not proof that earlier changes were reconciled.")

    roots = git("rev-list", "--max-parents=0", "HEAD").splitlines()
    if len(roots) == 1:
        return boundary(roots[0], "repository-root", "low", "No stronger boundary was found. Review current state as well as history: the root-to-HEAD diff omits files introduced in the root commit.")
    return boundary(None, "multiple-roots", "none", "History has multiple roots and no common reconciliation boundary. Review current repository state directly.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect Git evidence relevant to AGENTS.md maintenance")
    parser.add_argument("--baseline", help="Commit, tag, branch, or other Git ref to compare with HEAD")
    parser.add_argument("--repo", default=".", help="Target repository or a directory within it (default: current directory)")
    args = parser.parse_args()

    try:
        repo = GitRepo(args.repo)
        git = repo.git
        root = repo.root
        head = git("rev-parse", "--verify", "HEAD", check=False) or None
        shallow = git("rev-parse", "--is-shallow-repository") == "true"
    except RuntimeError as exc:
        print(json.dumps({"error": str(exc)}))
        return 2

    branch = git("branch", "--show-current", check=False) or None
    agents_files = repo.agents_files()

    if args.baseline:
        try:
            baseline_info = {
                "sha": git("rev-parse", "--verify", "--end-of-options", f"{args.baseline}^{{commit}}"),
                "source": "user",
                "confidence": "explicit",
                "reason": f"User supplied baseline {args.baseline!r}.",
            }
        except RuntimeError as exc:
            print(json.dumps({"error": f"Invalid baseline {args.baseline!r}: {exc}"}))
            return 2
    else:
        baseline_info = discover_baseline(repo, agents_files, head, shallow)

    baseline_sha = baseline_info["sha"]

    def add_signals(items):
        return [
            {**item, "signals": sorted(set(classify(item["path"]) + classify(item.get("previousPath", ""))))}
            for item in items
        ]

    files = add_signals(repo.changed_files(baseline_sha)) if baseline_sha and head else []
    working = add_signals(repo.working_tree_files())
    current_review = not agents_files or shallow or baseline_info["source"] in {"no-commits", "shallow-history", "repository-root", "multiple-roots"}
    current_files = repo.current_files() if current_review else []
    current_signals = [{"path": path, "signals": classify(path)} for path in current_files if classify(path)]
    removed_guidance = sorted({path for item in files + working
                               for path in (item["path"], item.get("previousPath", ""))
                               if Path(path).name == "AGENTS.md" and not (root / path).exists()})
    warnings = []
    if shallow:
        warnings.append("Git history is shallow. No network fetch was attempted; current-state review is required.")
    evidence = {
        "repositoryRoot": str(root),
        "branch": branch,
        "head": head,
        "baseline": baseline_info,
        "agentsFiles": agents_files,
        "guidanceScopes": repo.guidance_scopes(agents_files),
        "deletedAgentsFiles": removed_guidance,
        "historyComplete": not shallow,
        "currentStateReviewRequired": current_review,
        "currentFiles": current_files,
        "currentHighSignalFiles": current_signals,
        "warnings": warnings,
        "changedFiles": files,
        "highSignalFiles": [item for item in files if item["signals"]],
        "workingTreeChanges": working,
        "note": "Automatic baselines are discovery boundaries, not proof that older AGENTS.md guidance is complete. Current repository state remains the source of truth.",
    }
    print(json.dumps(evidence, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
