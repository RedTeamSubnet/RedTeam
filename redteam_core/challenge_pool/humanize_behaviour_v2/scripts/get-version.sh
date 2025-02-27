#!/bin/bash
set -euo pipefail


## --- Base --- ##
# Getting path of this script file:
_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
_PROJECT_DIR="$(cd "${_SCRIPT_DIR}/.." >/dev/null 2>&1 && pwd)"
cd "${_PROJECT_DIR}" || exit 2

# Loading .env file (if exists):
if [ -f ".env" ]; then
	# shellcheck disable=SC1091
	source .env
fi
## --- Base --- ##


## --- Variables --- ##
# Load from envrionment variables:
VERSION_FILE_PATH="${VERSION_FILE_PATH:-./src/api/__version__.py}"
## --- Variables --- ##


if [ -n "${VERSION_FILE_PATH}" ] && [ -f "${VERSION_FILE_PATH}" ]; then
	_current_version=$(< "${VERSION_FILE_PATH}" grep "__version__ = " | awk -F' = ' '{print $2}' | tr -d '"') || exit 2
else
	_current_version="0.0.0-$(date -u '+%y%m%d')"
fi

echo "${_current_version}"
