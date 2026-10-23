"""Structural checks have clear failure modes and never certify prose semantics."""
import json
import subprocess
import sys
import unittest

from test_inspect_repo import Repo, SCRIPT, run

VERIFY = SCRIPT.with_name('verify_agents.py')


class GuidanceVerificationTests(unittest.TestCase):
    def setUp(self):
        self.repo = Repo()

    def tearDown(self):
        self.repo.close()

    def verify(self, code=0):
        result = subprocess.run([sys.executable, str(VERIFY)], cwd=self.repo.path, capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def test_no_guidance_is_a_warning_even_in_unborn_repository(self):
        result = self.verify()
        self.assertTrue(result['ok'])
        self.assertTrue(result['warnings'])
        self.assertEqual(result['verificationLevel'], 'structural-only')
        self.assertTrue(result['semanticVerificationRequired'])

    def test_scope_hierarchy_is_shared_with_inspector(self):
        for path in ['AGENTS.md', 'services/api/AGENTS.md', 'services/api/private/AGENTS.md', 'services/web/AGENTS.md']:
            self.repo.write(path, 'Scope guidance.\n')
        self.repo.commit('guidance')
        result = self.verify()
        self.assertEqual(result['warnings'], [])
        self.assertEqual(result['guidanceScopes'], self.repo.inspect()['guidanceScopes'])
        parents = {item['path']: item['parent'] for item in result['guidanceScopes']}
        self.assertEqual(parents, {
            'AGENTS.md': None,
            'services/api/AGENTS.md': 'AGENTS.md',
            'services/api/private/AGENTS.md': 'services/api/AGENTS.md',
            'services/web/AGENTS.md': 'AGENTS.md',
        })

    def test_nested_only_guidance_has_no_fabricated_root_parent(self):
        self.repo.write('a/b/AGENTS.md', 'Local policy.\n')
        result = self.verify()
        self.assertIsNone(result['guidanceScopes'][0]['parent'])
        self.assertEqual(result['guidanceScopes'][0]['directory'], 'a/b')

    def test_whitespace_only_guidance_fails(self):
        self.repo.write('AGENTS.md', '  \n\t\n')
        self.assertIn('whitespace-only', self.verify(1)['errors'][0])

    def test_invalid_utf8_is_reported_without_a_traceback(self):
        (self.repo.path / 'AGENTS.md').write_bytes(b'\xff\xfe')
        self.assertIn('UTF-8', self.verify(1)['errors'][0])

    def test_conflict_markers_fail_but_markdown_setext_heading_is_valid(self):
        self.repo.write('AGENTS.md', '<<<<<<< HEAD\nOld rule.\n=======\nNew rule.\n>>>>>>> branch\n')
        self.assertIn('merge-conflict', self.verify(1)['errors'][0])
        self.repo.write('AGENTS.md', 'Guidance\n=======\nRun tests.\n')
        self.assertTrue(self.verify()['ok'])

    def test_deleted_guidance_is_visible_as_a_warning(self):
        self.repo.write('AGENTS.md', 'Root policy.\n')
        self.repo.write('sub/AGENTS.md', 'Local policy.\n')
        self.repo.commit('guidance')
        (self.repo.path / 'sub/AGENTS.md').unlink()
        result = self.verify()
        self.assertEqual(result['changedAgentsFiles'][0]['path'], 'sub/AGENTS.md')
        self.assertTrue(any('sub/AGENTS.md was removed' in warning for warning in result['warnings']))

    def test_staged_move_between_scopes_preserves_both_paths(self):
        self.repo.write('AGENTS.md', 'Root policy.\n')
        self.repo.commit('guidance')
        (self.repo.path / 'sub').mkdir()
        run('git', 'mv', 'AGENTS.md', 'sub/AGENTS.md', cwd=self.repo.path)
        result = self.verify()
        self.assertEqual(result['changedAgentsFiles'][0]['path'], 'sub/AGENTS.md')
        self.assertEqual(result['changedAgentsFiles'][0]['previousPath'], 'AGENTS.md')
        self.assertEqual(result['guidanceScopes'][0]['directory'], 'sub')
        self.assertTrue(any('AGENTS.md was removed' in warning for warning in result['warnings']))

    def test_structural_success_does_not_validate_commands_or_conflicting_prose(self):
        self.repo.write('AGENTS.md', 'Run `invented-command` everywhere.\n')
        self.repo.write('sub/AGENTS.md', 'Never run `invented-command`.\n')
        result = self.verify()
        self.assertTrue(result['ok'])
        self.assertTrue(result['semanticVerificationRequired'])
        self.assertEqual(result['verificationLevel'], 'structural-only')

    def test_custom_conflict_markers_and_unmerged_index_fail(self):
        for size in [3, 8]:
            with self.subTest(marker_size=size):
                repo = Repo()
                self.addCleanup(repo.close)
                repo.write('.gitattributes', f'AGENTS.md conflict-marker-size={size}\n')
                repo.write('AGENTS.md', 'Base rule.\n')
                repo.commit('base')
                branch = run('git', 'branch', '--show-current', cwd=repo.path)
                run('git', 'checkout', '-qb', 'side', cwd=repo.path)
                repo.write('AGENTS.md', 'Side rule.\n')
                repo.commit('side')
                run('git', 'checkout', '-q', branch, cwd=repo.path)
                repo.write('AGENTS.md', 'Main rule.\n')
                repo.commit('main')
                run('git', 'merge', 'side', cwd=repo.path, check=False)
                for staged in [False, True]:
                    if staged:
                        run('git', 'add', 'AGENTS.md', cwd=repo.path)
                    result = subprocess.run([sys.executable, str(VERIFY)], cwd=repo.path, capture_output=True, text=True)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    errors = json.loads(result.stdout)['errors']
                    self.assertTrue(any('merge-conflict markers' in error for error in errors))
                    if not staged:
                        self.assertTrue(any('index conflicts' in error for error in errors))

    def test_verifier_exposes_non_guidance_changes_for_final_review(self):
        self.repo.write('AGENTS.md', 'Policy.\n')
        self.repo.commit('guidance')
        self.repo.write('tests/test_example.py', 'pass\n')
        result = self.verify()
        self.assertEqual(result['changedAgentsFiles'], [])
        self.assertEqual(result['workingTreeChanges'][0]['path'], 'tests/test_example.py')

    def test_non_repository_returns_json_error(self):
        result = subprocess.run([sys.executable, str(VERIFY), '--repo', '/dev/null'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
