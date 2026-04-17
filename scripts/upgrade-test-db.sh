#!/usr/bin/env bash
# Upgrade a DB copy with the migrated module. This is the Phase 4 "real" test.
#
# Requires: an Odoo installation on the target version, and a DB copy of production.
#
# Usage:
#   ./scripts/upgrade-test-db.sh <odoo-bin-path> <db_name> <module_name> [addons_path]

set -euo pipefail

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <odoo-bin> <db_name> <module_name> [addons_path]"
    echo "Example: $0 /opt/odoo17/odoo-bin testdb_copy my_module /opt/odoo17/addons,/opt/custom"
    exit 1
fi

ODOO_BIN="$1"
DB_NAME="$2"
MODULE_NAME="$3"
ADDONS_PATH="${4:-}"

LOG_FILE="upgrade-${DB_NAME}-${MODULE_NAME}-$(date +%Y%m%d-%H%M%S).log"

ARGS=(
    -d "${DB_NAME}"
    -u "${MODULE_NAME}"
    --stop-after-init
    --log-level=info
    --logfile="${LOG_FILE}"
)

if [[ -n "${ADDONS_PATH}" ]]; then
    ARGS+=(--addons-path="${ADDONS_PATH}")
fi

echo "Upgrading ${MODULE_NAME} on DB ${DB_NAME}"
echo "Log: ${LOG_FILE}"
echo ""

"${ODOO_BIN}" "${ARGS[@]}"
EXIT_CODE=$?

echo ""
echo "----- Upgrade finished with exit code ${EXIT_CODE} -----"
echo ""
echo "Scanning log for warnings and errors related to ${MODULE_NAME}:"
grep -Ei "(error|warning|deprecat)" "${LOG_FILE}" | grep -i "${MODULE_NAME}" || echo "  (none found — good)"

exit ${EXIT_CODE}
