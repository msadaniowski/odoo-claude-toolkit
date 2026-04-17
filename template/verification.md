# Verification — `<module>` `<from>` → `<to>`

> Filled in Phase 4. The migration is NOT done until every box here is checked.

## Automated gates

- [ ] `pip install -e .` / dependencies resolve on target version
- [ ] `odoo -i <module> --stop-after-init --test-enable` exits 0 on a fresh DB
- [ ] `odoo -u <module> --stop-after-init` exits 0 on a **copy of production**
- [ ] Linters pass: `pre-commit run --all-files`
- [ ] No new warnings in server log matching the module name
- [ ] Coverage of risky paths is ≥ `<threshold>`% (if measured)

## Manual QA checklist
> Tailor to the module. The AI should propose this list based on `research.md` §4.

- [ ] Core user flow 1: `<describe>`
- [ ] Core user flow 2: `<describe>`
- [ ] Reports render (PDF + HTML)
- [ ] Wizards open and complete
- [ ] Email templates render
- [ ] Access rights behave as expected for all groups

## Data migration verification
> Only if there are `pre/post-migration.py` scripts.

- [ ] Row counts match pre/post upgrade (`SELECT COUNT(*) ...`)
- [ ] No orphaned records
- [ ] Renamed columns have expected values
- [ ] Demo data still works (if demo is shipped)

## Rollback plan
- DB snapshot taken at: `<path/url>`
- Rollback command: `<command>`
- Time-to-rollback estimate: `<minutes>`

## Sign-off
- Migrated by: `<name>` / `<AI + human>`
- Reviewed by: `<name>`
- Date: `<YYYY-MM-DD>`
