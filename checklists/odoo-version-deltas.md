# Odoo version deltas — quick reference

> Consolidated, non-exhaustive list of breaking / notable changes per version. Use as a **starting point** for Phase 1 research — always verify against the official release notes and OCA/OpenUpgrade for your specific version jump.

> Contribute: when you finish a migration, add the gotchas you actually hit to the matching section.

---

## Common concerns across all jumps

- `__manifest__.py` `version` field: bump the *first* number to match the target Odoo version.
- `__manifest__.py` `license` field: required on newer versions.
- Test that the module installs on a **fresh** DB and upgrades on a **copy** DB — both matter, and they fail for different reasons.
- Check every `depends` — a dependency that doesn't exist on the target version is a blocker, not a nit.

---

## 13.0 → 14.0

- `@api.multi` removed — it was already a no-op, but linters will complain.
- `track_visibility` attribute on fields removed in favor of `tracking=True`.
- `attrs` on `<button>` elements: check readonly / invisible behavior.
- JS: OWL framework introduced for some views (backport of 15.0 work). Legacy widgets still supported.

## 14.0 → 15.0

- `account` module: massive refactor (tax calculation, journal entries). If your module touches accounting, expect deep changes.
- `mail` templates: `email_from` default logic changed.
- Views: `t-options` serialization changes in some cases.
- JS: broader OWL adoption in settings / views.

## 15.0 → 16.0

- `states` attribute on fields and `<button>` is **deprecated** — migrate to `attrs` or `invisible` expressions.
- `name_get` / `name_search` conventions: stable but watch `_rec_name` interactions.
- `res.config.settings`: change in default value handling for some field types.
- Reports: QWeb reports — some wrapper templates renamed.

## 16.0 → 17.0

- `attrs` attribute on XML views **removed** — replaced by individual attributes: `invisible`, `readonly`, `required` with Python expressions.
- `states` attribute on views **removed** — migrate to `invisible="state not in [...]"`.
- `<tree>` XML tag **renamed to `<list>`**. The old tag still works (aliased) but new code should use `<list>`.
- Chatter: placement in views changed; `<div class="oe_chatter">` pattern often migrated to `<chatter/>` shortcut.
- JS: OWL is now the default; legacy widgets mostly removed.
- `@api.depends_context`: behavior tightened.

## 17.0 → 18.0

- Python 3.10 minimum.
- Web client: further OWL consolidation, some legacy JS APIs removed.
- Many `<tree>` compatibility aliases gone — must be `<list>`.
- `res.partner` / `res.users` — field signature changes in some areas.
- Server actions: API subtle changes around `env.context`.

---

## Mechanical vs semantic

The table below helps Phase 2 decide what to automate and what to hand-migrate.

| Change | Mechanical? | Tool |
|---|---|---|
| `<tree>` → `<list>` | Yes | `odoo-module-migrator` |
| `attrs="{...}"` → individual attrs | Mostly | `odoo-module-migrator` (covers common cases; complex Python expressions need review) |
| `states="..."` → `invisible="..."` | Mostly | `odoo-module-migrator` |
| `track_visibility` → `tracking` | Yes | sed / migrator |
| `@api.multi` removal | Yes | sed |
| Manifest version bump | Yes | sed |
| License field add | Yes | sed |
| `name_get` override compatibility | No — semantic | hand |
| Accounting module logic | No — semantic | hand, per OCA guide |
| OWL component migration (legacy JS) | Partially | hand, follow Odoo docs |
| Data-shape changes (renamed columns) | No — needs `pre-migration.py` | OpenUpgrade + hand |

---

## Canonical references (go here first, always)

- **Odoo release notes**: https://www.odoo.com/odoo/releases
- **OCA OpenUpgrade**: https://github.com/OCA/OpenUpgrade — has per-version `migrations/` directories showing real migration scripts for every core module
- **OCA Migration Guidelines wiki**: https://github.com/OCA/maintainer-tools/wiki (search "Migration to version X")
- **odoo-module-migrator**: https://github.com/OCA/odoo-module-migrator — read its `migration_scripts/` folder to see exactly what it transforms
