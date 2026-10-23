"""History fallbacks must expose evidence without inventing a review boundary."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_inspect_repo import Repo, SCRIPT, run


class GitHistoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def test_empty_repository_is_a_successful_current_state_review(self):
        result = self.repo.inspect()
        self.assertIsNone(result['head'])
        self.assertIsNone(result['baseline']['sha'])
        self.assertEqual(result['baseline']['source'], 'no-commits')
        self.assertTrue(result['currentStateReviewRequired'])
        self.assertEqual(result['changedFiles'], [])

    def test_unborn_repository_reports_staged_and_untracked_files(self):
        self.repo.write('package.json', '{}\n')
        run('git', 'add', 'package.json', cwd=self.repo.path)
        self.repo.write('new/AGENTS.md', 'Preserve local policy.\n')
        result = self.repo.inspect()
        self.assertEqual(set(result['currentFiles']), {'package.json', 'new/AGENTS.md'})
        self.assertEqual({item['path'] for item in result['workingTreeChanges']}, set(result['currentFiles']))
        self.assertIn('package.json', [item['path'] for item in result['currentHighSignalFiles']])

    def test_initial_commit_files_are_available_even_when_diff_is_empty(self):
        self.repo.write('package.json', '{}\n')
        self.repo.commit('initial tooling')
        result = self.repo.inspect()
        self.assertEqual(result['changedFiles'], [])
        self.assertTrue(result['currentStateReviewRequired'])
        self.assertEqual(result['currentHighSignalFiles'][0]['path'], 'package.json')

    def test_invalid_baseline_is_a_structured_error_including_without_commits(self):
        for with_commit in [False, True]:
            with self.subTest(with_commit=with_commit):
                if with_commit:
                    self.repo.write('README.md', 'repo\n')
                    self.repo.commit('root')
                result = subprocess.run([sys.executable, str(SCRIPT), '--baseline', 'not-a-real-ref'], cwd=self.repo.path, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn('Invalid baseline', json.loads(result.stdout)['error'])
                self.assertNotIn('Traceback', result.stderr)

    def shallow_clone(self):
        self.repo.write('AGENTS.md', 'Initial guidance.\n')
        root = self.repo.commit('root')
        self.repo.write('package.json', '{}\n')
        self.repo.commit('tooling')
        self.repo.write('README.md', 'current\n')
        self.repo.commit('latest')
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        clone = Path(folder.name) / 'clone'
        run('git', 'clone', '-q', '--depth=1', self.repo.path.as_uri(), str(clone), cwd=self.repo.path)
        return clone, root

    def test_shallow_clone_does_not_call_its_boundary_a_repository_root(self):
        clone, _ = self.shallow_clone()
        result = json.loads(run(sys.executable, str(SCRIPT), cwd=clone))
        self.assertFalse(result['historyComplete'])
        self.assertEqual(result['baseline']['source'], 'shallow-history')
        self.assertIsNone(result['baseline']['sha'])
        self.assertEqual(result['changedFiles'], [])
        self.assertTrue(result['currentStateReviewRequired'])
        self.assertIn('package.json', result['currentFiles'])
        self.assertTrue(result['warnings'])
        self.assertEqual(run('git', 'rev-parse', '--is-shallow-repository', cwd=clone), 'true')

    def test_shallow_clone_honors_available_explicit_baseline(self):
        clone, _ = self.shallow_clone()
        head = run('git', 'rev-parse', 'HEAD', cwd=clone)
        result = json.loads(run(sys.executable, str(SCRIPT), '--baseline', head, cwd=clone))
        self.assertEqual(result['baseline']['source'], 'user')
        self.assertEqual(result['baseline']['sha'], head)
        self.assertTrue(result['currentStateReviewRequired'])
        self.assertFalse(result['historyComplete'])

    def test_missing_shallow_baseline_does_not_silently_substitute(self):
        clone, root = self.shallow_clone()
        result = subprocess.run([sys.executable, str(SCRIPT), '--baseline', root], cwd=clone, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn(root, json.loads(result.stdout)['error'])

    def test_detached_head_preserves_baseline_and_changes(self):
        self.repo.write('AGENTS.md', 'Run tests.\n')
        baseline = self.repo.commit('guidance')
        self.repo.write('package.json', '{}\n')
        head = self.repo.commit('tooling')
        run('git', 'checkout', '--detach', '-q', head, cwd=self.repo.path)
        result = self.repo.inspect()
        self.assertIsNone(result['branch'])
        self.assertEqual(result['baseline']['sha'], baseline)
        self.assertEqual(result['changedFiles'][0]['path'], 'package.json')

    def test_deleting_all_guidance_is_reported(self):
        self.repo.write('AGENTS.md', 'Run tests.\n')
        self.repo.commit('guidance')
        (self.repo.path / 'AGENTS.md').unlink()
        self.repo.commit('delete guidance')
        result = self.repo.inspect()
        self.assertEqual(result['agentsFiles'], [])
        self.assertEqual(result['deletedAgentsFiles'], ['AGENTS.md'])
        self.assertTrue(result['currentStateReviewRequired'])

    def test_unstaged_deletion_and_rename_of_guidance_are_reported(self):
        self.repo.write('AGENTS.md', 'Run tests.\n')
        self.repo.commit('guidance')
        run('git', 'mv', 'AGENTS.md', 'instructions.md', cwd=self.repo.path)
        result = self.repo.inspect()
        self.assertEqual(result['deletedAgentsFiles'], ['AGENTS.md'])

    def test_recent_nested_edit_cannot_hide_older_root_or_sibling_changes(self):
        self.repo.write('AGENTS.md', 'Root policy.\n')
        oldest = self.repo.commit('root guidance')
        self.repo.write('package.json', '{"scripts":{"test":"new-command"}}\n')
        self.repo.commit('root tooling changed')
        self.repo.write('services/api/AGENTS.md', 'API policy.\n')
        self.repo.write('services/web/AGENTS.md', 'Web policy.\n')
        self.repo.commit('nested guidance')
        self.repo.write('services/web/package.json', '{}\n')
        self.repo.commit('web tooling changed')
        self.repo.write('services/api/AGENTS.md', 'Updated API policy.\n')
        self.repo.commit('only API guidance reviewed')
        self.repo.write('services/api/Makefile', 'check:\n\ttrue\n')
        self.repo.commit('API tooling changed')
        result = self.repo.inspect()
        self.assertEqual(result['baseline']['sha'], oldest)
        self.assertEqual(result['baseline']['source'], 'guidance-merge-base')
        changed = {item['path'] for item in result['changedFiles']}
        self.assertIn('package.json', changed)
        self.assertIn('services/web/package.json', changed)
        self.assertIn('services/api/Makefile', changed)

    def test_literal_guidance_paths_do_not_expand_as_git_globs(self):
        self.repo.write('README.md', 'root\n')
        self.repo.commit('root')
        self.repo.write('service[1]/AGENTS.md', 'Local policy.\n')
        boundary = self.repo.commit('guidance with bracketed path')
        self.repo.write('service[1]/package.json', '{}\n')
        self.repo.commit('tooling')
        self.assertEqual(self.repo.inspect()['baseline']['sha'], boundary)

    def test_multiple_unrelated_roots_require_current_state_review(self):
        self.repo.write('README.md', 'first\n')
        self.repo.commit('first root')
        first_branch = run('git', 'branch', '--show-current', cwd=self.repo.path)
        run('git', 'checkout', '--orphan', 'unrelated', cwd=self.repo.path)
        run('git', 'rm', '-rf', '.', cwd=self.repo.path)
        self.repo.write('package.json', '{}\n')
        self.repo.commit('second root')
        run('git', 'merge', '--allow-unrelated-histories', '-m', 'join roots', first_branch, cwd=self.repo.path)
        result = self.repo.inspect()
        self.assertEqual(result['baseline']['source'], 'multiple-roots')
        self.assertIsNone(result['baseline']['sha'])
        self.assertTrue(result['currentStateReviewRequired'])
        self.assertIn('package.json', result['currentFiles'])


if __name__ == '__main__':
    unittest.main()
