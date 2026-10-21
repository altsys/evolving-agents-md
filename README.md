# evolving-agents-md

An agent skill that continuously keeps `AGENTS.md` aligned with an evolving codebase.

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
