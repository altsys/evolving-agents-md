#!/usr/bin/env python3
"""Prepare isolated real repositories; check agent outputs against outcome constraints."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

from behavior_cases import CASES


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(['git', '-C', str(repo), *args]).decode('utf-8', errors='surrogateescape')


def snapshot(case: dict) -> dict[str, str]:
    files = {}
    for state in [case['before'], *case.get('intermediate', []), case['after']]:
        files.update(state)
    return files


def prepare(name: str, repo: Path) -> None:
    # Refuse to overwrite an existing run or checkout.
    if repo.exists():
        raise FileExistsError(repo)
    case = CASES[name]
    if case.get('history') == 'shallow':
        with tempfile.TemporaryDirectory() as directory:
            seed = Path(directory) / 'seed'
            seed_case(case, seed)
            repo.parent.mkdir(parents=True, exist_ok=True)
            subprocess.check_call(['git', 'clone', '-q', '--depth=1', seed.as_uri(), str(repo)])
        return
    seed_case(case, repo)


def seed_case(case: dict, repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=False)
    git(repo, 'init', '-q')
    git(repo, 'config', 'user.name', 'Behavior fixture')
    git(repo, 'config', 'user.email', 'fixture@example.test')
    states = [case['before'], *case.get('intermediate', []), case['after']]
    for index, files in enumerate(states):
        for relative, content in files.items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding='utf-8')
        if case.get('history') != 'unborn':
            git(repo, 'add', '-A')
            git(repo, 'commit', '-qm', f'fixture state {index}')


def check(name: str, repo: Path, report: str) -> dict:
    case = CASES[name]
    errors = []
    original = snapshot(case)
    actual_paths = set(filter(None, git(repo, 'ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0')))
    changed = set()
    for relative in set(original) | actual_paths:
        target = repo / relative
        before = original.get(relative)
        if before is None or not target.is_file() or target.read_bytes() != before.encode('utf-8'):
            changed.add(relative)
    # Compare against fixture state rather than HEAD, so unborn checkouts work
    # and an accidental agent commit cannot hide changes from the grader.
    indexed = set()
    for record in filter(None, git(repo, 'ls-files', '--stage', '-z').split('\0')):
        header, relative = record.split('\t', 1)
        _, sha, stage = header.split()
        indexed.add(relative)
        if stage != '0' or relative not in original:
            changed.add(relative)
            continue
        content = subprocess.check_output(['git', '-C', str(repo), 'cat-file', 'blob', sha])
        if case.get('history') == 'unborn' or content != original[relative].encode('utf-8'):
            changed.add(relative)
    if case.get('history') != 'unborn':
        changed |= set(original) - indexed
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
