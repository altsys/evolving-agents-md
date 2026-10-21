---
name: evolving-agents-md
description: Keep AGENTS.md aligned with meaningful changes in an evolving codebase while preserving stable human-authored guidance and avoiding unnecessary churn.
---

# Evolving AGENTS.md

Keep `AGENTS.md` trustworthy as the repository evolves.

## Goal

Continuously evaluate repository changes for information that affects how agents should work, and keep `AGENTS.md` aligned with that evolving reality.

Do not update it merely because code changed. Update it only when a change creates, modifies, or invalidates durable guidance future agents need.

## State model

For v1, Git is the state store. Do not create a database or persistent snapshot file merely to remember previous repository contents.

Use Git history to identify what changed and where to investigate. Use the current repository to determine what is true now. Use the applicable `AGENTS.md` files to determine what guidance agents currently receive. Reconcile all three.

A diff is evidence, not documentation.

## Manual invocation

When the user explicitly asks to update, refresh, reconcile, or check `AGENTS.md`, run this workflow.

If the user supplies a commit, tag, branch, or other valid Git ref as the baseline, use it.

If no baseline is supplied, use Git history to identify a useful comparison point. Do not assume that the most recent edit to `AGENTS.md` proves that all earlier repository changes were incorporated. If no trustworthy baseline can be established, inspect the current repository directly and reconcile it with `AGENTS.md`.

## Working model

Treat `AGENTS.md` as durable operational guidance, not as a changelog or a summary of the repository.

A useful entry should answer a recurring question for future agents, prevent a likely mistake, or encode a repository constraint that cannot be inferred reliably from the immediate task.

## Workflow

### 1. Discover applicable guidance

Find root and nested `AGENTS.md` files. Determine which directory tree each file governs and respect repository-specific scoping rules.

Preserve intentional human-authored instructions unless repository evidence clearly shows a conflict. A conflict is something to surface, not permission to silently overwrite human intent.

### 2. Establish the Git baseline

Prefer an explicit user-supplied ref.

Otherwise inspect Git history and choose a useful comparison point based on available evidence. Treat the baseline as a discovery aid, not as proof that older guidance is correct.

If a reliable baseline cannot be determined, continue by evaluating current repository state against existing guidance.

### 3. Triage repository changes

Start with inexpensive evidence such as changed filenames, status, commit history, and diff summaries. Use this to identify high-signal areas before reading file contents.

High-signal areas include:

- build, test, lint, formatting, and deployment configuration;
- package manifests, lockfiles, runtimes, and major tooling;
- architecture and important directory boundaries;
- database, data model, and API schemas;
- generated, vendored, protected, or special files;
- repository-wide conventions and validation rules;
- scripts and documentation that define how development work is performed.

Do not infer a repository rule from a single accidental implementation detail.

### 4. Inspect current truth selectively

For high-signal changes, inspect both the relevant diff and the current version of the affected files when useful.

Do not read the entire repository by default. Expand inspection only when the evidence requires it.

Git history answers where to look. Current repository state answers what is true.

### 5. Extract candidate guidance

For each meaningful finding, ask whether a future agent needs the information to work correctly, safely, or efficiently.

Strong candidates include changes to commands, architecture, directory responsibilities, major tooling, durable schema/interface expectations, repository-wide conventions, validation requirements, and files agents must handle specially.

Usually reject isolated bug fixes, temporary implementation details, immediately expiring migration steps, facts obvious from nearby code, and descriptions of what a particular commit did.

### 6. Reconcile candidates with AGENTS.md

Classify each candidate as:

- already accurate;
- missing;
- stale;
- contradictory; or
- irrelevant to durable agent guidance.

Only missing, stale, or appropriately resolvable contradictory guidance should produce an edit.

When repository evidence conflicts with explicit human-authored guidance, report the conflict rather than silently replacing the human instruction.

### 7. Make the smallest durable edit

Patch the `AGENTS.md` file whose scope matches the guidance. Root guidance belongs at the root; narrowly scoped guidance belongs in the appropriate nested file when one exists or is warranted.

Prefer concise instructions that remain useful across future tasks. Remove or correct stale guidance when repository evidence supports doing so.

Do not rewrite the whole file for style. Do not reorder stable sections without a functional reason. Do not erase useful human context just to standardize wording.

### 8. Verify

Check every changed instruction against current repository evidence.

Where practical, verify commands against configuration or scripts rather than memory. Verify paths and schema/interface claims against their current definitions. Check for contradictions between root and nested `AGENTS.md` files.

### 9. Report

State whether `AGENTS.md` changed.

If it changed, briefly explain the repository evidence that justified each meaningful documentation update and identify which `AGENTS.md` file was modified when multiple scopes exist.

If it did not change, say that the repository evidence did not reveal a durable guidance change requiring an edit.

## Guardrails

- Never invent commands, paths, conventions, schemas, interfaces, or architectural rules.
- Never turn `AGENTS.md` into a running changelog.
- Prefer repository evidence over assumptions.
- Treat explicit human-authored instructions as higher-confidence than inferred conventions. If repository evidence conflicts with them, surface the conflict rather than silently overriding them.
- Preserve stable instructions unless there is evidence they are stale.
- Do not duplicate information that agents can reliably discover from the repository unless recording it prevents a recurring mistake or materially changes agent behavior.
- Keep guidance scoped to the directory where it applies.
- Favor small, reviewable edits over broad rewrites.
- Avoid timestamps or volatile details unless they are operationally necessary.

## Success criteria

The skill succeeds when `AGENTS.md` remains accurate as the repository evolves, contains the durable guidance future agents need, preserves intentional human guidance, removes or corrects stale instructions, and avoids unnecessary edits when repository changes do not affect agent behavior.
