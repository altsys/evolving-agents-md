#!/usr/bin/env python3
"""Check AGENTS.md structure; semantic correctness requires agent review."""
from __future__ import annotations

import argparse
import json

from repo_git import GitRepo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Target repository or a directory within it")
    args = parser.parse_args()
    try:
        repo = GitRepo(args.repo)
        tracked = set(repo.git("ls-files", "-z", raw=True).split("\0"))
        agents = repo.agents_files()
        changed_agents = [item for item in repo.working_tree_files()
                          if item["path"].split("/")[-1] == "AGENTS.md"
                          or item.get("previousPath", "").split("/")[-1] == "AGENTS.md"]
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 2

    errors = []
    warnings = []
    if not agents:
        warnings.append("No AGENTS.md file exists in the repository.")
    for relative in agents:
        if (repo.root / relative).stat().st_size == 0:
            errors.append(f"{relative} is empty.")
        if relative not in tracked:
            warnings.append(f"{relative} is not tracked by Git.")
    print(json.dumps({
        "ok": not errors,
        "agentsFiles": agents,
        "changedAgentsFiles": changed_agents,
        "errors": errors,
        "warnings": warnings,
        "semanticVerificationRequired": True,
        "note": "Verify every changed instruction against current repository evidence; this script does not judge prose semantics.",
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
