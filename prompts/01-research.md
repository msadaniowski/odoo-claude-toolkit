# Phase 1 — Research prompt

> Paste this to Claude / Codex in a fresh chat. Attach or point it at your module directory and the filled `MIGRATION.md`.

---

You are in **Phase 1: Research** of an Odoo module migration. Read-only discovery pass. **Do not change any code.**

## Inputs
- `template/MIGRATION.md` (§0 Intake is filled)
- The module source at the path listed in MIGRATION.md
- Reference: `checklists/odoo-version-deltas.md` in this recipe

## Your job

Produce a complete `research.md` following the template in `template/research.md`. Specifically:

1. **Inventory** the module: models, views, wizards, reports, tests, deps.
2. **Compute the delta** between the source and target Odoo versions for *this specific module*. Only list changes that actually affect files in this module — do not dump the full changelog.
3. **Cross-reference OpenUpgrade**: for each model the module inherits from core, check if OCA/OpenUpgrade has migration scripts for that model in the target version. Link them.
4. **Build the risk table**: for each risky area, rate impact + likelihood + mitigation.
5. **List known unknowns**: things I need to answer before we can plan.

## Hard rules
- No code changes. No file writes except `research.md` and updating the `## 1. Research output` section of `MIGRATION.md` (which should just be a 5-line summary + "see research.md").
- If the source has no tests, say so explicitly — this is critical for planning.
- If you're unsure whether a change applies, mark it with `⚠️ needs human check` rather than assuming.
- Do NOT propose a plan or tasks. That is Phase 2.

When done, print: `RESEARCH COMPLETE — ready for Phase 2 (Plan)`.
