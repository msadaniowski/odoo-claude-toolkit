# Migration: `<module_name>` from Odoo `<from>` to `<to>`

> This file is the single source of truth for this migration. Every phase reads from and writes to it.
> Fill in the `<placeholders>` before starting Phase 1.

## 0. Intake (filled by human)

- **Module**: `<module_technical_name>`
- **Repo / path**: `<git_url_or_local_path>`
- **Source version**: `<e.g. 16.0>`
- **Target version**: `<e.g. 17.0>`
- **Type**: [ ] OCA module  [ ] Custom / in-house  [ ] 3rd-party
- **Has OpenUpgrade coverage?**: [ ] Yes  [ ] No  [ ] Partial — link: `<url>`
- **Depends on (other modules that must migrate first)**: `<list>`
- **Target DB for test upgrade**: `<db_name_or_dump_path>`
- **Deadline / constraints**: `<free text>`

### Risk checklist (human judgement)
- [ ] Module has tests covering business-critical paths
- [ ] Module has no undocumented monkey-patches of core
- [ ] No custom fields are stored in deprecated/renamed columns
- [ ] Demo data is safe to regenerate
- [ ] There is a rollback plan

### Non-goals for this migration
> List here what we are explicitly NOT doing (e.g. "no refactor", "no new features", "keep XML IDs stable")
-

---

## 1. Research output
> Filled by AI in Phase 1. Summarizes what's known about the module's current state and the delta to the target version.

_(pending)_

---

## 2. Plan output
> Filled by AI in Phase 2. List of atomic tasks, each with acceptance criteria.

_(pending)_

---

## 3. Execution log
> Append one line per task as it lands. Link to commit.

| # | Task | Commit | Status |
|---|------|--------|--------|
|   |      |        |        |

---

## 4. Verification output
> Filled by AI + human in Phase 4.

_(pending)_
