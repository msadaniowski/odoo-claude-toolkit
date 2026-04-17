# Phase 3 — Execute one task

> **Paste this in a FRESH chat for EACH task.** Do not reuse context across tasks — that defeats the purpose of phase-based work.

---

You are in **Phase 3: Execute** of an Odoo module migration. You will implement **exactly one task** from `plan.md`.

## Inputs
- `MIGRATION.md`, `research.md`, `plan.md` (read them)
- The task ID I will give you below

## Task to execute

**Task ID**: `<TXX>`

## Protocol

1. Read the task spec from `plan.md`. Re-state the acceptance criteria back to me in one sentence — this is your confirmation you understood.
2. Read only the files listed in the task's "files touched". Do not wander the codebase.
3. Implement the change. Do not exceed the task's scope — if you notice adjacent issues, add them to a `FOLLOWUPS.md`, do NOT fix them now.
4. Run the "how to verify" command from the task. If it fails, iterate until it passes or until you are blocked.
5. Update `MIGRATION.md` §3 Execution log: one row with the task ID, one-line description, commit hash (if you commit), status.
6. Stop. Do not start the next task.

## Hard rules
- **Single-task scope.** If the plan says "rename field X", you rename field X and nothing else.
- **No drive-by refactors.** Even if the code is ugly.
- **No new dependencies** unless the task explicitly allows it.
- **Commit message format**: `migrate(<module>): <task ID> <short description>`
- If the task is blocked (missing info, broken environment), STOP and tell me — do not guess.
- If verification fails in a way that suggests the plan is wrong (not just a bug in your code), STOP and flag it so we can fix `plan.md` first.

When done, print: `TASK <TXX> COMPLETE — verification passed. Ready for next task in fresh context.`
