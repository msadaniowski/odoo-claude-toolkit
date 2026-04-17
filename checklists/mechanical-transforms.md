# Mechanical transforms — what to automate

> "Mechanical" = the transformation is unambiguous and correctness can be verified by running the module. These are the changes you should **never** hand-edit.

## Always run first — `odoo-module-migrator`

```bash
pip install odoo-module-migrator
odoo-module-migrator \
    --directory=/path/to/module-repo \
    --modules=<module_name> \
    --init-version-name=<from> \
    --target-version-name=<to>
```

This covers (depending on the jump):
- Manifest version bump
- `<tree>` → `<list>`
- `attrs` / `states` XML transformations
- `@api.multi` removal
- `track_visibility` → `tracking`
- Deprecated decorator removal
- Some common import-path updates

**Always commit the output in its own commit** before any manual work — makes the review of hand-edits much cleaner.

## Helper — `oca-port` (for OCA modules)

```bash
pip install oca-port
oca-port <from> <to> <module_name> --repo-path=.
```

Pulls the relevant commits from the source branch and applies them to the target, surfacing conflicts.

## Reference the OpenUpgrade pre/post scripts

If your module inherits from a core model, OpenUpgrade has already done the heavy lifting for that model's data migration. Read:

```
OpenUpgrade/openupgrade_scripts/scripts/<module>/<target_version>/pre-migration.py
OpenUpgrade/openupgrade_scripts/scripts/<module>/<target_version>/post-migration.py
```

Copy patterns, don't reinvent.

## What NEVER to auto-migrate

- Business logic in `.py` files — read each change, understand it
- Custom JS widgets — OWL migration is case-by-case
- Report templates with complex QWeb logic
- `_sql_constraints` — they may no longer make sense with the new schema
- Security rules (`ir.rule`) — always re-audit on a major jump
