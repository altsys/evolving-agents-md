#!/usr/bin/env python3
"""Prepare isolated real repositories; check agent outputs against outcome constraints."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from behavior_cases import CASES


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args]).decode('utf-8', errors='surrogateescape')


def prepare(name: str, repo: Path) -> None:
    # Refuse to overwrite an existing run or checkout.
    repo.mkdir(parents=True, exist_ok=False)
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.name', 'Behavior fixture')
    git(repo, 'config', 'user.email', 'fixture@example.test')
    for message, files in [('initial state', CASES[name]['before']), ('repository change', CASES[name]['after'])]:
        for relative, content in files.items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        git(repo, 'add', '-A')
        git(repo, 'commit', '-qm', message)


def check(name: str, repo: Path, report: str) -> dict:
    case = CASES[name]
    errors = []
    tracked = set(filter(None, git(repo, 'ls-files', '-z').split('\0')))
    untracked = set(filter(None, git(repo, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')))
    changed = set()
    for relative in tracked:
        target = repo / relative
        original = subprocess.check_output(['git', '-C', str(repo), 'show', f'HEAD:{relative}'])
        if not target.is_file() or target.read_bytes() != original:
            changed.add(relative)
    changed |= untracked
    # Also catch staged-only edits and deleted files.
    changed |= set(filter(None, git(repo, 'diff', '--name-only', '-z', 'HEAD').split('\0')))
    expected = set(case['changedGuidance'])
    if changed != expected:
        errors.append(f'Changed files: expected {sorted(expected)!r}, got {sorted(changed)!r}')
    for relative, fragments in case.get('required', {}).items():
        text = (repo / relative).read_text() if (repo / relative).is_file() else ''
        for fragment in fragments:
            if fragment not in text:
                errors.append(f'{relative}: missing {fragment!r}')
    for relative, fragments in case.get('forbidden', {}).items():
        text = (repo / relative).read_text() if (repo / relative).is_file() else ''
        for fragment in fragments:
            if fragment in text:
                errors.append(f'{relative}: obsolete guidance {fragment!r}')
    if not report.strip():
        errors.append('A final agent report is required.')
    for pattern in case.get('reportPatterns', []):
        if not re.search(pattern, report):
            errors.append(f'Report missing conflict evidence matching {pattern!r}')
    return {'case': name, 'ok': not errors, 'errors': errors, 'semanticReviewRequired': True, 'rubric': case['rubric']}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'check'])
    parser.add_argument('--case', required=True, choices=sorted(CASES))
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--report', type=Path, help='Final agent report; required for check')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.case, args.repo)
        print(json.dumps({'case': args.case, 'repo': str(args.repo.resolve()), 'task': 'Check recent repository changes and update AGENTS.md.'}))
        return 0
    if not args.report:
        parser.error('--report is required for check')
    result = check(args.case, args.repo, args.report.read_text())
    print(json.dumps(result, indent=2))
    return 0 if result['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
