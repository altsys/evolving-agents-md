"""Shared repository discovery and lossless Git path handling."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

IGNORED_DIRECTORIES = {".git", "node_modules", ".venv", "venv", "dist", "build", ".next"}


class GitRepo:
    def __init__(self, directory: str | Path = "."):
        self.root = Path(directory).resolve()
        self.root = Path(self.git("rev-parse", "--show-toplevel"))

    def git(self, *args: str, check: bool = True, raw: bool = False) -> str:
        result = subprocess.run(
            ["git", "-C", str(self.root), *args],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=False,
        )
        stdout = result.stdout.decode("utf-8", errors="surrogateescape")
        stderr = result.stderr.decode("utf-8", errors="surrogateescape")
        if result.returncode:
            if check:
                raise RuntimeError(stderr.strip() or f"git {args[0]} failed")
            return ""
        return stdout if raw else stdout.removesuffix("\n")

    def agents_files(self) -> list[str]:
        files = []
        for directory, subdirs, names in os.walk(self.root):
            subdirs[:] = [name for name in subdirs if name not in IGNORED_DIRECTORIES]
            if "AGENTS.md" in names:
                files.append((Path(directory) / "AGENTS.md").relative_to(self.root).as_posix())
        return sorted(files)

    def current_files(self) -> list[str]:
        paths = self.git("ls-files", "--cached", "--others", "--exclude-standard", "-z", raw=True)
        return sorted({path for path in paths.split("\0") if path and (self.root / path).is_file()})

    def guidance_scopes(self, agents: list[str]) -> list[dict[str, str | None]]:
        scopes = []
        known = set(agents)
        for relative in agents:
            directory = Path(relative).parent
            parents = [parent / "AGENTS.md" for parent in directory.parents]
            parent = next((path.as_posix() for path in parents if path.as_posix() in known), None)
            scopes.append({"path": relative, "directory": directory.as_posix(), "parent": parent})
        return scopes

    def working_tree_files(self) -> list[dict[str, str]]:
        records = self.git("status", "--porcelain=v1", "-z", "--untracked-files=all", raw=True).split("\0")
        files = []
        index = 0
        while index < len(records) and records[index]:
            record = records[index]
            index += 1
            status, path = record[:2], record[3:]
            entry = {"path": path, "status": status.strip()}
            if "R" in status or "C" in status:
                # Porcelain -z emits destination first, then source.
                entry["previousPath"] = records[index]
                index += 1
            files.append(entry)
        return files

    def changed_files(self, baseline: str | None) -> list[dict[str, str]]:
        if not baseline:
            return self.working_tree_files()
        records = self.git("diff", "--name-status", "-z", "--find-renames", f"{baseline}..HEAD", "--", raw=True).split("\0")
        files = []
        index = 0
        while index < len(records) and records[index]:
            status, path = records[index:index + 2]
            index += 2
            entry = {"path": path, "status": status}
            if status.startswith(("R", "C")):
                entry["previousPath"] = path
                entry["path"] = records[index]
                index += 1
            files.append(entry)
        return files
