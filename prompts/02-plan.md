# Phase 2 — Plan prompt

> Paste this in a **fresh chat** after Phase 1 is complete and you have reviewed `research.md`.

---

You are in **Phase 2: Plan** of an Odoo module migration. No code changes yet.

## Inputs
- `MIGRATION.md` (§0 + §1 filled)
- `research.md` (completed in Phase 1)
- `checklists/mechanical-transforms.md`
- `checklists/gates.md`

## Your job

Produce `plan.md` following `template/plan.md`. Specifically:

1. **Break the migration into atomic tasks**. A task is atomic if:
   - It can land in one commit
   - It has a verifiable acceptance criterion
   - It can be implemented by an AI in a fresh ~200k-token context without needing to re-read the whole module
   - It does not mix concerns (a task is never "migrate models and views" — split them)
2. **Order tasks** using the priority in `template/plan.md` (manifest → mechanical → model → view → logic → tests → data).
3. **For each task** fill in: files touched, dependencies on other tasks, acceptance criteria, how-to-verify, risk.
4. **Identify tasks that can be done in parallel** (no dependency arrows) — mark them with `[parallelizable]`.
5. **Propose new tests** for any risky path in `research.md` §4 that currently lacks coverage. These go in early tasks, before the code that would break them.
6. **Propose pre/post-migration.py scripts** only for module-private models; for core models, defer to OpenUpgrade and note it.

## Hard rules
- Do NOT write any code. Just the plan.
- If a task would be larger than ~300 LOC of diff, split it.
- Do NOT include "refactor" tasks unless they are strictly required to unblock the migration. Scope discipline.
- Every task must list **how it will be verified** — if you can't state that, the task is not well-scoped.
- If `research.md` has `⚠️ needs human check` items, list them at the top of `plan.md` as blocking questions before any task can start.

When done, print: `PLAN READY FOR REVIEW — do not start Phase 3 until human approves.`
