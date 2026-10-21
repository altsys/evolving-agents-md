#!/usr/bin/env python3

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "inspect_repo.py"


def run(*args: str, cwd: Path, check: bool = True) -> str:
    result = subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode != 0:
        raise AssertionError(result.stderr or result.stdout)
    return result.stdout.strip()


class Repo:
    def __init__(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        run("git", "init", "-q", cwd=self.path)
        run("git", "config", "user.email", "test@example.com", cwd=self.path)
        run("git", "config", "user.name", "Test User", cwd=self.path)

    def close(self):
        self.temp.cleanup()

    def write(self, path: str, content: str):
        target = self.path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def commit(self, message: str) -> str:
        run("git", "add", "-A", cwd=self.path)
        run("git", "commit", "-qm", message, cwd=self.path)
        return run("git", "rev-parse", "HEAD", cwd=self.path)

    def inspect(self, *args: str) -> dict:
        output = run(sys.executable, str(SCRIPT), *args, cwd=self.path)
        return json.loads(output)


class BaselineDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def test_explicit_baseline_wins(self):
        self.repo.write("README.md", "one\n")
        root = self.repo.commit("root")
        self.repo.write("package.json", '{"scripts":{"test":"echo ok"}}\n')
        self.repo.commit("tooling")

        result = self.repo.inspect("--baseline", root)
        self.assertEqual(result["baseline"]["source"], "user")
        self.assertEqual(result["baseline"]["sha"], root)
        self.assertIn("package.json", [f["path"] for f in result["highSignalFiles"]])

    def test_last_agents_change_is_default_boundary(self):
        self.repo.write("README.md", "one\n")
        self.repo.commit("root")
        self.repo.write("AGENTS.md", "Use npm test.\n")
        agents_commit = self.repo.commit("add guidance")
        self.repo.write("package.json", '{"scripts":{"test":"vitest"}}\n')
        self.repo.commit("change tooling")

        result = self.repo.inspect()
        self.assertEqual(result["baseline"]["source"], "last-agents-change")
        self.assertEqual(result["baseline"]["sha"], agents_commit)

    def test_no_agents_file_falls_back_to_root(self):
        self.repo.write("README.md", "one\n")
        root = self.repo.commit("root")
        self.repo.write("src/app.py", "print('hi')\n")
        self.repo.commit("app")

        result = self.repo.inspect()
        self.assertEqual(result["baseline"]["source"], "repository-root")
        self.assertEqual(result["baseline"]["sha"], root)
        self.assertEqual(result["agentsFiles"], [])

    def test_uncommitted_changes_are_reported_separately(self):
        self.repo.write("AGENTS.md", "Run tests.\n")
        self.repo.commit("root guidance")
        self.repo.write("package.json", '{"scripts":{"test":"pytest"}}\n')

        result = self.repo.inspect()
        working = {f["path"]: f for f in result["workingTreeChanges"]}
        self.assertIn("package.json", working)
        self.assertIn("dependencies-tooling", working["package.json"]["signals"])

    def test_diverged_upstream_uses_merge_base(self):
        self.repo.write("README.md", "base\n")
        base = self.repo.commit("base")
        main_branch = run("git", "branch", "--show-current", cwd=self.repo.path)

        remote_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, remote_dir, True)
        run("git", "init", "--bare", "-q", str(remote_dir), cwd=self.repo.path)
        run("git", "remote", "add", "origin", str(remote_dir), cwd=self.repo.path)
        run("git", "push", "-q", "-u", "origin", main_branch, cwd=self.repo.path)

        run("git", "checkout", "-qb", "feature", cwd=self.repo.path)
        run("git", "branch", "--set-upstream-to", f"origin/{main_branch}", "feature", cwd=self.repo.path)
        self.repo.write("package.json", '{}\n')
        self.repo.commit("feature work")

        result = self.repo.inspect()
        self.assertEqual(result["baseline"]["source"], "upstream-merge-base")
        self.assertEqual(result["baseline"]["sha"], base)


if __name__ == "__main__":
    unittest.main()
