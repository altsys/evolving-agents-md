---
name: evolving-agents-md
description: Keep AGENTS.md aligned with meaningful changes in an evolving codebase while preserving stable human-authored guidance and avoiding unnecessary churn.
---

# Evolving AGENTS.md

Keep `AGENTS.md` trustworthy as the repository evolves.

## Goal

Update `AGENTS.md` when repository changes alter information an agent needs in order to work correctly, safely, or efficiently.

Do not update it merely because code changed.

## Working model

Treat `AGENTS.md` as durable operational guidance, not as a changelog or a summary of the repository.

A useful entry should answer a recurring question for future agents, prevent a likely mistake, or encode a repository constraint that cannot be inferred reliably from the immediate task.

## Workflow

### 1. Read existing guidance

Find the applicable `AGENTS.md` files and read them before proposing changes. Respect nested guidance and repository-specific scope.

Preserve intentional human-authored instructions unless repository evidence clearly shows that they are obsolete or incorrect.

### 2. Inspect repository change

Determine what changed using the strongest evidence available, such as:

- the current task and edited files;
- the diff or commits since the last relevant state;
- build and package configuration;
- test, lint, formatting, and deployment configuration;
- directory and architecture changes;
- repository documentation and scripts.

Do not infer a new repository rule from a single accidental implementation detail.

### 3. Decide whether AGENTS.md is affected

Update guidance when the change creates or modifies durable knowledge that future agents need.

Strong signals include:

- a build, test, lint, formatting, or deployment command changed;
- architecture or important directory boundaries changed;
- a new framework, package manager, runtime, or major tool changes how work is performed;
- repository-wide coding or testing conventions changed;
- generated, vendored, protected, or otherwise special files changed;
- validation requirements changed;
- a repeated agent mistake reveals missing repository guidance.

Usually do not update for:

- isolated bug fixes;
- temporary implementation details;
- one-off migrations whose instructions will immediately expire;
- facts obvious from nearby code;
- descriptions of what a particular commit did.

When uncertain, prefer no change over speculative guidance.

### 4. Make the smallest durable edit

Change only the affected section when possible.

Prefer concise instructions that remain useful across future tasks. Remove or correct stale guidance when repository evidence supports doing so.

Do not rewrite the whole file for style. Do not reorder stable sections without a functional reason. Do not erase useful human context just to standardize wording.

### 5. Verify

Before finishing, check that every changed instruction is supported by the current repository.

Where practical, verify commands against configuration or scripts rather than memory.

Check for contradictions between root and nested `AGENTS.md` files.

### 6. Report

State whether `AGENTS.md` changed.

If it changed, briefly explain the repository change that justified each meaningful documentation update.

If it did not change, say that the repository changes did not alter durable agent guidance.

## Guardrails

- Never invent commands, paths, conventions, or architectural rules.
- Never turn `AGENTS.md` into a running changelog.
- Prefer repository evidence over assumptions.
- Preserve stable instructions unless there is evidence they are stale.
- Keep guidance scoped to the directory where it applies.
- Favor small, reviewable edits over broad rewrites.
- Avoid timestamps or volatile details unless they are operationally necessary.

## Success criteria

The skill succeeds when a future agent can trust `AGENTS.md` to reflect the repository's current operating constraints without being distracted by transient history or unnecessary documentation churn.
