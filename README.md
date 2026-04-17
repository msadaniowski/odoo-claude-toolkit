# Odoo Module Migration Recipe

A **spec-driven, phase-based recipe** for migrating Odoo modules between versions, designed to work with AI coding assistants (Claude Code, Codex, Cursor, etc.).

Inspired by the [GSD (Get Shit Done)](https://github.com/gsd-build/get-shit-done) workflow, adapted to the realities of Odoo migration: `OpenUpgrade`, OCA guidelines, mechanical transformations, and the human judgement calls that always remain.

---

## Why this exists

Migrating an Odoo module is **never a pure "run the codemod" exercise**. You always have:

- Mechanical changes (API renames, deprecated attrs, manifest bumps) → automatable
- Semantic changes (business logic that relies on behavior that changed) → needs understanding
- Data-shape changes (field renames, models merged/split) → needs OpenUpgrade scripts
- Regression surface (tests, demo data, views) → needs verification

This recipe splits the work into **5 phases** so the IA works in small, verifiable chunks with fresh context, instead of trying to port a whole module in one shot (which fails).

---

## The phases

```
┌───────────┐   ┌──────┐   ┌──────┐   ┌─────────┐   ┌────────┐
│ 0. Intake │ → │ 1.   │ → │ 2.   │ → │ 3.      │ → │ 4.     │
│           │   │ Res. │   │ Plan │   │ Execute │   │ Verify │
└───────────┘   └──────┘   └──────┘   └─────────┘   └────────┘
```

| Phase | Goal | Output | Who leads |
|-------|------|--------|-----------|
| 0. Intake | Capture the migration request, scope, constraints | `MIGRATION.md` seed | Human |
| 1. Research | Understand target version changes + current module state | `research.md` | AI |
| 2. Plan | Break work into atomic tasks with acceptance criteria | `plan.md` | AI + Human review |
| 3. Execute | Apply changes task by task, each in fresh context | Commits per task | AI |
| 4. Verify | Run tests, manual QA, upgrade on real DB copy | `verification.md` | AI + Human |

---

## How to use it

1. **Copy** the `template/` folder into your module repo (or into a sibling folder).
2. **Fill in** `template/MIGRATION.md` with the 3 things only you know: source version, target version, module path.
3. **Open** the module in Claude Code / Codex and paste the **Phase 1 prompt** from `prompts/01-research.md`.
4. **Review** the AI's `research.md` output — this is your first gate.
5. **Paste Phase 2 prompt** → review `plan.md` → **this is your main gate**, do not skip.
6. For each task in `plan.md`, paste the **Phase 3 prompt** in a fresh chat window (important: fresh context per task).
7. When all tasks are done, paste **Phase 4 prompt** to run the verification suite.

See [`docs/workflow.md`](docs/workflow.md) for the full flow with diagrams.

---

## What's in the box

```
odoo-migration-recipe/
├── README.md                       ← you are here
├── template/                       ← copy this into your project
│   ├── MIGRATION.md                ← the single source of truth for this migration
│   ├── research.md                 ← filled by Phase 1
│   ├── plan.md                     ← filled by Phase 2
│   └── verification.md             ← filled by Phase 4
├── prompts/                        ← paste these into Claude/Codex
│   ├── 00-intake.md
│   ├── 01-research.md
│   ├── 02-plan.md
│   ├── 03-execute-task.md
│   └── 04-verify.md
├── checklists/
│   ├── odoo-version-deltas.md      ← known breaking changes per version
│   ├── mechanical-transforms.md    ← what to automate vs do by hand
│   └── gates.md                    ← the "don't proceed until" checklist
├── scripts/
│   ├── bootstrap.sh                ← initialize a new migration
│   ├── run-module-migrator.sh      ← wraps OCA odoo-module-migrator
│   └── upgrade-test-db.sh          ← spin up a test DB and upgrade
└── docs/
    ├── workflow.md
    ├── tools.md                    ← OpenUpgrade, oca-port, module-migrator
    └── why-phases.md
```

---

## Rules of the recipe

These are non-negotiable — they're the lessons from every Odoo migration gone wrong:

1. **Never skip Phase 2 (Plan)**. "Just start porting" is the #1 cause of week-long migrations that should have taken a day.
2. **One task = one commit = one fresh AI context.** Do not let the AI batch tasks.
3. **Tests first, then code.** If the original module has no tests on the risky path, Phase 2 must add them before Phase 3 touches the code.
4. **Real DB upgrade is the only real test.** `-u module` on a copy of production data is the gate for "done".
5. **Mechanical transforms are not a migration.** `odoo-module-migrator` is step zero, not step done.
6. **Read OpenUpgrade first.** If OCA already ported the models your module touches, use their `pre/post-migration.py` as reference.

---

## Credits & references

- [OCA OpenUpgrade](https://github.com/OCA/OpenUpgrade) — the reference for DB-level migration
- [OCA Migration Guidelines](https://github.com/OCA/maintainer-tools/wiki) — the community checklist
- [OCA odoo-module-migrator](https://github.com/OCA/odoo-module-migrator) — mechanical transforms
- [OCA oca-port](https://github.com/OCA/oca-port) — port commits between versions
- [GSD: Get Shit Done](https://github.com/gsd-build/get-shit-done) — the meta-prompting approach this is modeled on
