#!/usr/bin/env python3
"""Run structural checks after an agent edits AGENTS.md.

Semantic correctness remains the agent's responsibility. This script catches
basic repository and scoping problems deterministically.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def main() -> int:
    try:
        root = Path(git("rev-parse", "--show-toplevel"))
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "errors": [str(exc)]}, indent=2))
        return 2

    tracked = set(git("ls-files").splitlines())
    agents = sorted(
        p.relative_to(root).as_posix()
        for p in root.rglob("AGENTS.md")
        if ".git" not in p.parts and "node_modules" not in p.parts
    )

    errors: list[str] = []
    warnings: list[str] = []

    if not agents:
        warnings.append("No AGENTS.md file exists in the repository.")

    for relative in agents:
        path = root / relative
        if path.stat().st_size == 0:
            errors.append(f"{relative} is empty.")
        if relative not in tracked:
            warnings.append(f"{relative} is not tracked by Git.")

    changed = git("status", "--short").splitlines()
    changed_agents = [line for line in changed if line[3:].strip().endswith("AGENTS.md")]

    result = {
        "ok": not errors,
        "agentsFiles": agents,
        "changedAgentsFiles": changed_agents,
        "errors": errors,
        "warnings": warnings,
        "semanticVerificationRequired": True,
        "note": "Verify every changed instruction against current repository evidence; this script does not judge prose semantics.",
    }
    print(json.dumps(result, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
