#!/usr/bin/env python3
"""Check AGENTS.md structure; semantic correctness requires agent review."""
from __future__ import annotations

import argparse
import json
import re

from repo_git import GitRepo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Target repository or a directory within it")
    args = parser.parse_args()
    try:
        repo = GitRepo(args.repo)
        tracked = set(repo.git("ls-files", "-z", raw=True).split("\0"))
        agents = repo.agents_files()
        working = repo.working_tree_files()
        changed_agents = [item for item in working
                          if item["path"].split("/")[-1] == "AGENTS.md"
                          or item.get("previousPath", "").split("/")[-1] == "AGENTS.md"]
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 2

    marker_records = repo.git("check-attr", "-z", "conflict-marker-size", "--", *agents, raw=True).split("\0") if agents else []
    marker_sizes = {}
    for index in range(0, len(marker_records) - 2, 3):
        path, _, value = marker_records[index:index + 3]
        marker_sizes[path] = int(value) if value.isdecimal() and int(value) > 0 else 7

    errors = []
    warnings = []
    for item in changed_agents:
        if item["status"] in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}:
            errors.append(f"{item['path']} has unresolved Git index conflicts.")
    if not agents:
        warnings.append("No AGENTS.md file exists in the repository.")
    for item in changed_agents:
        for relative in (item["path"], item.get("previousPath", "")):
            if relative.split("/")[-1] == "AGENTS.md" and not (repo.root / relative).exists():
                warnings.append(f"{relative} was removed; review whether its guidance is still needed.")
    for relative in agents:
        try:
            content = (repo.root / relative).read_text(encoding="utf-8")
            if not content.strip():
                errors.append(f"{relative} is empty or whitespace-only.")
            size = min(marker_sizes.get(relative, 7), 7)
            if re.search(rf"^(?:<{{{size},}} |>{{{size},}} |\|{{{size},}} )", content, flags=re.MULTILINE):
                errors.append(f"{relative} contains unresolved merge-conflict markers.")
        except (OSError, UnicodeError) as exc:
            errors.append(f"{relative} could not be read as UTF-8: {exc}")
        if relative not in tracked:
            warnings.append(f"{relative} is not tracked by Git.")
    print(json.dumps({
        "ok": not errors,
        "agentsFiles": agents,
        "guidanceScopes": repo.guidance_scopes(agents),
        "verificationLevel": "structural-only",
        "changedAgentsFiles": changed_agents,
        "workingTreeChanges": working,
        "errors": errors,
        "warnings": warnings,
        "semanticVerificationRequired": True,
        "note": "Verify every changed instruction against current repository evidence; this script does not judge prose semantics.",
    }, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
