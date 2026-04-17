# Gates — the "don't proceed until" list

Gates are non-negotiable checkpoints between phases. Skipping a gate is how migrations blow up.

## Gate A — Before Phase 1 (Research)
- [ ] `MIGRATION.md` §0 Intake is filled
- [ ] Source and target versions are pinned (not "latest")
- [ ] A copy of production DB exists somewhere accessible for Phase 4

## Gate B — Before Phase 2 (Plan)
- [ ] `research.md` is complete
- [ ] All `⚠️ needs human check` items in research are answered
- [ ] The risk table has at least one entry (if it's empty, you haven't looked hard enough)

## Gate C — Before Phase 3 (Execute)
- [ ] `plan.md` is complete AND human-reviewed
- [ ] Tasks are atomic (no mega-tasks)
- [ ] Every task has an acceptance criterion and a verify command
- [ ] Test coverage for risky paths is added in early tasks (not deferred)
- [ ] Out-of-scope list is explicit

## Gate D — Per-task (during Phase 3)
- [ ] Task's verify command passes
- [ ] Only files listed in the task were touched
- [ ] Commit message follows format: `migrate(<module>): <TXX> <desc>`
- [ ] `MIGRATION.md` §3 Execution log updated

## Gate E — Before declaring migration done (Phase 4)
- [ ] All automated gates in `verification.md` are green
- [ ] `odoo -u <module>` succeeds on a copy of production
- [ ] Manual QA checklist reviewed by a human (not the AI)
- [ ] Rollback plan written and tested on the copy
- [ ] `FOLLOWUPS.md` items are captured as tickets, not left in code
