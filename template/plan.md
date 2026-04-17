# Plan — `<module>` `<from>` → `<to>`

> Filled by AI in Phase 2, reviewed by human. Each task must be atomic: one concern, one commit, one fresh AI context.

## Ordering principles
1. **Manifest + metadata** first (unblocks loading the module on the target version).
2. **Mechanical transforms** next (`odoo-module-migrator`, `attrs`→`invisible`, etc.).
3. **Model changes** (fields, API, ORM calls).
4. **View / XML changes**.
5. **Business logic** (the semantic risky part).
6. **Tests** (add missing coverage for the risky paths, then keep existing ones green).
7. **Data migration scripts** (`pre-migration.py`, `post-migration.py`) last.

## Tasks

### T01 — `<short imperative title>`
- **Phase**: [metadata | mechanical | model | view | logic | tests | data]
- **Files touched (expected)**: `<list>`
- **Dependencies**: `<task numbers>`
- **Acceptance criteria**:
  - [ ] `<verifiable outcome 1>`
  - [ ] `<verifiable outcome 2>`
- **How to verify**: `<command or manual step>`
- **Estimated risk**: [low | medium | high]

### T02 — ...

---

## Out of scope (explicitly)
> Things this plan does NOT do, to prevent scope creep.
-

## Gates (must pass before declaring migration done)
- [ ] Module installs on fresh target-version DB
- [ ] Module upgrades on DB copy of production (via `-u <module>`)
- [ ] All existing tests pass
- [ ] New tests cover the risky paths identified in research.md §4
- [ ] `odoo --test-enable -i <module>` exits 0
- [ ] Views render without warnings in server log
- [ ] No deprecation warnings in server log for this module
