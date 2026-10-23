# evolving-agents-md

An agent skill that continuously keeps `AGENTS.md` aligned with an evolving codebase.

## Quick start

Require Python 3.10+, Git, and a coding agent that can read local skill files and run
commands. The Python helpers use only the standard library.

Clone this skill outside the repository you want to maintain:

```sh
mkdir -p ~/agent-skills
git clone https://github.com/altsys/evolving-agents-md.git ~/agent-skills/evolving-agents-md
```

Give your agent the absolute path to the cloned `SKILL.md` and the target checkout:

```text
Use the skill at /absolute/path/to/evolving-agents-md/SKILL.md to check recent
repository changes and update AGENTS.md in /absolute/path/to/my-project.
```

Add `since <commit/tag/branch>` when you want a specific baseline. This explicit-path
invocation works without an installer or client-specific discovery configuration.
If your client supports a skill catalog, register the same folder through that
client's supported setup. Keep `scripts/` beside `SKILL.md`; the helpers collect and
check evidence, while the coding agent makes and verifies guidance edits.

## Example: a renamed validation command

Suppose the Makefile renames `test` to `check` and CI also switches to `make check`.
Existing **derived** guidance says:

```markdown
Run `make test` to validate changes.
```

The skill corroborates both files, then changes that line to:

```markdown
Run `make check` to validate changes.
```

It preserves unrelated instructions and reports the evidence, behavioral consequence,
and checks run. An explicit maintainer instruction conflicting with the command is
reported for resolution. A dependency patch or label-text edit can correctly result
in no guidance change.

## Why

`AGENTS.md` is useful only while it reflects the repository agents are actually working in. As architecture, commands, conventions, dependencies, schemas, and workflows change, static guidance can become stale and eventually misleading.

This skill treats `AGENTS.md` as living operational documentation.

## Core model

For v1, **Git is the state store**. The skill does not maintain a database or duplicate snapshots of important repository files.

Git history tells the skill **where to investigate**. The current repository tells it **what is true now**. Existing `AGENTS.md` files tell it **what agents are currently being told**. The skill reconciles those three sources.

A diff is evidence, not documentation. A code change belongs in `AGENTS.md` only when it creates, changes, or invalidates durable guidance future agents need.

## What the skill does

The skill:

1. discovers the applicable root and nested `AGENTS.md` files and their scopes;
2. establishes a Git baseline, using a user-supplied ref when provided and Git history/current repository state otherwise;
3. inspects changes since that baseline, starting with changed files and high-signal areas rather than reading the whole repository;
4. reads the current state of relevant code, configuration, schemas, scripts, and documentation;
5. extracts candidate guidance that would materially affect future agent behavior;
6. reconciles that guidance with existing `AGENTS.md` content;
7. makes the smallest durable edit in the correctly scoped `AGENTS.md` file;
8. verifies the resulting guidance against the current repository; and
9. reports what changed and why, or reports that no update was necessary.

## Manual trigger

The first supported trigger is explicit user invocation.

Examples:

- `Update AGENTS.md.`
- `Check recent repository changes and update AGENTS.md.`
- `Update AGENTS.md since <commit/tag/branch>.`

If the user supplies a commit, tag, or branch, the skill uses it as the comparison baseline. If no baseline is supplied, the skill uses Git history to identify a useful comparison point but treats the current repository as the final source of truth. If Git history cannot establish a trustworthy baseline, the skill evaluates the current repository directly rather than pretending it knows what is recent.

Future versions may add change-driven and scheduled reconciliation triggers. A raw commit-count trigger is intentionally not part of v1 because commit count measures activity, not significance.

## Helper invocation and validation

Require Python 3.10+ and Git. The skill's scripts stay in the installed skill folder;
they do not need to be copied into the target repository:

```sh
python "/absolute/path/to/evolving-agents-md/scripts/inspect_repo.py" --repo "/path/to/target"
python "/absolute/path/to/evolving-agents-md/scripts/inspect_repo.py" --repo "/path/to/target" --baseline "<ref>"
python "/absolute/path/to/evolving-agents-md/scripts/verify_agents.py" --repo "/path/to/target"
```

`--repo` defaults to the current directory and accepts a subdirectory of a checkout.
Output paths are always relative to the target repository root. Changes include
individual untracked files; renames preserve both `path` and `previousPath`.
`workingTreeChanges` and `changedAgentsFiles` contain structured path/status records.
`guidanceScopes` describes each guidance file's directory and nearest parent;
`deletedAgentsFiles` reports removed guidance found in inspected changes.

History fallbacks are explicit:

| Repository state | Inspection behavior |
| --- | --- |
| No commits yet | `head` and `baseline.sha` are null; review current files and staged/untracked changes. |
| Shallow clone | Automatic baseline is null; warn that history is incomplete and review current state. No fetch is attempted. |
| Valid explicit baseline | Honor it; shallow history remains flagged. An unavailable ref returns an error. |
| Root fallback or multiple unrelated roots | Review current files too, including files introduced in the initial commit. |
| Multiple guidance scopes | Combine scope boundaries conservatively so a recent nested edit cannot hide older root/sibling changes. |
| Deleted guidance or detached HEAD | Report available evidence without recreating deleted instructions or requiring an attached branch. |

When `currentStateReviewRequired` is true, use `currentHighSignalFiles` and
`currentFiles` alongside change evidence. All automatic boundaries remain heuristics.

The verifier reports `verificationLevel: structural-only`; `ok: true` means only that
its structural checks passed. It checks nonblank UTF-8 guidance and merge markers,
reports untracked/removed files and all working-tree changes, and exposes scope relationships. It also rejects unmerged guidance and reads configured conflict marker sizes. Commands, paths,
contradictions, and instruction meaning still require agent review. Exit codes are
0 for successful structural checks (warnings may remain), 1 for structural errors,
and 2 for invalid invocation/repository errors. The inspector uses 0 for successful
evidence collection and 2 for invalid repository/baseline errors.

From this skill repository, run the deterministic tests with:

```sh
python -m unittest discover -s tests -v
```

For agent evaluations covering stale and missing guidance, human conflicts, nested
scopes, and no-change decisions, follow [the evaluation instructions](evals/README.md).
These evaluations run separately from CI and require semantic review of each result.

## What should trigger an AGENTS.md change?

Examples include:

- architecture or directory structure changes;
- new or changed build, test, lint, or deployment commands;
- dependency or tooling changes that affect development;
- database, data model, or API schema changes that affect implementation patterns, interfaces, or workflows;
- new coding conventions or repository-wide patterns;
- changes to generated files or files agents should avoid editing;
- new validation requirements or important workflow constraints.

A normal code change or one-off migration does **not** automatically justify changing `AGENTS.md`. Schema changes should trigger an update only when they create durable guidance future agents need.

## Reconciliation, not summarization

Candidate guidance should be classified against existing `AGENTS.md` content as one of:

- already accurate;
- missing;
- stale;
- contradictory; or
- irrelevant to durable agent guidance.

The skill patches only what needs to change. It does not turn `AGENTS.md` into a changelog, repository summary, or duplicate of information agents can reliably discover themselves.

Explicit human-authored instructions receive higher confidence than inferred conventions. If current repository evidence conflicts with an explicit human instruction, the skill surfaces the conflict rather than silently replacing the instruction.

## Core principle

`AGENTS.md` should describe the repository's current operating reality, not its commit history.

The goal is not to make the file change often. The goal is to make it trustworthy.

## Status

Early development. Manual invocation and the Git-backed reconciliation mechanism are the v1 focus. The behavioral contract lives in [`SKILL.md`](./SKILL.md).

## License

[MIT](LICENSE).
