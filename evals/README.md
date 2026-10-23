# Behavioral evaluations

Unit tests check Git collection and helper invocation. These cases check an agent's
use of the skill: stale commands, missing guidance, human conflicts, nested scopes,
ordinary dependency bumps, and implementation changes that need no guidance edit.

Prepare a fresh checkout for each case:

```sh
python tests/run_behavior_evals.py prepare --case changed-command --repo /tmp/eval-changed-command
```

Start a fresh agent with only this task, the installed skill path, and the prepared
checkout: "Use the skill at <skill-dir>/SKILL.md to check recent repository changes
and update AGENTS.md in <repo-dir>." Do not show it the case definitions, expected
outcomes, or previous runs. Save its final report outside the checkout. Do not let
it commit changes, because HEAD is the comparison point used by the grader.

Then check its result:

```sh
python tests/run_behavior_evals.py check --case changed-command --repo /tmp/eval-changed-command --report /tmp/report.txt
```

Repeat with `missing-guidance`, `human-conflict`, `nested-scope`, `dependency-bump`,
and `no-change`. Each preparation refuses to overwrite an existing directory.

The checker validates changed file boundaries, preserved files, essential command
facts, obsolete commands, and conflict reporting. A pass is not proof of semantic
correctness. Review each diff and final report using the returned rubric: ensure
claims have repository evidence, wording is scoped, edits are small, and no
unsupported rule or changelog was added. Record agent/model, skill commit, case,
checker outcome, semantic review, and limitations. Rerun fresh cases after changes
to the workflow; do not treat a single run as evidence of universal reliability.

These evaluations require an agent and are separate from the deterministic CI
suite. The deterministic suite also tests the fixture builder and grader, including
that a no-op agent cannot pass cases that require edits.

Recorded outcomes, agent reports, guidance diffs, and limitations: [2026-10-23 run](results-2026-10-23.json).
