# Phase 4 — Verify prompt

> Paste this in a fresh chat after all tasks in `plan.md` are done.

---

You are in **Phase 4: Verify**. The migration is NOT done until every gate in `template/verification.md` is green.

## Inputs
- All the files in the migration (MIGRATION.md, research.md, plan.md, module source)
- `checklists/gates.md`

## Your job

1. Produce `verification.md` following `template/verification.md`.
2. For each **automated gate**, run the command and record the result. If it fails, diagnose root cause (do NOT silence the failure).
3. For each **manual QA item**, write a step-by-step reproduction I can run. Do not check the box yourself for manual items — only I can.
4. If `pre-migration.py` / `post-migration.py` exist, propose SQL queries that prove the data migration worked (e.g. row counts before/after, orphan checks).
5. Produce the **rollback plan** section with the exact commands needed to revert.
6. List any `FOLLOWUPS.md` items discovered during Phase 3 that should become their own tickets.

## Hard rules
- Do NOT declare the migration done if any automated gate fails. Red stays red.
- Do NOT skip gates because "the manual test probably covers it".
- If a gate is not applicable (e.g. no demo data shipped), write `N/A — <reason>`, do not silently drop it.
- Running the target-version DB upgrade against a **copy of production** is non-negotiable for the "done" state.

When done, print a summary of: gates passed / failed / N/A / pending-human, then `VERIFICATION REPORT READY — human review needed.`
