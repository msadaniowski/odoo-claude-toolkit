#!/usr/bin/env bash
# Wrapper around OCA odoo-module-migrator. Run this as the FIRST code-changing step of Phase 3.
# https://github.com/OCA/odoo-module-migrator
#
# Usage: ./scripts/run-module-migrator.sh <module_path> <module_name> <from> <to>

set -euo pipefail

if [[ $# -lt 4 ]]; then
    echo "Usage: $0 <repo_root> <module_name> <from_version> <to_version>"
    exit 1
fi

REPO_ROOT="$1"
MODULE_NAME="$2"
FROM="$3"
TO="$4"

if ! command -v odoo-module-migrator >/dev/null 2>&1; then
    echo "Installing odoo-module-migrator..."
    pip install --quiet odoo-module-migrator
fi

echo "Running odoo-module-migrator: ${MODULE_NAME} from ${FROM} to ${TO}"
echo "Repo: ${REPO_ROOT}"
echo ""

odoo-module-migrator \
    --directory="${REPO_ROOT}" \
    --modules="${MODULE_NAME}" \
    --init-version-name="${FROM}" \
    --target-version-name="${TO}"

echo ""
echo "Done. Review changes with 'git diff' and commit as a single 'chore(migrate): mechanical transforms' commit BEFORE any hand edits."
