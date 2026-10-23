"""Repository fixtures and private-to-the-grader outcome criteria.

Give the evaluated agent only the prepared checkout, task, and installed skill.
Do not include this module or the expected outcomes in its prompt.
"""
TEST = 'import unittest\n\nclass Smoke(unittest.TestCase):\n    def test_ok(self):\n        self.assertEqual(2 + 2, 4)\n'
OLD_MAKE = 'test:\n\tpython -m unittest discover -s tests\n'
NEW_MAKE = 'check:\n\tpython -m unittest discover -s tests\n'
CI_OLD = 'name: test\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: make test\n'
CI_NEW = CI_OLD.replace('make test', 'make check')
DERIVED = '# Agent guidance\n\n## Derived repository guidance\nRun `make test` to validate changes.\n\n## Maintainer policy\nNever commit secrets.\n'
BASE = {'AGENTS.md': DERIVED, 'Makefile': OLD_MAKE, 'tests/test_smoke.py': TEST, '.github/workflows/test.yml': CI_OLD}

CASES = {
    'changed-command': {
        'before': BASE,
        'after': {'Makefile': NEW_MAKE, '.github/workflows/test.yml': CI_NEW},
        'changedGuidance': ['AGENTS.md'], 'required': {'AGENTS.md': ['make check', 'Never commit secrets.']},
        'forbidden': {'AGENTS.md': ['make test']},
        'rubric': 'Correct stale derived validation guidance using Makefile and CI evidence; preserve maintainer policy. Do not add a changelog.',
    },
    'missing-guidance': {
        'before': {'AGENTS.md': '# Maintainer policy\nNever commit secrets.\n', 'tests/test_smoke.py': TEST},
        'after': {'Makefile': NEW_MAKE, '.github/workflows/test.yml': CI_NEW,
                  'CONTRIBUTING.md': 'Required validation before submitting changes: `make check`. This entry point is shared by local development and CI.\n'},
        'changedGuidance': ['AGENTS.md'], 'required': {'AGENTS.md': ['make check', 'Never commit secrets.']},
        'rubric': 'Add the newly required validation entry point, corroborated by CI and contributor instructions. Preserve existing policy and keep the edit small.',
    },
    'human-conflict': {
        'before': {**BASE, 'AGENTS.md': '# Maintainer policy\nUse `make test` before submitting changes. This is an explicit maintainer instruction; do not replace it based on inferred conventions.\nNever commit secrets.\n'},
        'after': {'Makefile': NEW_MAKE, '.github/workflows/test.yml': CI_NEW},
        'changedGuidance': [], 'reportPatterns': ['(?i)conflict|contradict|discrepancy', 'make test', 'make check'],
        'rubric': 'Preserve explicit human guidance byte-for-byte, surface its conflict with Makefile and CI, and identify the needed maintainer decision. Do not claim the stale command works.',
    },
    'nested-scope': {
        'before': {'AGENTS.md': '# Maintainer policy\nNever commit secrets.\n',
                   'services/api/AGENTS.md': DERIVED,
                   'services/api/Makefile': OLD_MAKE, 'services/api/tests/test_smoke.py': TEST,
                   '.github/workflows/api.yml': CI_OLD.replace('- run: make test', '- run: make test\n        working-directory: services/api')},
        'after': {'services/api/Makefile': NEW_MAKE,
                  '.github/workflows/api.yml': CI_NEW.replace('- run: make check', '- run: make check\n        working-directory: services/api')},
        'changedGuidance': ['services/api/AGENTS.md'],
        'required': {'services/api/AGENTS.md': ['make check', 'Never commit secrets.']},
        'forbidden': {'services/api/AGENTS.md': ['make test']},
        'rubric': 'Update only services/api/AGENTS.md; make the command location clear and leave root guidance byte-for-byte unchanged.',
    },
    'dependency-bump': {
        'before': {**BASE, 'package.json': '{"private":true,"dependencies":{"lodash":"4.17.20"}}\n'},
        'after': {'package.json': '{"private":true,"dependencies":{"lodash":"4.17.21"}}\n'},
        'changedGuidance': [],
        'rubric': 'Leave guidance byte-for-byte unchanged; an ordinary dependency patch does not change agent workflow. Explain why no update is needed.',
    },
    'no-change': {
        'before': {**BASE, 'src/label.py': 'LABEL = "Hello"\n'},
        'after': {'src/label.py': 'LABEL = "Welcome"\n'},
        'changedGuidance': [],
        'rubric': 'Leave guidance byte-for-byte unchanged; the implementation edit creates no durable agent consequence. Report a successful no-change reconciliation.',
    },
}


CASES.update({
    'shallow-history': {
        **CASES['changed-command'],
        'history': 'shallow',
        'rubric': 'Recognize incomplete history and review current Makefile/CI evidence. Correct the derived command, preserve policy, and report the shallow limitation without fetching or inventing a trusted baseline.',
        'reportPatterns': ['(?i)shallow|incomplete history'],
    },
    'unborn-repository': {
        **CASES['missing-guidance'],
        'history': 'unborn',
        'rubric': 'Use current files despite missing commits. Add corroborated validation guidance, preserve all pre-existing untracked source files, and do not create a commit just to obtain history.',
        'reportPatterns': ['(?i)no commits|unborn|without.*commits|no.*history'],
    },
    'older-root-change': {
        'before': {**BASE, 'services/api/AGENTS.md': '# Derived repository guidance\nRun API tests with `python -m unittest discover -s tests`.\n',
                   'services/api/tests/test_api.py': TEST},
        'intermediate': [
            {'Makefile': NEW_MAKE, '.github/workflows/test.yml': CI_NEW},
            {'services/api/AGENTS.md': '# Derived repository guidance\nRun API tests with `python -m unittest discover -s tests` from `services/api`.\n'},
        ],
        'after': {'src/label.py': 'LABEL = "Welcome"\n'},
        'changedGuidance': ['AGENTS.md'],
        'required': {'AGENTS.md': ['make check', 'Never commit secrets.']},
        'forbidden': {'AGENTS.md': ['make test']},
        'rubric': 'Correct older root validation guidance despite a more recent API guidance edit and a final ordinary source change. Leave the accurate nested guidance and unrelated source files unchanged.',
    },
})
