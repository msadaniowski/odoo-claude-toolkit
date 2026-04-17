# Phase 0 — Intake prompt

> Paste this to Claude / Codex when you want help filling in `MIGRATION.md`. Optional — you can fill it by hand.

---

You are helping me start an Odoo module migration. Before we do anything else, help me fill out the intake section of `template/MIGRATION.md`.

Ask me **only** the questions whose answers you cannot derive from reading the module source. Specifically:

1. Source and target Odoo versions
2. Path to the module and path to the target DB dump (for test upgrades)
3. Deadline or hard constraints
4. Any known "do not touch" areas
5. Whether we have a rollback plan

For everything else (module name, manifest version, dependencies), read the code and fill it yourself.

**Rules:**
- Do NOT start researching or planning yet. This is intake only.
- Do NOT modify any code.
- Output only the updated `MIGRATION.md` intake section.
- If something is ambiguous, ask me — do not guess.

When done, print: `INTAKE COMPLETE — ready for Phase 1 (Research)`.
