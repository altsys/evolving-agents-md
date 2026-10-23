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

Otherwise run `scripts/inspect_repo.py` without a baseline and use its automatically discovered Git boundary. Treat automatic baselines as discovery boundaries, not proof that older guidance is complete.

## Working model

Treat `AGENTS.md` as durable operational guidance, not as a changelog or a summary of the repository.

A useful entry should answer a recurring question for future agents, prevent a likely mistake, or encode a repository constraint that cannot be inferred reliably from the immediate task.

## Script location and target repository

Resolve `<skill-dir>` to the absolute directory containing this `SKILL.md`.
Resolve `<repo-dir>` to the target checkout (or a directory within it). Invoke the
bundled scripts by absolute path with `--repo`; do not assume the target contains
this skill's `scripts/` directory. Both helpers normalize Git operations and
output paths to the target repository root, regardless of the caller's directory.
Require Python 3.10+ and Git. Quote paths and refs as shell arguments.

## Workflow

### 1. Collect deterministic evidence

Run:

```sh
python "<skill-dir>/scripts/inspect_repo.py" --repo "<repo-dir>"
```

Or, when the user supplied a baseline:

```sh
python "<skill-dir>/scripts/inspect_repo.py" --repo "<repo-dir>" --baseline "<ref>"
```

Consume the structured output. Start with `highSignalFiles` and `workingTreeChanges`, while keeping the complete `changedFiles` list available for context.

Paths are repository-relative. Renames include `previousPath`; inspect both scopes when guidance may have moved. Working-tree entries include staged, unstaged, and individual untracked files.

The inspector identifies where investigation is likely worthwhile. Its signal labels are prioritization hints, not conclusions that `AGENTS.md` must change.

### 2. Discover applicable guidance

Read the root `AGENTS.md` and any nested `AGENTS.md` whose scope covers a high-signal change. Determine which directory tree each file governs.

If no `AGENTS.md` exists, do not automatically create one merely because the skill was invoked. First establish that durable repository guidance exists and would materially help future agents.

Preserve intentional human-authored instructions unless repository evidence clearly shows a conflict. A conflict is something to surface, not permission to silently overwrite human intent.

### 3. Investigate each high-signal change

For each high-signal file, follow an evidence ladder. Stop when the evidence is sufficient to accept or reject a candidate. Do not read broadly without a reason.

1. **Path and signal**: understand why the inspector flagged the file.
2. **Diff**: inspect what actually changed between the baseline and current state, including working-tree changes when present.
3. **Current file**: read the relevant current section so deleted or moved context is not mistaken for present truth.
4. **Direct dependencies**: inspect files directly referenced by, invoked by, generated from, or structurally coupled to the changed file when needed.
5. **Corroboration**: look for a second source such as a script, config, test, documentation file, schema consumer, or repeated repository pattern before inferring a repository-wide convention.

The diff answers what changed. The current file answers what is true. Related evidence answers whether the fact is durable and operationally important.

### 4. Form candidate guidance

Convert evidence into a candidate only when it can be expressed as an instruction or constraint useful to a future coding agent.

Represent the reasoning internally as:

```text
Evidence -> Repository fact -> Agent consequence -> Candidate guidance
```

Example:

```text
package.json changes test script to `vitest run`
+ CI invokes `npm test`
-> repository test entry point is now `npm test`
-> agents should use that command before completing changes
-> "Run `npm test` before submitting changes."
```

Do not copy implementation facts directly into `AGENTS.md`. First identify the consequence for future agent behavior.

### 5. Apply the durability test

A candidate should normally pass all of these questions:

- **Future relevance**: Is this likely to matter beyond the current task or commit?
- **Behavior impact**: Would knowing it change how a future agent edits, validates, navigates, or reasons about the repository?
- **Evidence strength**: Is it directly supported, or sufficiently corroborated if inferred?
- **Discoverability**: Is recording it more useful than expecting an agent to rediscover it each time?
- **Stability**: Is it unlikely to become obsolete immediately?
- **Scope**: Can it be stated at the correct repository or directory scope?

Reject a candidate when the answer to future relevance, behavior impact, or evidence strength is no.

Discoverability is contextual. A command visible in `package.json` may still deserve guidance when it is the required validation path. A trivial implementation detail visible next to the edited code usually does not.

### 6. Use signal-specific investigation

Treat inspector signals as prompts for targeted questions:

- **dependencies-tooling**: Did the package manager, runtime, framework, required tool, or canonical command change? Ignore ordinary dependency bumps unless they change development behavior.
- **schema-interface**: Did an API, database model, generated contract, migration workflow, or compatibility rule change in a way future edits must respect? Do not document every field or migration.
- **build-deploy**: Did the build/deploy entry point, environment assumption, generated artifact, CI requirement, or hosting constraint change?
- **commands-workflow**: Did the supported way to run, generate, migrate, seed, validate, or maintain the repository change?
- **validation-conventions**: Did formatting, linting, typing, testing, or repository-wide coding requirements change?
- **agent-guidance**: Treat changes to `AGENTS.md` itself as context. Do not assume a recent edit was a complete reconciliation.

Architecture and directory changes may not always receive a filename-based signal. If the changed-file set shows meaningful moves, additions, deletions, or repeated new boundaries, inspect the relevant tree structure and ownership patterns.

### 7. Reconcile candidates with AGENTS.md

For every surviving candidate, classify the applicable existing guidance as:

- **already accurate**: no edit;
- **missing**: add the smallest useful instruction;
- **stale**: replace or remove the obsolete instruction;
- **contradictory**: resolve only when the existing text is inferred/derived guidance and repository evidence is strong;
- **human conflict**: surface the conflict instead of silently changing explicit human intent;
- **irrelevant**: no edit.

Prefer modifying an existing instruction over adding a second instruction about the same behavior.

### 8. Make the smallest durable edit

Patch the `AGENTS.md` file whose scope matches the guidance. Root guidance belongs at the root; narrowly scoped guidance belongs in the appropriate nested file when one exists or is warranted.

Write instructions in operational language. Prefer what an agent should do, avoid, verify, or understand over historical explanation.

Do not rewrite the whole file for style. Do not reorder stable sections without a functional reason. Do not erase useful human context just to standardize wording.

### 9. Verify

Run:

```sh
python "<skill-dir>/scripts/verify_agents.py" --repo "<repo-dir>"
```

Then perform semantic verification yourself. For every changed instruction, identify the current repository evidence that supports it. Re-run relevant repository commands when practical. Verify paths and schema/interface claims against current definitions. Check root and nested guidance for contradictions.

If an instruction cannot be supported after verification, remove or revise it before finishing.

After the last validation command, review `git status` and the final diff. Preserve pre-existing user changes. Remove only disposable artifacts created by your own validation, or prevent them when invoking the command. Confirm the final changed-file set before reporting which files changed.

### 10. Report

State whether `AGENTS.md` changed.

For each meaningful edit, report the repository evidence and the behavioral consequence that justified it. Identify which `AGENTS.md` file changed when multiple scopes exist.

If it did not change, say that the inspected repository evidence did not produce durable guidance requiring an edit. A no-change result is a successful reconciliation.

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
- Do not treat every high-signal file as an AGENTS.md change. Signals trigger investigation, not documentation.
- Do not promote a local pattern into a repository-wide rule without corroboration.

## Success criteria

The skill succeeds when `AGENTS.md` remains accurate as the repository evolves, contains the durable guidance future agents need, preserves intentional human guidance, removes or corrects stale instructions, and avoids unnecessary edits when repository changes do not affect agent behavior.
