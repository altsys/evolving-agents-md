# evolving-agents-md

An agent skill that continuously keeps `AGENTS.md` aligned with an evolving codebase.

## Why

`AGENTS.md` is useful only while it reflects the repository agents are actually working in. As architecture, commands, conventions, dependencies, and workflows change, static guidance can become stale and eventually misleading.

This skill treats `AGENTS.md` as living operational documentation.

## What the skill does

The skill:

1. inspects the repository and the existing `AGENTS.md`;
2. identifies meaningful changes that affect agent guidance;
3. distinguishes durable repository knowledge from temporary implementation details;
4. updates only the affected guidance;
5. preserves useful human-authored instructions and avoids unnecessary churn; and
6. reports what changed and why.

## What should trigger an update?

Examples include:

- architecture or directory structure changes;
- new or changed build, test, lint, or deployment commands;
- dependency or tooling changes that affect development;
- database, data model, or API schema changes that affect implementation patterns or workflows;
- new coding conventions or repository-wide patterns;
- changes to generated files or files agents should avoid editing;
- new validation requirements or important workflow constraints.

A normal code change or one-off migration does **not** automatically justify changing `AGENTS.md`. Schema changes should trigger an update only when they create durable guidance future agents need.

## Core principle

`AGENTS.md` should describe the repository's current operating reality, not its commit history.

The goal is not to make the file change often. The goal is to make it trustworthy.

## Status

Early development. The initial skill contract lives in [`SKILL.md`](./SKILL.md).
