#!/bin/bash
set -euo pipefail

## --- Base --- ##
# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

echo "INFO: Copying compose override file..."
cp ./templates/compose/compose.override.dev.yml ./compose.override.yml || exit 2

echo "INFO: Starting challenge server..."
./compose.sh start -l || exit 2

echo "OK: Setup complete!"
