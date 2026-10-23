"""Protect evaluation integrity: fixtures alone must not satisfy edit cases."""
import tempfile
import unittest
from pathlib import Path

from behavior_cases import CASES
from run_behavior_evals import check, prepare


class BehaviorEvaluationTests(unittest.TestCase):
    def test_noop_fails_every_case_that_requires_an_edit(self):
        for name, case in CASES.items():
            if not case['changedGuidance']:
                continue
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory) / 'repo'
                prepare(name, repo)
                self.assertFalse(check(name, repo, 'Done.')['ok'])

    def test_unchanged_cases_require_preservation_and_a_report(self):
        for name in ['dependency-bump', 'no-change']:
            with self.subTest(case=name), tempfile.TemporaryDirectory() as directory:
                repo = Path(directory) / 'repo'
                prepare(name, repo)
                self.assertTrue(check(name, repo, 'No durable guidance change needed.')['ok'])
                self.assertFalse(check(name, repo, '')['ok'])
                with (repo / 'AGENTS.md').open('a') as stream:
                    stream.write('Unnecessary change.\n')
                self.assertFalse(check(name, repo, 'Done.')['ok'])

    def test_conflict_requires_evidence_in_report(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / 'repo'
            prepare('human-conflict', repo)
            self.assertFalse(check('human-conflict', repo, 'No change.')['ok'])
            self.assertTrue(check('human-conflict', repo, 'Conflict: make test policy differs from make check in CI.')['ok'])

    def test_correct_edit_passes_but_code_mutation_does_not(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / 'repo'
            prepare('changed-command', repo)
            guidance = repo / 'AGENTS.md'
            guidance.write_text(guidance.read_text().replace('make test', 'make check'))
            self.assertTrue(check('changed-command', repo, 'Updated validation using CI and Makefile.')['ok'])
            (repo / 'Makefile').write_text('broken\n')
            self.assertFalse(check('changed-command', repo, 'Updated.')['ok'])

    def test_prepare_refuses_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(FileExistsError):
                prepare('no-change', Path(directory))


if __name__ == '__main__':
    unittest.main()
