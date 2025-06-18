#!/bin/bash
set -euo pipefail

## --- Base --- ##
# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

SCORE=$(
curl -X 'GET' \
  'http://127.0.0.1:10002/test-script' \
  -H 'accept: application/json'
)

echo "OK: Bot got the score of ${SCORE}"
