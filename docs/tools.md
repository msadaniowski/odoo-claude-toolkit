# Tools

The recipe orchestrates these OCA / community tools. None of them are built here — we just script their usage.

## `odoo-module-migrator` (mechanical)
- **Repo**: https://github.com/OCA/odoo-module-migrator
- **What it does**: applies mechanical transformations between versions (manifest bump, XML renames, deprecated-attr removal, decorator cleanup).
- **When to use**: step 1 of Phase 3, always.
- **Wrapper**: `scripts/run-module-migrator.sh`

## `oca-port` (commit porting)
- **Repo**: https://github.com/OCA/oca-port
- **What it does**: takes commits that already exist on the source-version branch of an OCA module and replays them on the target-version branch, surfacing conflicts.
- **When to use**: for OCA modules where newer versions already have partial migration commits.
- **Install**: `pip install oca-port`

## `OpenUpgrade` (data migration reference)
- **Repo**: https://github.com/OCA/OpenUpgrade
- **What it does**: provides per-version migration scripts for every core Odoo module. It is the canonical reference for *how core data shapes change between versions*.
- **When to use**: Phase 1 (research — check if your module's models are covered), Phase 3 (pattern reference for your own `pre/post-migration.py`).
- **Not a codemod** — you read its scripts, you don't run them on your custom modules.

## Odoo itself (the only real verifier)
- `-i <module>` on a fresh DB — tests installation path
- `-u <module>` on a DB copy of production — tests upgrade path (this is the real gate)
- `--test-enable` — runs the module's unit tests during install/upgrade
- Wrapper: `scripts/upgrade-test-db.sh`

## Optional but useful

### `pre-commit` with OCA hooks
- **Install**: `pip install pre-commit && pre-commit install`
- OCA provides a curated set of hooks (`.pre-commit-config.yaml` templates in `OCA/oca-addons-repo-template`) that catch manifest/license/XML issues before they reach a commit.

### `flake8-odoo` / `pylint-odoo`
- Static analysis plugins tuned for Odoo code. Integrate with pre-commit or run standalone. Catches many deprecated-API usages.

### `coverage.py`
- For measuring test coverage of risky paths identified in `research.md`.
