#!/usr/bin/env bash
# Initialize a new migration: copy the template into the target module folder.
#
# Usage:  ./scripts/bootstrap.sh <path/to/module> <from_version> <to_version>
# Example: ./scripts/bootstrap.sh ~/repos/my_module 16.0 17.0

set -euo pipefail

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <module_path> <from_version> <to_version>"
    exit 1
fi

MODULE_PATH="$1"
FROM_VERSION="$2"
TO_VERSION="$3"

RECIPE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MIGRATION_DIR="${MODULE_PATH}/.migration"

if [[ ! -d "${MODULE_PATH}" ]]; then
    echo "ERROR: module path does not exist: ${MODULE_PATH}"
    exit 1
fi

if [[ -d "${MIGRATION_DIR}" ]]; then
    echo "ERROR: ${MIGRATION_DIR} already exists. Remove it or resume the existing migration."
    exit 1
fi

mkdir -p "${MIGRATION_DIR}"
cp "${RECIPE_DIR}/template/"*.md "${MIGRATION_DIR}/"

# Seed MIGRATION.md with the versions we know
sed -i.bak \
    -e "s|<from>|${FROM_VERSION}|g" \
    -e "s|<to>|${TO_VERSION}|g" \
    "${MIGRATION_DIR}/MIGRATION.md" \
    "${MIGRATION_DIR}/research.md" \
    "${MIGRATION_DIR}/plan.md" \
    "${MIGRATION_DIR}/verification.md"
rm -f "${MIGRATION_DIR}"/*.bak

echo "Migration initialized at: ${MIGRATION_DIR}"
echo ""
echo "Next steps:"
echo "  1. Fill in the remaining <placeholders> in ${MIGRATION_DIR}/MIGRATION.md"
echo "  2. Open the module in Claude Code / Codex"
echo "  3. Paste the Phase 1 prompt from: ${RECIPE_DIR}/prompts/01-research.md"
