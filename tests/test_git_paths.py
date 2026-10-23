"""Exercise real Git output, including names that cannot be line-parsed."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

from test_inspect_repo import Repo, SCRIPT, run

VERIFY = SCRIPT.with_name("verify_agents.py")


class GitPathTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()
        self.repo.write("AGENTS.md", "Run tests.\n")
        self.repo.write("package.json", "{}\n")
        self.base = self.repo.commit("base")

    def tearDown(self):
        self.repo.close()

    def test_unstaged_first_record_keeps_filename_and_signal(self):
        self.repo.write("package.json", '{"private":true}\n')
        self.assertEqual(self.repo.inspect()["workingTreeChanges"], [{
            "path": "package.json", "status": "M", "signals": ["dependencies-tooling"]}])

    def test_new_nested_files_are_enumerated(self):
        self.repo.write("new/package.json", "{}\n")
        self.repo.write("new/scripts/build.py", "pass\n")
        files = {f["path"]: f for f in self.repo.inspect()["workingTreeChanges"]}
        self.assertIn("dependencies-tooling", files["new/package.json"]["signals"])
        self.assertIn("new/scripts/build.py", files)

    def test_names_round_trip_in_working_tree_and_commit(self):
        names = ['space dir/package.json', 'ሰላም/package.json', 'tab\tname.txt', 'line\nname.txt', 'carriage\rname.txt', 'say"hi.txt', 'literal -> name.txt', ' trailing .txt']
        for name in names:
            self.repo.write(name, "content\n")
        self.assertEqual(set(names), {f["path"] for f in self.repo.inspect()["workingTreeChanges"]})
        self.repo.commit("odd paths")
        self.assertEqual(set(names), {f["path"] for f in self.repo.inspect("--baseline", self.base)["changedFiles"]})

    def test_staged_rename_retains_both_paths(self):
        run("git", "mv", "package.json", "new package.json", cwd=self.repo.path)
        working = self.repo.inspect()["workingTreeChanges"]
        self.assertEqual(working[0]["path"], "new package.json")
        self.assertEqual(working[0]["previousPath"], "package.json")
        self.assertIn("dependencies-tooling", working[0]["signals"])
        self.repo.commit("rename")
        changed = self.repo.inspect("--baseline", self.base)["changedFiles"]
        self.assertEqual(changed[0]["path"], "new package.json")
        self.assertEqual(changed[0]["previousPath"], "package.json")
        self.assertIn("dependencies-tooling", changed[0]["signals"])

    def test_staged_and_unstaged_changes_preserve_status(self):
        self.repo.write("package.json", '{"staged":true}\n')
        run("git", "add", "package.json", cwd=self.repo.path)
        self.repo.write("package.json", '{"unstaged":true}\n')
        self.assertEqual(self.repo.inspect()["workingTreeChanges"][0]["status"], "MM")

    def test_subdirectory_and_explicit_repo_match_root(self):
        self.repo.write("AGENTS.md", "Updated guidance.\n")
        self.repo.write("nested/package.json", "{}\n")
        expected = self.repo.inspect()
        nested = self.repo.path / "nested"
        actual = json.loads(run(sys.executable, str(SCRIPT), cwd=nested))
        self.assertEqual(actual, expected)
        actual = json.loads(run(sys.executable, str(SCRIPT), "--repo", str(nested), cwd=SCRIPT.parent))
        self.assertEqual(actual, expected)
        for cwd, args in [(self.repo.path, []), (nested, []), (SCRIPT.parent, ["--repo", str(nested)])]:
            result = json.loads(run(sys.executable, str(VERIFY), *args, cwd=cwd))
            self.assertEqual(result["changedAgentsFiles"][0]["path"], "AGENTS.md")
            self.assertEqual(result["warnings"], [])

    def test_verifier_handles_quoted_nested_guidance(self):
        self.repo.write('ሰላም space/AGENTS.md', "Keep guidance.\n")
        result = json.loads(run(sys.executable, str(VERIFY), cwd=self.repo.path))
        self.assertEqual(result["changedAgentsFiles"][0]["path"], 'ሰላም space/AGENTS.md')
        self.assertEqual(len(result["warnings"]), 1)

    def test_verifier_reports_empty_guidance(self):
        self.repo.write("AGENTS.md", "")
        result = subprocess.run([sys.executable, str(VERIFY)], cwd=self.repo.path, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertFalse(json.loads(result.stdout)["ok"])

    def test_discovery_is_consistent_and_prunes_generated_directories(self):
        for folder in [".venv", "dist", "build", ".next", "node_modules"]:
            self.repo.write(f"{folder}/AGENTS.md", "")
        inspected = self.repo.inspect()["agentsFiles"]
        verified = json.loads(run(sys.executable, str(VERIFY), cwd=self.repo.path))["agentsFiles"]
        self.assertEqual(inspected, ["AGENTS.md"])
        self.assertEqual(verified, inspected)


if __name__ == "__main__":
    unittest.main()
